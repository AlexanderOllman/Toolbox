from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.services.database import get_repositories
from app.services.config_service import (
    generate_yaml_config, 
    get_default_config_path, 
    get_config_value, 
    set_config_value, 
    get_all_config
)
from app.services.vector_db_service import get_qdrant_client, init_vector_db, check_qdrant_connection

router = APIRouter()

class ConfigItem(BaseModel):
    key: str
    value: str

class ConfigUpdateRequest(BaseModel):
    items: List[ConfigItem]

@router.get("/yaml", response_class=PlainTextResponse)
async def get_yaml_config():
    """Generate YAML configuration for MCP servers."""
    yaml_str = generate_yaml_config()
    return yaml_str

@router.get("/json")
async def get_json_config() -> Dict[str, Any]:
    """Generate JSON configuration for MCP servers."""
    repositories = get_repositories()
    servers = {}
    
    for repo in repositories:
        servers[repo["name"]] = {
            "command": repo["command"],
            "args": repo["args"]
        }
    
    return {"mcp": {"servers": servers}}

@router.post("/generate", status_code=201)
async def generate_config_file(background_tasks: BackgroundTasks, output_path: Optional[str] = None):
    """Generate and save YAML configuration file.
    
    Args:
        output_path: Optional custom path to write the config. If not provided, uses default path.
        
    Returns:
        Dict with the path where the file was saved
    """
    file_path = output_path or get_default_config_path()
    
    # Use background task to generate the file
    background_tasks.add_task(generate_yaml_config, file_path)
    
    return {"message": "Configuration file generation started", "file_path": file_path}

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
    config["QDRANT_STATUS"] = connection_status["status"]
    
    return config

@router.post("/settings")
async def update_settings(config: ConfigUpdateRequest):
    """Update configuration settings."""
    for item in config.items:
        set_config_value(item.key, item.value)
    
    # Reinitialize vector DB with new settings if they change
    if any(item.key in ["QDRANT_HOST", "QDRANT_PORT"] for item in config.items):
        try:
            init_vector_db()
        except Exception as e:
            return {"message": f"Settings updated but vector DB initialization failed: {str(e)}"}
    
    return {"message": "Settings updated successfully"}

@router.get("/test-qdrant")
async def test_qdrant_connection():
    """Test connection to Qdrant server."""
    connection_status = check_qdrant_connection()
    return {
        "status": "success" if connection_status["status"] == "connected" else "error",
        "message": connection_status["message"]
    }

@router.get("/qdrant-status")
async def get_qdrant_status():
    """Get current Qdrant connection status."""
    return check_qdrant_connection() 