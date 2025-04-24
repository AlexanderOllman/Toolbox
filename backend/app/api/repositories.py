from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import subprocess
import os
from pydantic import BaseModel

from app.models.repositories import Repository, RepositoryCreate, ServerRoot
from app.services.database import get_repositories, get_repository, add_repository, delete_repository, add_server_root, get_server_roots
from app.services.openai_service import get_repo_info_from_gpt
from app.services.vector_db_service import search_repositories
from app.services.config_service import get_mcp_repo_path

router = APIRouter()

class RepoDetailsRequest(BaseModel):
    repo_url: str

class SearchQuery(BaseModel):
    query: str
    limit: int = 5

class ServerRootCreate(BaseModel):
    uri: str
    name: str = None
    server_uri_alias: str = None

@router.get("/", response_model=List[Repository])
async def list_repositories():
    """List all repositories."""
    return get_repositories()

@router.get("/{name}", response_model=Repository)
async def get_repository_by_name(name: str):
    """Get a repository by name."""
    repo = get_repository(name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.post("/search")
async def search_repos(search_query: SearchQuery):
    """Search repositories using vector similarity."""
    results = search_repositories(search_query.query, search_query.limit)
    return results

@router.post("/details")
async def fetch_repository_details(request: RepoDetailsRequest):
    """Fetch repository details without adding to database."""
    repo_url = request.repo_url
    
    try:
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
        
        # Set up temp directory for clone
        base_dir = get_mcp_repo_path()
        dest = os.path.join(base_dir, repo_name)
        
        # Clone repo if not exists
        if not os.path.exists(dest):
            subprocess.run(['git', 'clone', repo_url, dest], check=True)
        
        # Extract README
        readme_text = ""
        for fname in ['README.md', 'README.rst', 'README']:
            path = os.path.join(dest, fname)
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    readme_text = f.read()
                break
        
        if not readme_text:
            return {
                "name": repo_name,
                "description": "No README found",
                "command": None,
                "args": []
            }
            
        # Use GPT to extract info from README
        repo_info = get_repo_info_from_gpt(readme_text)
        
        return {
            "name": repo_name,
            "description": repo_info.get("description", "No description available"),
            "command": repo_info.get("command"),
            "args": repo_info.get("args", [])
        }
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone repository: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process repository: {str(e)}")

@router.post("/", response_model=Repository, status_code=status.HTTP_201_CREATED)
async def create_repository(repo_data: RepositoryCreate):
    """Add a new repository."""
    # Clone the repository and extract info
    try:
        # Clone repo and extract README
        base_dir = get_mcp_repo_path()
        repo_url = repo_data.repo_url
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
        dest = os.path.join(base_dir, repo_name)
        
        # Clone if not exists
        if not os.path.exists(dest):
            subprocess.run(['git', 'clone', repo_url, dest], check=True)
        
        # Extract README
        readme_text = ""
        for fname in ['README.md', 'README.rst', 'README']:
            path = os.path.join(dest, fname)
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    readme_text = f.read()
                break
        
        # Use provided values or extract from README with GPT
        name = repo_data.name or repo_name
        
        # If description, command, or args are not provided, use GPT to extract them
        if not repo_data.description or not repo_data.command or not repo_data.args:
            try:
                # Only use GPT if we found a README
                if readme_text:
                    repo_info = get_repo_info_from_gpt(readme_text)
                    description = repo_data.description or repo_info.get("description", "No description available")
                    command = repo_data.command or repo_info.get("command")
                    args = repo_data.args or repo_info.get("args", [])
                else:
                    description = repo_data.description or "No description available"
                    command = repo_data.command
                    args = repo_data.args or []
            except Exception as e:
                # If GPT fails, fall back to provided values
                print(f"GPT extraction failed: {str(e)}")
                description = repo_data.description or "No description available"
                command = repo_data.command
                args = repo_data.args or []
        else:
            # Use provided values directly
            description = repo_data.description
            command = repo_data.command
            args = repo_data.args
        
        # Add to database (now using Qdrant) with all the fields
        repo = add_repository(
            name=name, 
            description=description, 
            command=command, 
            args=args,
            transport=repo_data.transport,
            url=repo_data.url,
            read_timeout_seconds=repo_data.read_timeout_seconds,
            read_transport_sse_timeout_seconds=repo_data.read_transport_sse_timeout_seconds,
            headers=repo_data.headers,
            api_key=repo_data.api_key,
            env=repo_data.env,
            roots_table=repo_data.roots_table
        )
        
        return repo
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone repository: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process repository: {str(e)}")

@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repository(name: str):
    """Delete a repository."""
    success = delete_repository(name)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return None

@router.post("/{name}/roots", response_model=ServerRoot)
async def add_root_to_repository(name: str, root_data: ServerRootCreate):
    """Add a root directory to a repository."""
    # Check if repository exists
    repo = get_repository(name)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # If no roots_table is defined for this repository, return an error
    if not repo.get("roots_table"):
        raise HTTPException(
            status_code=400, 
            detail="This repository does not have a roots table defined. Update the repository first to set a roots_table value."
        )
    
    # Add the root
    success = add_server_root(
        server_name=name,
        uri=root_data.uri,
        name=root_data.name,
        server_uri_alias=root_data.server_uri_alias
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add root to repository")
    
    return ServerRoot(
        server_name=name,
        uri=root_data.uri,
        name=root_data.name,
        server_uri_alias=root_data.server_uri_alias
    )

@router.get("/{name}/roots", response_model=List[ServerRoot])
async def get_repository_roots(name: str):
    """Get all roots for a repository."""
    # Check if repository exists
    repo = get_repository(name)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Get the roots
    roots = get_server_roots(name)
    
    # Convert to ServerRoot models
    return [
        ServerRoot(
            server_name=name,
            uri=root["uri"],
            name=root.get("name"),
            server_uri_alias=root.get("server_uri_alias")
        ) for root in roots
    ] 