import os
import yaml
import json
import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Path to config file
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mcp_config.json')

def generate_yaml_config(repositories=None, output_path=None):
    """Generate YAML configuration for MCP servers.
    
    Args:
        repositories: List of repository dictionaries. If None, caller must get repositories.
        output_path: Optional path to write the YAML file. If None, only returns the YAML string.
        
    Returns:
        str: The YAML configuration as a string
    """
    # repositories must be passed in from outside to avoid circular imports
    if repositories is None:
        logger.warning("No repositories provided to generate_yaml_config")
        repositories = []
        
    servers = {}
    
    for repo in repositories:
        servers[repo["name"]] = {
            "command": repo["command"],
            "args": repo["args"]
        }
    
    data = {"mcp": {"servers": servers}}
    yaml_str = yaml.dump(data, sort_keys=False)
    
    # If output path is provided, write to file
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_str)
        print(f"Wrote configuration to {output_path}.")
    
    return yaml_str

def get_default_config_path():
    """Get the default path for the YAML configuration file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mcp_servers.yaml') 

def load_config():
    """Load configuration from the JSON file."""
    if not os.path.exists(CONFIG_FILE_PATH):
        # Return default config if file doesn't exist
        return {
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "6333",
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "COLLECTION_NAME": "mcp_servers"
        }
    
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        # Return default config on error
        return {
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "6333",
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "COLLECTION_NAME": "mcp_servers"
        }

def save_config(config):
    """Save configuration to the JSON file."""
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")

def init_config():
    """Initialize the configuration file with default values if it doesn't exist."""
    if not os.path.exists(CONFIG_FILE_PATH):
        # Create default config
        default_config = {
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "6333",
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "COLLECTION_NAME": "mcp_servers"
        }
        save_config(default_config)
        logger.info(f"Created default config at {CONFIG_FILE_PATH}")

def get_config_value(key: str, default: str = None) -> str:
    """Get a configuration value."""
    config = load_config()
    value = config.get(key, default)
    logger.debug(f"Retrieved config {key}={value}")
    return value

def set_config_value(key: str, value: str) -> None:
    """Set a configuration value."""
    logger.info(f"Setting config {key}={value}")
    config = load_config()
    config[key] = value
    save_config(config)
    logger.info(f"Saved config {key}={value}")

def get_all_config() -> Dict[str, str]:
    """Get all configuration values."""
    return load_config()

# Initialize config on module load
init_config() 