from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import subprocess
import os
from pydantic import BaseModel

from app.models.repositories import Repository, RepositoryCreate
from app.services.database import get_repositories, get_repository, add_repository, delete_repository
from app.services.openai_service import get_repo_info_from_gpt
from app.services.vector_db_service import add_repository_to_vector_db, delete_repository_from_vector_db, search_repositories

router = APIRouter()

class RepoDetailsRequest(BaseModel):
    repo_url: str

class SearchQuery(BaseModel):
    query: str
    limit: int = 5

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
        base_dir = os.path.join(os.path.expanduser('~'), 'mcp')
        os.makedirs(base_dir, exist_ok=True)
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
        base_dir = os.path.join(os.path.expanduser('~'), 'mcp')
        os.makedirs(base_dir, exist_ok=True)
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
        
        # Add to database
        repo = add_repository(name, description, command, args)
        
        # Add to vector database - this won't fail if Qdrant is unavailable
        try:
            metadata = {
                "command": command,
                "args": args,
                "repo_url": repo_url
            }
            add_repository_to_vector_db(name, description, metadata)
        except Exception as e:
            print(f"Warning: Failed to add repository to vector database: {str(e)}")
            # Continue anyway, don't fail the whole request
        
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
    
    # Also remove from vector database - this won't fail if Qdrant is unavailable
    try:
        delete_repository_from_vector_db(name)
    except Exception as e:
        print(f"Warning: Failed to remove repository from vector database: {str(e)}")
        # Continue anyway, don't fail the whole request
    
    return None 