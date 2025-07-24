from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# New model for structured environment variable details
class EnvVarDetail(BaseModel):
    value: Optional[str] = None
    status: Optional[str] = "Optional" # Default to Optional

class RepositoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = []
    transport: str = "stdio"
    url: Optional[str] = ""
    read_timeout_seconds: Optional[int] = None
    read_transport_sse_timeout_seconds: Optional[int] = 300
    headers: Optional[str] = "{}"
    api_key: Optional[str] = ""
    # Updated env field type
    env: Optional[Dict[str, EnvVarDetail]] = Field(default_factory=dict)
    roots_table: Optional[str] = ""
    repo_url: Optional[str] = None
    docker_image_name_suggestion: Optional[str] = None
    has_dockerfile: Optional[bool] = False
    deploy_as_container: Optional[bool] = False
    is_external_config: Optional[bool] = False # New field
    container_args_template: Optional[Dict[str, Any]] = Field(default_factory=dict) # Was string, now dict from parsing
    container_args_user: Optional[Dict[str, str]] = Field(default_factory=dict)
    deployment_status: Optional[str] = "not_deployed" # New field for deployment status
    # New fields for persisting deployment settings
    image_name_override: Optional[str] = None
    host_port_mapping: Optional[int] = None
    actual_container_port: Optional[int] = None
    last_build_attempt_local: Optional[bool] = None
    last_push_attempt_registry: Optional[bool] = None
    last_deployment_used_compose: Optional[bool] = None
    # MCP testing fields
    test_status: Optional[str] = "pending"  # pending, running, completed, failed
    test_results: Optional[Dict[str, Any]] = Field(default_factory=dict)
    last_tested_at: Optional[str] = None  # ISO timestamp
    tools_discovered: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    test_success_rate: Optional[float] = None

class RepositoryCreate(RepositoryBase):
    repo_url: str # For Git repos, this is the clone URL. For external, it's external://<name>

class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    transport: Optional[str] = None
    url: Optional[str] = None
    read_timeout_seconds: Optional[int] = None
    read_transport_sse_timeout_seconds: Optional[int] = None
    headers: Optional[str] = None # JSON string for headers
    api_key: Optional[str] = None
    env: Optional[Dict[str, EnvVarDetail]] = None
    roots_table: Optional[str] = None
    repo_url: Optional[str] = None # Should generally not be updated directly, esp. for external.
    has_dockerfile: Optional[bool] = None
    deploy_as_container: Optional[bool] = None
    is_external_config: Optional[bool] = None
    container_args_template: Optional[Dict[str, Any]] = None
    container_args_user: Optional[Dict[str, str]] = None
    deployment_status: Optional[str] = None

class Repository(RepositoryBase):
    id: int
    
    class Config:
        from_attributes = True

class RepositoryInDB(Repository):
    pass

class ServerRoot(BaseModel):
    server_name: str
    uri: str
    name: Optional[str] = None
    server_uri_alias: Optional[str] = None 

# New model for the finalize-deployment endpoint
class FinalizeDeploymentRequest(BaseModel):
    original_repo_name: str # The name given by the user on ReviewRepository page
    original_repo_url: Optional[str] = None # Original Git URL, if applicable
    description: Optional[str] = None
    
    deployed_image_name: Optional[str] = None # Actual image name used (could be from Dockerfile, compose, or user input)
    deployed_container_id_or_project_name: Optional[str] = None # Container ID (single) or Docker Compose project name
    
    host_port: Optional[int] = None # The host port the container/service is exposed on
    mcp_container_port: Optional[int] = None # The internal port MCP listens on (e.g. 8999)
    mcp_path: Optional[str] = "/mcp" # Path for the MCP endpoint, e.g. /mcp, /mcp/v1

    final_env_vars: Optional[Dict[str, str]] = Field(default_factory=dict) # Effective env vars used for deployment
    deployment_type: str # e.g., "dockerfile", "compose", "local_command"
    
    # Include fields that might be useful for re-deployment or info, even if not directly used for external URL
    command_suggestion: Optional[str] = None # Original command suggestion from GPT (if any)
    args_suggestion: Optional[List[str]] = Field(default_factory=list) # Original args suggestion
    has_dockerfile: Optional[bool] = False
    has_docker_compose: Optional[bool] = False
    dockerfile_content: Optional[str] = None # Could be large, maybe store hash or path if too big for DB directly 

class DeployContainerRequest(BaseModel):
    image_name: Optional[str] = None # Optional if using docker-compose
    container_args: Optional[Dict[str, str]] = Field(default_factory=dict)
    env_vars: Optional[Dict[str, EnvVarDetail]] = Field(default_factory=dict)
    attempt_local_build: Optional[bool] = True
    attempt_push_to_registry: Optional[bool] = False
    use_docker_compose: Optional[bool] = False # New field to indicate compose usage
    host_port_mapping: Optional[int] = None # The host port selected by the user
    actual_container_port: Optional[int] = None # The container port it's mapped to 