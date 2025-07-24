import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List
import re # Import re for parsing repo URL
from sqlalchemy.orm import Session
from app.models.repositories import Repository

# Set up logging
logger = logging.getLogger(__name__)

# Path to config file
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mcp_config.json')

def get_docker_aware_qdrant_host():
    """Returns 'host.docker.internal' if IN_DOCKER env var is set, else 'localhost'."""
    if os.getenv("IN_DOCKER", "false").lower() == "true":
        logger.info("IN_DOCKER is true, defaulting QDRANT_HOST to host.docker.internal")
        return "host.docker.internal"
    logger.info("Not in Docker or IN_DOCKER not true, defaulting QDRANT_HOST to localhost")
    return "localhost"

def _parse_image_name(repo_url: Optional[str], repo_name: Optional[str]) -> str:
    """Helper to derive a Docker image name from repo URL and name."""
    default_image = f"{repo_name or 'unknown'}:latest"
    if not repo_url:
        return default_image

    # Try to extract owner/repo from common Git URL patterns
    match = re.search(r'github\.com[/:]([^/]+)/([^/.]+)(\.git)?', repo_url, re.IGNORECASE)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        return f"{owner}/{repo}:latest"
    
    # Fallback to repo name if parsing fails
    return default_image

def _process_env(raw_env_list: List[Any]) -> Dict[str, Any]:
    env = {}
    if isinstance(raw_env_list, list):
        for item in raw_env_list:
            if isinstance(item, dict) and 'name' in item and 'value' in item:
                env[item['name']] = item['value'] # Preserves None values if present
            elif isinstance(item, str) and '=' in item: # Basic "KEY=VALUE" string format
                k, v = item.split('=', 1)
                env[k] = v
    return env

def _build_server_config_entry(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    entry = {}
    
    if repo_data.get('is_external_config'):
        transport_val = repo_data.get('transport')
        url_val = repo_data.get('url')

        # External configs must have transport and url
        entry['transport'] = transport_val if transport_val is not None else "sse"
        entry['url'] = url_val if url_val is not None else "" # API layer should validate non-empty URL

        if not url_val:
            logger.warning(f"External repository '{repo_data.get('name')}' has an empty or missing URL.")

        headers_str = repo_data.get('headers')
        if headers_str and headers_str.strip() != "{}": # Process only if headers_str is truthy and not an empty JSON object
            try:
                headers = json.loads(headers_str)
                if isinstance(headers, dict) and headers: # Add only if the parsed dictionary is not empty
                    entry['headers'] = headers
            except json.JSONDecodeError:
                logger.warning(f"Could not parse headers JSON for external repo {repo_data.get('name')}: {headers_str}")
        
        current_transport = entry.get('transport')
        if current_transport == 'sse':
            timeout_val = repo_data.get('read_transport_sse_timeout_seconds')
            if isinstance(timeout_val, int): # Add timeout only if transport is 'sse' and timeout_val is a valid integer
                entry['read_transport_sse_timeout_seconds'] = timeout_val
            # If timeout_val is not an int or not present, it won't be added, matching user reference (optional)
        
        # Remove any keys that ended up with None or empty string if they are not essential for all external types
        # For example, if url was defaulted to "" but should not be there if truly empty.
        # However, for this structure, transport and url are always expected.
        # Headers and timeout are optional.
        return entry

    elif repo_data.get('deploy_as_container'):
        command = repo_data.get('command')
        if not command: # Container command must exist
            return {}

        entry['command'] = command
        entry['args'] = repo_data.get('args', [])
        
        env_list = repo_data.get('env', [])
        processed_env = _process_env(env_list)
        if processed_env:
            entry['env'] = processed_env
        
        return {k: v for k, v in entry.items() if v is not None} # Clean Nones

    else: # Default to local execution
        command = repo_data.get('command')
        if not command: # Command must exist and be non-empty for local execution
            return {} # Invalid entry if command is None or ""

        entry['command'] = command
        entry['args'] = repo_data.get('args', []) 
        
        env_list = repo_data.get('env', [])
        processed_env = _process_env(env_list)
        if processed_env:
            entry['env'] = processed_env
        
        return entry # Already filtered by non-empty command, args default to [], env is optional

def generate_yaml_config(repositories=None, output_path=None):
    """Generate YAML configuration for MCP servers.
    
    Args:
        repositories: List of repository dictionaries. If None, caller must get repositories.
        output_path: Optional path to write the YAML file. If None, only returns the YAML string.
        
    Returns:
        str: The YAML configuration as a string
    """
    if repositories is None:
        logger.warning("No repositories provided to generate_yaml_config")
        repositories = []
        
    servers = {}
    
    for repo in repositories:
        server_entry_config = _build_server_config_entry(repo)
        if server_entry_config is not None and repo.get("name"):
            servers[repo["name"]] = server_entry_config

    # Format for the final output structure (mcp -> servers)
    # Use mcpServers key to match the user's requested format
    data = {"mcp": {"servers": servers}}
    # Use default_flow_style=False to force block style for all dictionaries
    yaml_str = yaml.dump(data, sort_keys=False, default_flow_style=False, indent=2)
    
    if output_path:
        # Determine if output is JSON or YAML based on extension
        _, ext = os.path.splitext(output_path)
        is_json = ext.lower() == '.json'
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                    if is_json:
                        json.dump(data, f, indent=2) # Use json.dump for JSON
                    else:
                        f.write(yaml_str) # Write the YAML string
            logger.info(f"Wrote configuration to {output_path}.")
        except Exception as e:
            logger.error(f"Failed to write configuration to {output_path}: {e}")
    
    # Return the dictionary data structure as well, useful for JSON output or further processing
    return data

def get_default_config_path():
    """Get the default path for the YAML configuration file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mcp_servers.yaml') 

def load_config():
    """Load configuration from the JSON file, ensuring existing values are respected."""
    default_qdrant_host = get_docker_aware_qdrant_host()
    default_base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # These are the absolute defaults for a fresh setup
    base_defaults = {
        "QDRANT_HOST": default_qdrant_host,
        "QDRANT_PORT": "6333",
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "COLLECTION_NAME": "mcp_servers",
        "MCP_REPO_PATH": default_base_path
    }

    if not os.path.exists(CONFIG_FILE_PATH):
        logger.info(f"Config file {CONFIG_FILE_PATH} not found. Creating with defaults.")
        save_config(base_defaults)
        return base_defaults
    
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            loaded_values = json.load(f)

        # Start with the defaults, then merge the loaded config on top.
        # This ensures all keys are present.
        config = base_defaults.copy()
        config.update(loaded_values)

        # Special handling for empty but present keys that should use a default.
        # If QDRANT_HOST is present but empty, use the Docker-aware default.
        if 'QDRANT_HOST' in loaded_values and not loaded_values['QDRANT_HOST']:
            config['QDRANT_HOST'] = default_qdrant_host
            logger.info("QDRANT_HOST was empty, applying Docker-aware default.")
            
        # If MCP_REPO_PATH is present but empty, use the default path.
        if 'MCP_REPO_PATH' in loaded_values and not loaded_values['MCP_REPO_PATH']:
            config['MCP_REPO_PATH'] = default_base_path
            logger.info("MCP_REPO_PATH was empty, applying default path.")

        # If OPENAI_API_KEY is empty in the file, try to load from environment
        if 'OPENAI_API_KEY' in loaded_values and not loaded_values['OPENAI_API_KEY']:
            env_api_key = os.getenv("OPENAI_API_KEY")
            if env_api_key:
                config['OPENAI_API_KEY'] = env_api_key
                logger.info("OPENAI_API_KEY from file was empty, using value from environment variable.")

        # Save the potentially corrected config back to the file
        save_config(config)

        return config
        
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error loading or parsing config from {CONFIG_FILE_PATH}: {str(e)}. Overwriting with safe defaults.")
        save_config(base_defaults)
        return base_defaults
    except Exception as e:
        logger.error(f"An unexpected error occurred loading config: {str(e)}. Returning defaults.")
        return base_defaults

def save_config(config):
    """Save configuration to the JSON file."""
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")

def init_config():
    """Initialize the configuration file by calling load_config."""
    load_config()

def get_config_value(key: str, default: Any = None) -> Any:
    """Get a specific value from the config."""
    config = load_config()
    value = config.get(key)
    if value is None:
        # logger.debug(f"Config key '{key}' not found, returning provided default: '{default}'")
        return default
    # logger.debug(f"Retrieved config {key}={value}") # Too noisy for every get
    return value

def get_mcp_repo_path():
    """Get the MCP repository path with fallback to default."""
    # Get the path from config, or default to the working parent directory (Toolbox) if not set
    default_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = get_config_value("MCP_REPO_PATH", default_path)
    # Create the directory if it doesn't exist
    os.makedirs(path, exist_ok=True)
    return path

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

def generate_json_config(db: Session) -> Dict[str, Any]:
    repos_db = db.query(Repository).all()
    servers = {}
    for repo_model in repos_db:
        repo_dict = {c.name: getattr(repo_model, c.name) for c in repo_model.__table__.columns}

        env_value = repo_dict.get('env')
        if isinstance(env_value, str):
            try:
                parsed_env = json.loads(env_value)
                if isinstance(parsed_env, list):
                    repo_dict['env'] = parsed_env
                else:
                    repo_dict['env'] = []
            except json.JSONDecodeError:
                repo_dict['env'] = []
        elif env_value is None:
             repo_dict['env'] = []
        
        server_config_entry = _build_server_config_entry(repo_dict)
        if server_config_entry: # Add only if valid
            servers[repo_model.name] = server_config_entry
            
    return {"mcp": {"servers": servers}} 