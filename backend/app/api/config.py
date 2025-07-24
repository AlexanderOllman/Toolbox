from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
import stat
import json
import yaml

from app.services.database import get_repositories
from app.services.config_service import (
    generate_yaml_config, 
    get_default_config_path, 
    get_config_value, 
    set_config_value, 
    get_all_config,
    _build_server_config_entry
)
from app.services.vector_db_service import get_qdrant_client, init_vector_db, check_qdrant_connection

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

class ConfigItem(BaseModel):
    key: str
    value: str

class ConfigUpdateRequest(BaseModel):
    items: List[ConfigItem]

# Custom Dumper to force block style for all dictionaries
class BlockStyleDumper(yaml.SafeDumper):
    def represent_dict_as_block(self, data):
        return self.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)

BlockStyleDumper.add_representer(dict, BlockStyleDumper.represent_dict_as_block)

@router.get("/yaml", response_class=PlainTextResponse)
async def get_yaml_config():
    """Generate YAML configuration for MCP servers."""
    repositories = get_repositories()
    config_data = generate_yaml_config(repositories=repositories)
    # Use the custom dumper and ensure default_flow_style=False at the top level as well
    yaml_str = yaml.dump(config_data, Dumper=BlockStyleDumper, sort_keys=False, default_flow_style=False, indent=2)
    return yaml_str

@router.get("/json")
async def get_json_config() -> Dict[str, Any]:
    """Generate JSON configuration for MCP servers."""
    repositories = get_repositories()
    servers = {}
    
    for repo in repositories:
        server_entry_config = _build_server_config_entry(repo)
        if server_entry_config is not None and repo.get("name"):
            servers[repo["name"]] = server_entry_config
    
    return {"mcp": {"servers": servers}}

@router.post("/generate", status_code=200)
async def generate_config_file(background_tasks: BackgroundTasks, output_path: Optional[str] = None):
    """Generate and save YAML (or JSON if extension is .json) configuration file."""
    
    file_path = output_path or get_default_config_path()
    
    repositories = get_repositories()
    
    background_tasks.add_task(generate_yaml_config, repositories=repositories, output_path=file_path)
    
    return {"message": f"Configuration file generation to '{os.path.basename(file_path)}' started", "file_path": file_path}

@router.get("/download")
async def download_config_file():
    """Download the generated YAML configuration file."""
    file_path = get_default_config_path()
    
    if not os.path.exists(file_path):
        # Generate on-the-fly if it doesn't exist
        generate_yaml_config(file_path)
    
    return FileResponse(
        path=file_path,
        filename="mcp_servers.yaml",
        media_type="application/x-yaml"
    ) 

@router.get("/settings")
async def get_settings():
    """Get all configuration settings."""
    config = get_all_config()
    
    # Add Qdrant connection status
    connection_status = check_qdrant_connection()
    # Ensure connection_status is a dict and 'status' key exists
    if isinstance(connection_status, dict) and "status" in connection_status:
        config["QDRANT_STATUS"] = connection_status["status"]
    else:
        config["QDRANT_STATUS"] = "error" # Default to error if status is not as expected
        logger.error(f"Unexpected Qdrant connection status format: {connection_status}")
    
    return config

@router.post("/settings")
async def update_settings(config: ConfigUpdateRequest):
    """Update configuration settings."""
    logger.info(f"Received settings update: {config.items}")
    
    # Keep track of which settings changed
    changed_settings = []
    
    for item in config.items:
        # Get current value
        current_value = get_config_value(item.key, "")
        
        # Only update if value has changed
        if current_value != item.value:
            logger.info(f"Updating {item.key} from '{current_value}' to '{item.value}'")
            set_config_value(item.key, item.value)
            changed_settings.append(item.key)
        else:
            logger.info(f"Skipping unchanged setting {item.key}={item.value}")
    
    # After updating, check the connection status with the new settings
    connection_status = check_qdrant_connection()
    logger.info(f"Current connection status after update: {connection_status}")
    
    return {
        "message": "Settings updated successfully",
        "updated_settings": changed_settings,
        "connection_status": connection_status
    }

@router.get("/test-qdrant")
async def test_qdrant_connection():
    """Test connection to Qdrant server."""
    # Log current settings
    host = get_config_value("QDRANT_HOST", "localhost")
    port = get_config_value("QDRANT_PORT", "6333")
    collection_name = get_config_value("COLLECTION_NAME", "mcp_servers")
    logger.info(f"Testing connection with settings: host={host}, port={port}, collection={collection_name}")
    
    connection_status = check_qdrant_connection()
    
    logger.info(f"Connection test result: {connection_status}")
    
    return {
        "status": "success" if connection_status["status"] == "connected" else "error",
        "message": connection_status["message"],
        "settings": {
            "host": host,
            "port": port,
            "collection": collection_name
        }
    }

@router.get("/qdrant-status")
async def get_qdrant_status():
    """Get current Qdrant connection status."""
    return check_qdrant_connection()

@router.get("/collection-status")
async def get_collection_status():
    """Check if Qdrant collections exist and are accessible."""
    try:
        from app.services.vector_db_service import get_qdrant_client, get_collection_name
        
        # First check if we can connect to Qdrant
        connection_status = check_qdrant_connection()
        if connection_status["status"] != "connected":
            return {
                "status": "disconnected",
                "message": f"Cannot connect to Qdrant: {connection_status['message']}"
            }
        
        # Check if collection exists
        client = get_qdrant_client()
        collection_name = get_collection_name()
        
        if client.collection_exists(collection_name):
            # Get collection info to verify it's properly configured
            collection_info = client.get_collection(collection_name)
            return {
                "status": "connected",
                "message": f"Collection '{collection_name}' exists and is accessible",
                "collection_name": collection_name,
                "vector_count": collection_info.points_count if hasattr(collection_info, 'points_count') else 0
            }
        else:
            return {
                "status": "missing",
                "message": f"Collection '{collection_name}' does not exist",
                "collection_name": collection_name
            }
            
    except Exception as e:
        logger.error(f"Error checking collection status: {str(e)}")
        return {
            "status": "error",
            "message": f"Error checking collection status: {str(e)}"
        }

@router.post("/initialize-collections")
async def initialize_collections():
    """Initialize Qdrant collections."""
    try:
        from app.services.vector_db_service import init_vector_db, get_collection_name
        
        logger.info("Initializing vector database...")
        success = init_vector_db()
        
        collection_name = get_collection_name()

        if success:
            return {
                "status": "success",
                "message": f"Collections initialized successfully! Collection '{collection_name}' is ready.",
                "collection_name": collection_name
            }
        else:
            return {
                "status": "error",
                "message": f"Vector database initialization failed. Check Qdrant connection."
            }
            
    except Exception as e:
        logger.error(f"Error initializing collections: {str(e)}")
        return {
            "status": "error",
            "message": f"Error initializing collections: {str(e)}"
        }

@router.get("/docker-status")
async def get_docker_status():
    """Check Docker connectivity status."""
    docker_socket_path = "/var/run/docker.sock"
    try:
        if os.path.exists(docker_socket_path):
            stat_info = os.stat(docker_socket_path)
            # Check if it is a socket file
            # Use stat.S_ISSOCK for portability
            if stat.S_ISSOCK(stat_info.st_mode):
                logger.info(f"Docker socket found at {docker_socket_path}")
                return JSONResponse(content={
                    "status": "available", 
                    "method": "socket", 
                    "message": f"Docker socket available at {docker_socket_path}"
                })
            else:
                logger.warning(f"{docker_socket_path} exists but is not a socket.")
                # Fall through to check CONTAINER_HOST
        else:
            logger.info(f"Docker socket not found at {docker_socket_path}")
            # Fall through to check CONTAINER_HOST

        container_host = get_config_value("CONTAINER_HOST", None)
        if container_host:
            logger.info(f"Docker socket not found, but CONTAINER_HOST is set to: {container_host}")
            # Here you could implement a remote Docker check if desired in the future.
            # For now, we indicate it's configured but not actively checked remotely by this status endpoint.
            return JSONResponse(content={
                "status": "misconfigured", # Or 'available' if you implement a remote check
                "method": "remote_configured", 
                "message": f"Docker socket not found. Remote host {container_host} is configured. Remote connectivity test not implemented in this status check."
            })
        else:
            logger.info("Docker socket not found and CONTAINER_HOST is not configured.")
            return JSONResponse(content={
                "status": "unavailable", 
                "message": "Docker socket not found and no remote Container Host configured."
            })

    except Exception as e:
        logger.error(f"Error checking Docker status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"An error occurred: {str(e)}"}
        ) 