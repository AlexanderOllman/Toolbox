from fastapi import APIRouter, HTTPException, Depends, status, Response, BackgroundTasks
from typing import List, Dict, Any, Optional
import subprocess
import os
import logging # Import logging
from pydantic import BaseModel, Field
from fastapi.responses import PlainTextResponse, JSONResponse
import json # Added for header processing
import re # For regex parsing of ENV in Dockerfile

from app.models.repositories import Repository, RepositoryCreate, RepositoryUpdate, ServerRoot, EnvVarDetail, FinalizeDeploymentRequest
from app.services.database import get_repositories, get_repository, add_repository, delete_repository, add_server_root, get_server_roots, update_repository_fields
from app.services.openai_service import get_repo_info_from_gpt
from app.services.vector_db_service import search_repositories
from app.services.config_service import get_mcp_repo_path
from app.services.repository_validation_service import RepositoryValidationService
from app.services.mcp_auto_test import mcp_auto_test_service
# Docker service imports removed - using new MCP testing system instead

router = APIRouter()
logger = logging.getLogger(__name__) # Add logger

# Add OPTIONS endpoint to handle preflight requests and prevent redirects
@router.options("/", include_in_schema=False)
async def options_repositories():
    return Response(status_code=200)

class RepoDetailsRequest(BaseModel):
    repo_url: str

class DeployContainerRequest(BaseModel):
    image_name: Optional[str] = None # Optional if using docker-compose
    container_args: Optional[Dict[str, str]] = Field(default_factory=dict) # Changed from {} to Field for consistency
    env_vars: Optional[Dict[str, EnvVarDetail]] = Field(default_factory=dict) # Changed from {} to Field for consistency
    attempt_local_build: Optional[bool] = True
    attempt_push_to_registry: Optional[bool] = False
    use_docker_compose: Optional[bool] = False
    host_port_mapping: Optional[int] = None # The host port selected by the user
    actual_container_port: Optional[int] = None # The container port it's mapped to
    container_command: Optional[str] = None # Command to run inside the container
    container_command_args: Optional[List[str]] = None # Arguments for the command

class SearchQuery(BaseModel):
    query: str
    limit: int = 5

class ServerRootCreate(BaseModel):
    uri: str
    name: str = None
    server_uri_alias: str = None

# Helper function to parse ENV from Dockerfile content
def parse_dockerfile_env_vars(dockerfile_content: str) -> List[Dict[str, str]]:
    env_vars = []
    # Regex to capture ENV key=value or ENV key value
    # It handles optional quotes around the value
    env_pattern = re.compile(r"^\s*ENV\s+([^=\s]+)\s*=?\s*(\"(.*?)\"|'(.*?)'|([^\s#]+))", re.MULTILINE)
    for match in env_pattern.finditer(dockerfile_content):
        key = match.group(1)
        # Value can be in group 3 (double-quoted), 4 (single-quoted), or 5 (unquoted)
        value = match.group(3) or match.group(4) or match.group(5)
        if key and value is not None:
            env_vars.append({"key": key, "value": value, "source": "dockerfile"})
    logger.info(f"Parsed ENV vars from Dockerfile: {env_vars}")
    return env_vars

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

@router.post("/details", status_code=200)
async def fetch_repository_details(request: RepoDetailsRequest):
    repo_url = request.repo_url
    logger.info(f"Fetching details for repository URL: {repo_url}")
    
    try:
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
        base_dir = get_mcp_repo_path()
        dest = os.path.join(base_dir, repo_name)
        
        # Ensure base directory exists
        os.makedirs(base_dir, exist_ok=True)
        
        if not os.path.exists(dest):
            logger.info(f"Cloning {repo_url} to {dest}")
            try:
                subprocess.run(['git', 'clone', repo_url, dest], check=True, timeout=60)
                logger.info(f"Successfully cloned {repo_url} to {dest}")
            except subprocess.TimeoutExpired:
                logger.error(f"Git clone timed out for {repo_url}")
                raise HTTPException(status_code=500, detail=f"Repository clone timed out. Please try again.")
            except subprocess.CalledProcessError as clone_error:
                logger.error(f"Git clone failed for {repo_url}: {clone_error}")
                raise HTTPException(status_code=500, detail=f"Failed to clone repository: {clone_error}")
        else:
            logger.info(f"Repository {repo_name} already exists at {dest}. Pulling latest changes.")
            try:
                # Attempt to pull latest changes. This might require more robust error handling.
                subprocess.run(['git', '-C', dest, 'pull'], check=True, timeout=30) # Added timeout
                logger.info(f"Successfully updated {repo_name}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Git pull timed out for {dest}. Using existing files.")
            except subprocess.CalledProcessError as pull_error:
                logger.warning(f"Git pull failed for {dest}: {pull_error}. Using existing files.")
        
        # Validate that the repository was properly cloned/updated
        if not os.path.isdir(dest):
            logger.error(f"Repository directory {dest} does not exist after clone/pull operation")
            raise HTTPException(status_code=500, detail=f"Repository directory not found after clone operation")

        readme_text = ""
        for fname_readme in ['README.md', 'README.rst', 'README']:
            path_readme = os.path.join(dest, fname_readme)
            if os.path.isfile(path_readme):
                with open(path_readme, 'r', encoding='utf-8') as f_readme:
                    readme_text = f_readme.read()
                break
        
        dockerfile_path = os.path.join(dest, 'Dockerfile')
        has_dockerfile = os.path.isfile(dockerfile_path)
        dockerfile_content = ""
        if has_dockerfile:
            try:
                with open(dockerfile_path, 'r', encoding='utf-8') as df_content_file:
                    dockerfile_content = df_content_file.read()
            except Exception as e_dockerfile:
                logger.warning(f"Could not read Dockerfile at {dockerfile_path}: {e_dockerfile}")

        has_docker_compose = False
        # relevant_compose_content = "" # If we wanted to return content
        for cf_name in ['docker-compose.yml', 'docker-compose.yaml']:
            potential_compose_path = os.path.join(dest, cf_name)
            if os.path.isfile(potential_compose_path):
                has_docker_compose = True
                # try:
                #     with open(potential_compose_path, 'r', encoding='utf-8') as comp_f:
                #         relevant_compose_content = comp_f.read()
                # except Exception as e_compose_read:
                #     logger.warning(f"Could not read compose file at {potential_compose_path}: {e_compose_read}")
                break

        container_args_template = {}
        if has_dockerfile and readme_text: # Prioritize Dockerfile context for args if available
            lines = readme_text.splitlines()
            for line in lines:
                if 'docker run' in line:
                    parts = line.split()
                    parsed_args = {} 
                    i = 0
                    while i < len(parts):
                        part = parts[i]
                        if part == 'docker' or part == 'run': 
                            i += 1
                            continue
                        if not part.startswith('-'): break # Heuristic: End of options
                        
                        key = part
                        value = ""
                        if i + 1 < len(parts) and not parts[i+1].startswith('-'):
                            value = parts[i+1]
                            i += 1 # Consumed value
                        parsed_args[key] = value
                        i += 1
                    if parsed_args: container_args_template = parsed_args; break
        
        dockerfile_env_vars_parsed = []
        if dockerfile_content:
            dockerfile_env_vars_parsed = parse_dockerfile_env_vars(dockerfile_content)

        exposed_port = None # New variable to store EXPOSEd port
        if dockerfile_content: # Parse EXPOSE from Dockerfile
            expose_pattern = re.compile(r"^\s*EXPOSE\s+([0-9]+)", re.MULTILINE | re.IGNORECASE)
            match = expose_pattern.search(dockerfile_content)
            if match:
                try:
                    exposed_port = int(match.group(1))
                    logger.info(f"Parsed EXPOSEd port from Dockerfile: {exposed_port}")
                except ValueError:
                    logger.warning(f"Could not parse port from EXPOSE line: {match.group(0)}")

        gpt_repo_info = {}
        try:
            repo_info_from_gpt = get_repo_info_from_gpt(readme_text, dockerfile_content if has_dockerfile else None)
            gpt_repo_info = {
                "description": repo_info_from_gpt.get("description", "No description available"),
                "command": repo_info_from_gpt.get("command"),
                "args": repo_info_from_gpt.get("args", []),
                "env": repo_info_from_gpt.get("env", {}),
                "docker_image_name_suggestion": repo_info_from_gpt.get("docker_image_name_suggestion")
            }
        except Exception as e_openai_config:
            # Handle case where OpenAI service is not configured or other errors
            logger.warning(f"OpenAI service error: {e_openai_config}")
            gpt_repo_info = {"description": "AI analysis skipped: OpenAI service error.", "command": None, "args": [], "env": {}, "docker_image_name_suggestion": None}
        except Exception as e_gpt:
            logger.error(f"GPT extraction failed: {e_gpt}")
            gpt_repo_info = {"description": "AI analysis failed.", "command": None, "args": [], "env": {}, "docker_image_name_suggestion": None}
            
        response_data = {
            "name": repo_name,
            "repo_url": repo_url,
            "description": gpt_repo_info.get("description"),
            "command": gpt_repo_info.get("command"),
            "args": gpt_repo_info.get("args"),
            "env": gpt_repo_info.get("env"),
            "has_dockerfile": has_dockerfile,
            "has_docker_compose": has_docker_compose,
            "docker_image_name_suggestion": gpt_repo_info.get("docker_image_name_suggestion"),
            "container_args_template": container_args_template,
            "dockerfile_env_vars": dockerfile_env_vars_parsed,
            "dockerfile_content": dockerfile_content if has_dockerfile else "",
            "exposed_port_suggestion": exposed_port,
            "error": None
        }
        logger.debug(f"Returning details for {repo_url}: {response_data}")
        return JSONResponse(content=response_data)
    
    except subprocess.CalledProcessError as e_clone:
        logger.error(f"Failed to clone repository {repo_url}: {e_clone}")
        raise HTTPException(status_code=500, detail=f"Failed to clone repository: {str(e_clone)}")
    except Exception as e_main:
        logger.error(f"Error fetching repository details for {repo_url}: {e_main}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process repository: {str(e_main)}")

# --- New Endpoint for Container Repos ---
@router.get("/containers/", response_model=List[Repository])
async def list_container_repositories():
    """List all repositories configured for container deployment."""
    all_repos = get_repositories() # This already includes the new fields
    # Filter for both deploy_as_container and is_external_config to be more accurate based on previous frontend changes
    # However, the previous frontend tab logic was `deploy_as_container` OR `is_external_config` for "External"
    # Let's assume for now this endpoint is strictly for `deploy_as_container` true.
    # If external ones should be listed here, the filter needs adjustment.
    container_repos = [repo for repo in all_repos if repo.get('deploy_as_container') is True and repo.get('is_external_config') is not True]
    return container_repos
# --- End New Endpoint ---

@router.put("/{repo_name}", response_model=Repository)
async def update_existing_repository(repo_name: str, repo_update_data: RepositoryUpdate):
    """Update an existing repository. 
    'repo_name' in path is the key. 'name' in body is ignored if provided for non-external, 
    and drives 'repo_url' for external (but external name is immutable once set).
    """
    existing_repo = get_repository(repo_name)
    if not existing_repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository '{repo_name}' not found.")

    update_data = repo_update_data.dict(exclude_unset=True)

    # Primary identifier `name` (and thus `repo_url` for external) should not be changed once created.
    # The frontend already disallows editing `name` for external configs.
    # If `name` were allowed to change for external, repo_url (`external://<name>`) would need to sync.
    if update_data.get('name') and update_data.get('name') != repo_name:
        # This logic branch is more for non-external. For external, name is immutable in current design.
        logger.warning(f"Attempt to change repository name from '{repo_name}' to '{update_data.get('name')}' is not allowed. Name change ignored.") 
    update_data.pop('name', None) # Remove name from update_data as it's the key or immutable

    # repo_url should not be changed after creation, especially for external configs.
    update_data.pop('repo_url', None) 

    if repo_update_data.is_external_config is True:
        logger.info(f"Updating repository '{repo_name}' as external config.")
        # Explicitly set fields for an external configuration
        update_data['is_external_config'] = True
        update_data['deployment_status'] = 'n/a_external'
        
        # Fields to keep from payload if provided (already in update_data if exclude_unset=True)
        # update_data['description'] = repo_update_data.description
        # update_data['transport'] = repo_update_data.transport
        # update_data['url'] = repo_update_data.url
        # update_data['headers'] = repo_update_data.headers # Assumed to be JSON string from frontend
        # update_data['read_transport_sse_timeout_seconds'] = repo_update_data.read_transport_sse_timeout_seconds

        # Nullify fields not applicable to external configurations
        update_data['command'] = None
        update_data['args'] = []
        update_data['env'] = {}
        update_data['has_dockerfile'] = False
        update_data['deploy_as_container'] = False
        update_data['container_args_template'] = {}
        update_data['container_args_user'] = {}
        update_data['git_clone_url'] = None # Assuming this field exists in the DB model implicitly or via RepositoryBase
        update_data['local_path'] = None
        update_data['readme_content'] = None
        update_data['gpt_summary'] = None
        update_data['tags'] = []
        update_data['last_pulled'] = None
        update_data['last_commit_sha'] = None

        # Validate headers if provided: ensure it's a valid JSON string representing an object
        if 'headers' in update_data and update_data['headers'] is not None:
            try:
                headers_dict = json.loads(update_data['headers'])
                if not isinstance(headers_dict, dict):
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Headers must be a JSON string representing a key-value object.")
            except json.JSONDecodeError:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON format for headers.")

    elif repo_update_data.is_external_config is False: # Explicitly set to not external
        logger.info(f"Updating repository '{repo_name}' as non-external (Git/Docker).")
        update_data['is_external_config'] = False
        # deployment_status would be handled by other logic (e.g., deploy endpoint) or remain as is if not changed.
        # If it was 'n/a_external' and now it's not external, it should probably reset to 'not_deployed' or similar.

        # Handle env for non-external (Git/Docker)
        if "env" in update_data and update_data["env"] is not None:
            # Assuming repo_update_data.env is Dict[str, EnvVarDetail]
            serialized_env = {k: v.dict() for k, v in repo_update_data.env.items()} 
            update_data["env"] = serialized_env
        elif "env" in update_data and update_data["env"] is None: # Explicitly clearing env
             update_data["env"] = {}
        # If "env" not in update_data, it's unchanged due to exclude_unset=True

        # container_args_user should be Dict[str, str]
        # Frontend sends it as an object if deploy_as_container is true.
        # RepositoryUpdate expects Dict[str, str], so direct assignment should be fine.
        if "container_args_user" in update_data and update_data["container_args_user"] is None:
            update_data["container_args_user"] = {}

        # If deploy_as_container is explicitly set to False, clear container specific fields
        if repo_update_data.deploy_as_container is False:
            update_data['container_args_user'] = {}
            # deployment_status might also need an update, e.g. if it was 'deployed_docker'
            if existing_repo.get('deploy_as_container') is True: # If switching FROM container
                 update_data['deployment_status'] = 'not_deployed' # Or based on actual command presence
        
        # If deploy_as_container is True, ensure related fields are handled.
        # Frontend sends these, so they should be in update_data via exclude_unset.

    else: # is_external_config is not in payload (None)
        # This means we are updating an existing repo without changing its external/non-external nature.
        # Apply updates based on its current type stored in DB.
        logger.info(f"Partially updating repository '{repo_name}'. External status determined by existing record.")
        if existing_repo.get('is_external_config') is True:
            # If it's an existing external config, ensure non-applicable fields are not erroneously set
            # and that external-specific fields are processed correctly.
            update_data['is_external_config'] = True # Ensure this stays true
            if 'deployment_status' not in update_data: # If not explicitly set in payload
                update_data['deployment_status'] = 'n/a_external'
            
            update_data.pop('command', None)
            update_data.pop('args', None)
            # env for external should be empty or not present, current model might allow it.
            # For safety, let's clear it if it's not supposed to be there for external types.
            update_data.pop('env', None) # Or set to {}
            update_data.pop('has_dockerfile', None)
            update_data.pop('deploy_as_container', None)
            update_data.pop('container_args_template', None)
            update_data.pop('container_args_user', None)
            
            if 'headers' in update_data and update_data['headers'] is not None:
                try:
                    headers_dict = json.loads(update_data['headers'])
                    if not isinstance(headers_dict, dict):
                        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Headers must be a JSON string for an object.")
                except json.JSONDecodeError:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON for headers.")
        else: # Existing repo is NOT external (Git/Docker)
            update_data['is_external_config'] = False # Ensure this stays false
            if "env" in update_data and update_data["env"] is not None:
                serialized_env = {k: v.dict() for k, v in repo_update_data.env.items()} 
                update_data["env"] = serialized_env
            elif "env" in update_data and update_data["env"] is None:
                 update_data["env"] = {}
            
            if "container_args_user" in update_data and update_data["container_args_user"] is None:
                 update_data["container_args_user"] = {}
            
            if repo_update_data.deploy_as_container is False and 'deploy_as_container' in update_data:
                update_data['container_args_user'] = {}
                if existing_repo.get('deploy_as_container') is True and existing_repo.get('deployment_status', '').startswith('deployed'):
                    update_data['deployment_status'] = 'not_deployed' 

    # Remove has_dockerfile and container_args_template as these are generally not directly updatable by user.
    # They are derived at creation or by system processes.
    update_data.pop('has_dockerfile', None) 
    update_data.pop('container_args_template', None)

    if not update_data:
        # This can happen if only 'name' or 'repo_url' was in payload and got popped,
        # or if payload was empty.
        # However, if exclude_unset=True, an empty payload means repo_update_data had no fields set.
        # If all fields in payload matched existing_repo fields, update_data could also be empty if we diffed.
        # But update_repository_fields should handle empty update_data gracefully (as no-op).
        # For clarity, we can return the existing repo or a message.
        logger.info(f"No effective changes detected for repository '{repo_name}'. Returning existing data.")
        return Repository(**existing_repo) # Return existing data as no actual update fields processed

    logger.debug(f"Calling update_repository_fields for '{repo_name}' with data: {update_data}")
    try:
        updated_id = update_repository_fields(repo_name, update_data)
        if updated_id is None: # Should not happen if repo exists, but as a safeguard
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update repository, ID not returned.")
        
        # Fetch the updated repository to return the full object
        # get_repository should return a dict-like object, which Repository can model
        updated_repo_data = get_repository(repo_name) 
        if updated_repo_data is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve repository after update.")
        
        return Repository(**updated_repo_data)
    except Exception as e:
        logger.error(f"Error during repository update for '{repo_name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/", response_model=Repository, status_code=status.HTTP_201_CREATED)
async def create_repository(repo_data: RepositoryCreate, background_tasks: BackgroundTasks):
    logger.info(f"Creating repository. is_external_config: {repo_data.is_external_config}, name: {repo_data.name}, repo_url: {repo_data.repo_url}")
    try:
        repo_data_dict = repo_data.dict(exclude_unset=True)

        # Ensure read_transport_sse_timeout_seconds is an integer or the default
        parsed_timeout_val = None
        if repo_data.read_transport_sse_timeout_seconds is not None:
            try:
                # Pydantic model RepositoryCreate should ensure it's an int if not None
                parsed_timeout_val = repo_data.read_transport_sse_timeout_seconds 
            except (ValueError, TypeError):
                 # This case should ideally not be hit if RepositoryCreate works as expected
                logger.warning(f"Could not parse read_transport_sse_timeout_seconds: {repo_data.read_transport_sse_timeout_seconds}, using default.")

        if repo_data.is_external_config:
            logger.info(f"Processing as external config for: {repo_data.name}")
            if not repo_data.description: # Check if description is empty or None
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Description is required for external MCP server configurations.")
            
            if repo_data.transport not in ['http', 'sse', 'streamable_http']:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid transport protocol. Must be: http, sse, streamable_http")
            if not repo_data.url:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="URL is required for external MCP server configurations.")
            
            repo_data_dict['name'] = repo_data.name
            repo_data_dict.setdefault('description', repo_data.description or "Externally configured server.")
            repo_data_dict.setdefault('command', '')
            repo_data_dict.setdefault('args', [])
            repo_data_dict.setdefault('env', {k: v.dict() for k, v in repo_data.env.items()} if repo_data.env else {})
            repo_data_dict.setdefault('transport', repo_data.transport)
            repo_data_dict.setdefault('url', repo_data.url)
            repo_data_dict.setdefault('headers', repo_data.headers or '{}')
            # Explicitly set the timeout, defaulting to 300 if None or parsing failed
            repo_data_dict['read_transport_sse_timeout_seconds'] = parsed_timeout_val if parsed_timeout_val is not None else 300
            repo_data_dict.setdefault('deploy_as_container', False)
            repo_data_dict.setdefault('has_dockerfile', False)
            repo_data_dict.setdefault('container_args_template', {})
            repo_data_dict.setdefault('container_args_user', {})
            repo_data_dict.setdefault('deployment_status', 'n/a_external')
        else:
            if not repo_data.command and not (repo_data.has_dockerfile or False): # Assuming has_docker_compose is not on repo_data
                 raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Command is required for non-containerized/non-compose repositories.")
            if repo_data.deploy_as_container and not repo_data.name:
                 raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Repository Name is required for container deployment.")

            repo_data_dict.setdefault('transport', 'stdio')
            repo_data_dict.setdefault('url', '')
            repo_data_dict.setdefault('headers', '{}')
            # For non-external, it's not user-configurable and should use the system default (handled by RepositoryBase model default)
            # However, to be absolutely sure no None slips to the DB model if it disallows it, we set it.
            # The RepositoryBase model has `Optional[int] = 300`, so `None` should be fine and use default 300.
            # If `None` from `repo_data.read_transport_sse_timeout_seconds` (via `RepositoryCreate`) is causing issues
            # when constructing `Repository` later, explicitly setting it to the default here is safer.
            repo_data_dict['read_transport_sse_timeout_seconds'] = parsed_timeout_val if parsed_timeout_val is not None else 300
            repo_data_dict.setdefault('deploy_as_container', repo_data.deploy_as_container or False)
            repo_data_dict.setdefault('has_dockerfile', repo_data.has_dockerfile or False)
            repo_data_dict.setdefault('container_args_template', {})
            repo_data_dict.setdefault('container_args_user', repo_data.container_args_user or {})
            repo_data_dict.setdefault('deployment_status', 'not_deployed')

        # Create the repository in the database using Qdrant
        repo = add_repository(repo_data_dict)
        
        # Trigger automatic MCP testing for eligible repositories
        if mcp_auto_test_service.should_auto_test_repository(repo_data_dict):
            logger.info(f"Triggering automatic MCP test for newly created repository: {repo_data.name}")
            mcp_auto_test_service.trigger_auto_test(repo_data.name, background_tasks)
        else:
            logger.debug(f"Repository '{repo_data.name}' not eligible for automatic testing")
        
        return Repository(**repo)
    except Exception as e:
        logger.error(f"Error creating repository: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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

# --- New Endpoint for Dockerfile Content ---
@router.get("/{name}/dockerfile", response_class=PlainTextResponse)
async def get_repo_dockerfile_content(name: str):
    """Get the Dockerfile content for a specific repository."""
    # First try to get from database
    repo = get_repository(name)
    repo_url = None
    cloned_repo_name = name  # Default fallback
    
    if repo is not None:
        repo_url = repo.get("repo_url")
        if repo_url:
            cloned_repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
    else:
        # If not in database, try to find the repository directory directly
        # This handles cases where repository details were fetched but not saved to DB
        logger.warning(f"Repository '{name}' not found in database, attempting direct file system lookup")
    
    base_dir = get_mcp_repo_path()
    
    # Try multiple possible paths for the repository
    possible_paths = [
        os.path.join(base_dir, cloned_repo_name),  # From repo_url derivation
        os.path.join(base_dir, name),              # Direct name match
    ]
    
    repo_path = None
    dockerfile_path = None
    
    # Find the actual repository path
    for path in possible_paths:
        if os.path.isdir(path):
            potential_dockerfile = os.path.join(path, "Dockerfile")
            if os.path.isfile(potential_dockerfile):
                repo_path = path
                dockerfile_path = potential_dockerfile
                logger.info(f"Found Dockerfile at {dockerfile_path}")
                break
    
    if not repo_path:
        # If we have repo info but no local clone, provide helpful error
        if repo and repo_url:
            raise HTTPException(
                status_code=404, 
                detail=f"Repository '{name}' found in database but not cloned locally. "
                       f"Expected at {possible_paths[0]}. Please re-fetch repository details to clone it."
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Repository '{name}' not found. Searched paths: {possible_paths}. "
                       f"Please ensure the repository has been added and cloned."
            )

    if not dockerfile_path or not os.path.isfile(dockerfile_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Dockerfile not found in repository '{name}' at {repo_path}"
        )

    try:
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Successfully read Dockerfile for {name} from {dockerfile_path}")
        return PlainTextResponse(content=content)
    except Exception as e:
        logger.error(f"Error reading Dockerfile for {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read Dockerfile: {str(e)}")
# --- End New Dockerfile Endpoint --- 

# --- Helper function for background task ---
async def _start_and_monitor_container_task(
    repo_name: str, 
    container_id: str, 
    final_container_name: str,
):
    logger.info(f"[BGTask {repo_name}/{container_id[:7]}] Background task started.")
    try:
        await docker_service.start_and_monitor_container(
            container_id=container_id, 
            final_container_name=final_container_name, 
            repo_name=repo_name # Pass repo_name for potential DB updates within service
        )
        logger.info(f"[BGTask {repo_name}/{container_id[:7]}] Container started and passed health check successfully.")
        update_repository_fields(repo_name, {"deployment_status": "deployed", "container_id": container_id})
    
    except docker_service.DockerServiceError as e:
        logger.error(f"[BGTask {repo_name}/{container_id[:7]}] DockerServiceError: {e.error_type} - {e}", exc_info=True)
        failure_status = "failed_to_deploy"
        if e.error_type == "runtime_check_failed":
            failure_status = "failed_health_check"
        elif e.error_type == "oom_killed":
            failure_status = "failed_oom"
        elif e.error_type == "container_error_state":
            failure_status = "failed_container_error_state"
        elif e.error_type == "docker_start_monitor_failed":
            failure_status = "failed_start_monitor"
        # else, keep as failed_to_deploy or be more specific
        update_repository_fields(repo_name, {"deployment_status": failure_status, "container_id": container_id})
    
    except Exception as e_generic:
        logger.error(f"[BGTask {repo_name}/{container_id[:7]}] Generic exception: {e_generic}", exc_info=True)
        update_repository_fields(repo_name, {"deployment_status": "failed_unknown_error", "container_id": container_id})


# --- New Deploy Container Endpoint --- (Modified to use Background Task)
@router.post("/{repo_name}/deploy", status_code=status.HTTP_202_ACCEPTED) # Changed to 202 Accepted
async def deploy_container_repository(repo_name: str, deploy_request: DeployContainerRequest, background_tasks: BackgroundTasks):
    """Deploy a repository as a Docker container. Initiates deployment and returns."""
    logger.info(f"[API /deploy] Received request for {repo_name}. Image: {deploy_request.image_name}, Build: {deploy_request.attempt_local_build}")
    repo = get_repository(repo_name)
    if repo is None:
        logger.error(f"[API /deploy] Repository '{repo_name}' not found in database.")
        raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found.")

    if not repo.get("deploy_as_container"):
        logger.error(f"[API /deploy] Repository '{repo_name}' is not configured for container deployment.")
        raise HTTPException(status_code=400, detail=f"Repository '{repo_name}' is not configured for container deployment.")

    # --- Get additional repo data needed for build/deploy ---
    has_dockerfile = repo.get("has_dockerfile", False)
    has_docker_compose = repo.get("has_docker_compose", False) # Get this new flag
    repo_url = repo.get("repo_url")
    repo_local_path = None
    cloned_repo_folder_name = None

    # Determine cloned_repo_path (needed for both Dockerfile build and docker-compose)
    if repo_url: # repo_url is necessary to derive the path where it was cloned
        try:
            cloned_repo_folder_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
            base_dir = get_mcp_repo_path()
            repo_local_path = os.path.join(base_dir, cloned_repo_folder_name)
            
            # Enhanced validation with multiple path attempts
            if not os.path.isdir(repo_local_path):
                # Try alternative paths
                alternative_paths = [
                    os.path.join(base_dir, repo_name),  # Direct name match
                    os.path.join(base_dir, cloned_repo_folder_name)  # Original derivation
                ]
                
                for alt_path in alternative_paths:
                    if os.path.isdir(alt_path):
                        repo_local_path = alt_path
                        logger.info(f"Found repository at alternative path: {repo_local_path}")
                        break
                else:
                    # Still not found, update status and raise error
                    update_repository_fields(repo_name, {"deployment_status": "failed_repo_not_cloned"})
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Repository directory not found. Searched paths: {alternative_paths}. "
                               f"Please re-fetch repository details to ensure it's properly cloned."
                    )
            
            # Validate that required files exist for the deployment type
            if deploy_request.attempt_local_build and has_dockerfile:
                dockerfile_path = os.path.join(repo_local_path, "Dockerfile")
                if not os.path.isfile(dockerfile_path):
                    update_repository_fields(repo_name, {"deployment_status": "failed_dockerfile_missing"})
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Dockerfile not found at {dockerfile_path}. Cannot perform local build."
                    )
            
            if deploy_request.use_docker_compose and has_docker_compose:
                compose_files = ['docker-compose.yml', 'docker-compose.yaml']
                compose_found = False
                for compose_file in compose_files:
                    if os.path.isfile(os.path.join(repo_local_path, compose_file)):
                        compose_found = True
                        break
                
                if not compose_found:
                    update_repository_fields(repo_name, {"deployment_status": "failed_compose_missing"})
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Docker Compose file not found in {repo_local_path}. Cannot use Docker Compose deployment."
                    )
                    
        except Exception as path_e:
            update_repository_fields(repo_name, {"deployment_status": "failed_path_error"})
            raise HTTPException(status_code=500, detail=f"Error determining repository path: {path_e}")
    elif has_dockerfile or deploy_request.use_docker_compose:
        # If we intend to build or use compose, but have no repo_url to find the files
        update_repository_fields(repo_name, {"deployment_status": "failed_missing_repo_url_for_local_op"})
        raise HTTPException(status_code=400, detail="Repository URL not found, cannot locate local files for build or Docker Compose.")

    # Decision point: Use Docker Compose or single container deployment?
    if deploy_request.use_docker_compose:
        if not has_docker_compose:
            raise HTTPException(status_code=400, detail=f"Repository '{repo_name}' is not configured with a docker-compose.yml file.")
        if not repo_local_path: # Should be caught above, but double check
             raise HTTPException(status_code=500, detail="Cannot use Docker Compose without a valid local repository path.")

        logger.info(f"Deploying '{repo_name}' using Docker Compose from path: {repo_local_path}")
        update_repository_fields(repo_name, {"deployment_status": "deploying_compose"})
        try:
            compose_result = await docker_service.deploy_with_compose(
                repo_name=repo_name,
                cloned_repo_path=repo_local_path
            )
            update_repository_fields(repo_name, {"deployment_status": "deployed_compose", "container_id": compose_result.get("project_name")})
            return compose_result # Contains message, project_name, services
        except docker_service.DockerServiceError as e:
            update_repository_fields(repo_name, {"deployment_status": "failed_compose_deploy"}) 
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            update_repository_fields(repo_name, {"deployment_status": "failed_compose_deploy"}) 
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred with Docker Compose deployment: {str(e)}")

    # --- Standard Single Container Deployment Logic (now uses background task for start+monitor) ---
    else:
        logger.info(f"[API /deploy] Initiating single container deployment for '{repo_name}'.")
        if not deploy_request.image_name:
             logger.error(f"[API /deploy] Image name missing for '{repo_name}'.")
             raise HTTPException(status_code=400, detail="Image name required.")

        image_name_from_request = deploy_request.image_name
        user_container_args = deploy_request.container_args or {}
        user_env_vars_detail = deploy_request.env_vars or {} 
        attempt_local_build_flag = deploy_request.attempt_local_build
        attempt_push_flag = deploy_request.attempt_push_to_registry

        effective_command = deploy_request.container_command if deploy_request.container_command is not None else repo.get("command")
        effective_args = deploy_request.container_command_args if deploy_request.container_command_args is not None else repo.get("args", [])
        
        # Save initial user choices and set status to "pending_create"
        fields_to_update = {
            "container_args_user": user_container_args,
            "env": {k: v.dict() for k, v in user_env_vars_detail.items() if isinstance(v, EnvVarDetail)},
            "host_port_mapping": deploy_request.host_port_mapping,
            "actual_container_port": deploy_request.actual_container_port,
            "last_build_attempt_local": attempt_local_build_flag,
            "last_push_attempt_registry": attempt_push_flag,
            "last_deployment_used_compose": False,
            "deployment_status": "pending_create" # New initial status
        }
        if image_name_from_request != repo.get("docker_image_name_suggestion"):
            fields_to_update["image_name_override"] = image_name_from_request
        else:
            fields_to_update["image_name_override"] = None 
        
        update_repository_fields(repo_name, fields_to_update)
        logger.debug(f"[API /deploy] Initial fields updated for {repo_name}, status set to pending_create.")

        # Log critical variables before calling the service
        logger.info(f"[API /deploy] For repo '{repo_name}':")
        logger.info(f"  repo_url: {repo_url}")
        logger.info(f"  repo_local_path (becomes cloned_repo_path): {repo_local_path}")
        logger.info(f"  image_name_from_request: {image_name_from_request}")
        logger.info(f"  attempt_local_build_flag: {attempt_local_build_flag}")
        logger.info(f"  effective_command: {effective_command}")
        logger.info(f"  effective_args: {effective_args}")

        try:
            logger.info(f"[API /deploy] Calling build_and_create_container for {repo_name}...")
            created_container_id, final_container_name = await docker_service.build_and_create_container(
                repo_name=repo_name,
                image_name=image_name_from_request,
                container_args=user_container_args,
                env_vars=user_env_vars_detail,
                repo_url=repo_url, 
                cloned_repo_path=repo_local_path,
                attempt_local_build=attempt_local_build_flag,
                attempt_push_to_registry=attempt_push_flag,
                container_command=effective_command,
                container_command_args=effective_args
            )
            logger.info(f"[API /deploy] build_and_create_container for {repo_name} SUCCEEDED. Container ID: {created_container_id}, Name: {final_container_name}")
            
            # Update DB with created ID and status "pending_start"
            update_repository_fields(repo_name, {"deployment_status": "pending_start", "container_id": created_container_id})
            logger.debug(f"[API /deploy] DB status for {repo_name} updated to pending_start.")

            # Add the start and monitor step to background tasks
            logger.info(f"[API /deploy] Adding start_and_monitor_container_task to background for {repo_name} (ID: {created_container_id}).")
            background_tasks.add_task(
                _start_and_monitor_container_task, 
                repo_name=repo_name, 
                container_id=created_container_id, 
                final_container_name=final_container_name
            )
            
            logger.info(f"[API /deploy] Returning 202 Accepted for {repo_name}. Deployment initiated.")
            return {
                "message": f"Deployment initiated for '{repo_name}'. Container creation succeeded.", 
                "container_id": created_container_id,
                "container_name": final_container_name,
                "status": "pending_start"
            }

        except docker_service.DockerServiceError as e:
            logger.error(f"DockerServiceError during build/create for '{repo_name}': {e}", exc_info=True)
            # Determine specific failure status based on error type from build_and_create_container
            failure_status = "failed_to_deploy" # Generic fallback
            if e.error_type == "docker_build_failed": # Assuming build_image internally sets this type
                failure_status = "build_failed"
            elif e.error_type == "docker_push_failed": # Assuming push_image sets this
                failure_status = "push_failed"
            elif e.error_type == "docker_create_failed":
                failure_status = "create_failed"
            # Add more specific error types if build_and_create_container provides them
            
            update_repository_fields(repo_name, {"deployment_status": failure_status})
            raise HTTPException(status_code=500, detail=str(e)) # Re-raise to client
        
        except Exception as e_generic:
            logger.error(f"Generic exception during build/create for '{repo_name}': {e_generic}", exc_info=True)
            update_repository_fields(repo_name, {"deployment_status": "failed_unknown_error"})
            raise HTTPException(status_code=500, detail=f"Failed to initiate deployment: {str(e_generic)}")

# --- End New Deploy Container Endpoint --- 

@router.post("/repositories/finalize-deployment", response_model=Repository)
async def finalize_deployment_and_create_repository(
    request_data: FinalizeDeploymentRequest
):
    """
    Finalizes a container/service deployment by creating an 'external' repository entry
    pointing to the successfully deployed local container/service.
    This is called *after* the container is confirmed running by the frontend/deployment script.
    """
    logger.info(f"Finalizing deployment for: {request_data.original_repo_name}")

    if not request_data.host_port:
        raise HTTPException(status_code=400, detail="Host port is required to finalize deployment as an external service.")

    # Construct the URL for the locally deployed MCP service
    # Assuming deployment is always on localhost from the perspective of the backend
    # The mcp_path should include a leading slash if it's a path, e.g. /mcp
    service_url_path = request_data.mcp_path if request_data.mcp_path.startswith('/') else f"/{request_data.mcp_path}"
    if service_url_path == "/": # Avoid double slashes if path is just root
        service_url_path = ""
    service_url = f"http://localhost:{request_data.host_port}{service_url_path}"

    logger.info(f"Constructed service URL: {service_url}")

    # Convert simple {key: value} env_vars from request to Dict[str, EnvVarDetail]
    env_vars_for_db: Dict[str, EnvVarDetail] = {}
    if request_data.final_env_vars:
        for key, val_str in request_data.final_env_vars.items():
            env_vars_for_db[key] = EnvVarDetail(value=val_str, status="User-defined")

    repo_data_for_db = RepositoryCreate(
        name=request_data.original_repo_name,
        description=request_data.description,
        repo_url=request_data.original_repo_url, # Store original Git URL for reference
        is_external_config=True, # Key change: it's now an external config
        transport="http", # Assuming http for containerized MCPs
        url=service_url,
        # Store deployment-specific info for potential future use (e.g., re-deploy, info)
        # These fields might need to be added to RepositoryBase/RepositoryCreate if not already there
        # or stored in a separate related table if they become too numerous.
        command=request_data.command_suggestion, 
        args=request_data.args_suggestion,
        env=env_vars_for_db,
        has_dockerfile=request_data.has_dockerfile,
        deploy_as_container=True, # Indicates it was deployed as a container
        # container_args_user: might store some representation of user args if needed
        deployment_status=f"deployed_self_hosted_{request_data.deployment_type}", # e.g., deployed_self_hosted_dockerfile
        # Potentially store: deployed_image_name, deployed_container_id_or_project_name, dockerfile_content (or its hash/path)
        # For now, keeping it simple. Add to model if these are critical for DB.
        read_transport_sse_timeout_seconds=300 # Default, can be made configurable
    )

    try:
        logger.info(f"Attempting to add repository to DB: {repo_data_for_db.name}")
        # Convert RepositoryCreate to dict for Qdrant-based add_repository
        repo_dict = repo_data_for_db.dict()
        add_repository(repo_dict)
        logger.info(f"Successfully added repository {repo_data_for_db.name} to DB after deployment.")
        # Return the created repository data
        return get_repository(repo_data_for_db.name)
    except Exception as e:
        logger.error(f"Error while finalizing deployment for {request_data.original_repo_name}: {e}")
        # Log the full stack trace for unexpected errors
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while saving the repository: {str(e)}")

@router.post("/sync-local/{repo_name}", status_code=status.HTTP_201_CREATED)
async def sync_local_repository(repo_name: str, background_tasks: BackgroundTasks):
    """
    Synchronize a locally cloned repository with the database.
    This handles cases where repositories were cloned via /details but not saved to DB.
    """
    # Check if repository already exists in database
    existing_repo = get_repository(repo_name)
    if existing_repo:
        return {"message": f"Repository '{repo_name}' already exists in database", "repository": existing_repo}
    
    # Use validation service to find and analyze the local repository
    is_valid, error_msg, repo_info = RepositoryValidationService.validate_repository_for_deployment(repo_name)
    
    if not repo_info.get('local_path'):
        raise HTTPException(
            status_code=404, 
            detail=f"Repository '{repo_name}' not found locally. Please clone it first using the repository details endpoint."
        )
    
    local_path = repo_info['local_path']
    
    # Try to derive repository URL from git remote
    repo_url = None
    try:
        result = subprocess.run(
            ['git', '-C', local_path, 'remote', 'get-url', 'origin'], 
            capture_output=True, text=True, check=True
        )
        repo_url = result.stdout.strip()
        logger.info(f"Derived repository URL: {repo_url}")
    except subprocess.CalledProcessError:
        logger.warning(f"Could not determine git remote URL for {repo_name}")
        # Fallback to a constructed URL if possible
        repo_url = f"https://github.com/unknown/{repo_name}.git"
    
    # Read README for description
    description = "Repository synchronized from local clone"
    readme_files = ['README.md', 'README.rst', 'README.txt', 'README']
    for readme_file in readme_files:
        readme_path = os.path.join(local_path, readme_file)
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                    # Extract first paragraph as description
                    lines = readme_content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and len(line) > 20:
                            description = line[:200] + "..." if len(line) > 200 else line
                            break
                break
            except Exception as e:
                logger.warning(f"Could not read README file {readme_path}: {e}")
    
    # Analyze repository for MCP configuration
    command = None
    args = []
    env = {}
    
    # Check for common MCP patterns
    if repo_info.get('has_dockerfile'):
        # If has Dockerfile, likely meant for container deployment
        deploy_as_container = True
        
        # Try to extract command from Dockerfile
        dockerfile_path = repo_info.get('dockerfile_path')
        if dockerfile_path:
            try:
                with open(dockerfile_path, 'r', encoding='utf-8') as f:
                    dockerfile_content = f.read()
                    # Look for CMD or ENTRYPOINT
                    for line in dockerfile_content.split('\n'):
                        line = line.strip()
                        if line.startswith('CMD') or line.startswith('ENTRYPOINT'):
                            # Extract command (simplified parsing)
                            if '[' in line and ']' in line:
                                # JSON format
                                import json
                                try:
                                    cmd_part = line.split('[', 1)[1].split(']', 1)[0]
                                    cmd_list = json.loads('[' + cmd_part + ']')
                                    if cmd_list:
                                        command = cmd_list[0]
                                        args = cmd_list[1:] if len(cmd_list) > 1 else []
                                except:
                                    pass
                            else:
                                # Shell format
                                cmd_part = line.split(None, 1)[1] if ' ' in line else ''
                                if cmd_part:
                                    command = cmd_part.split()[0] if cmd_part.split() else cmd_part
                                    args = cmd_part.split()[1:] if len(cmd_part.split()) > 1 else []
                            break
            except Exception as e:
                logger.warning(f"Could not parse Dockerfile: {e}")
    else:
        deploy_as_container = False
        
        # Check for Python package
        pyproject_path = os.path.join(local_path, 'pyproject.toml')
        setup_py_path = os.path.join(local_path, 'setup.py')
        
        if os.path.isfile(pyproject_path):
            # Try to extract command from pyproject.toml
            try:
                import toml
                with open(pyproject_path, 'r') as f:
                    pyproject_data = toml.load(f)
                    
                # Look for scripts or entry points
                scripts = pyproject_data.get('project', {}).get('scripts', {})
                if scripts:
                    # Use first script as command
                    script_name = list(scripts.keys())[0]
                    command = script_name
                else:
                    # Look for tool.poetry.scripts or similar
                    poetry_scripts = pyproject_data.get('tool', {}).get('poetry', {}).get('scripts', {})
                    if poetry_scripts:
                        script_name = list(poetry_scripts.keys())[0]
                        command = script_name
                    else:
                        # Fallback to package name
                        package_name = pyproject_data.get('project', {}).get('name', repo_name)
                        command = package_name
            except Exception as e:
                logger.warning(f"Could not parse pyproject.toml: {e}")
                command = f"python -m {repo_name}"
        elif os.path.isfile(setup_py_path):
            # Fallback for setup.py
            command = f"python -m {repo_name}"
        else:
            # Generic fallback
            command = repo_name
    
    # Create repository data
    repo_data = {
        "name": repo_name,
        "repo_url": repo_url,
        "description": description,
        "command": command,
        "args": args,
        "env": env,
        "transport": "stdio",
        "url": "",
        "headers": "{}",
        "has_dockerfile": repo_info.get('has_dockerfile', False),
        "has_docker_compose": repo_info.get('has_docker_compose', False),
        "deploy_as_container": deploy_as_container,
        "is_external_config": False,
        "container_args_template": {},
        "container_args_user": {},
        "deployment_status": "not_deployed",
        "read_transport_sse_timeout_seconds": 300
    }
    
    try:
        # Add to database
        created_repo = add_repository(repo_data)
        logger.info(f"Successfully synchronized repository '{repo_name}' to database")
        
        # Trigger automatic MCP testing for the synchronized repository
        if mcp_auto_test_service.should_auto_test_repository(repo_data):
            logger.info(f"Triggering automatic MCP test for synchronized repository: {repo_name}")
            mcp_auto_test_service.trigger_auto_test(repo_name, background_tasks)
        else:
            logger.debug(f"Synchronized repository '{repo_name}' not eligible for automatic testing")
        
        return {
            "message": f"Repository '{repo_name}' successfully synchronized to database",
            "repository": created_repo,
            "local_path": local_path,
            "analysis": {
                "has_dockerfile": repo_info.get('has_dockerfile', False),
                "has_docker_compose": repo_info.get('has_docker_compose', False),
                "deploy_as_container": deploy_as_container
            }
        }
    except Exception as e:
        logger.error(f"Error synchronizing repository '{repo_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to synchronize repository: {str(e)}")