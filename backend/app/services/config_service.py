import os
import yaml
import sqlite3
import logging
from typing import Dict, Any, Optional
from app.services.database import get_repositories, get_connection

# Set up logging
logger = logging.getLogger(__name__)

def generate_yaml_config(output_path=None):
    """Generate YAML configuration for MCP servers.
    
    Args:
        output_path: Optional path to write the YAML file. If None, only returns the YAML string.
        
    Returns:
        str: The YAML configuration as a string
    """
    repositories = get_repositories()
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

def init_config_table():
    """Initialize the configuration table in the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        '''
    )
    
    # Insert default values if they don't exist
    default_config = {
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")
    }
    
    for key, value in default_config.items():
        c.execute(
            '''
            INSERT OR IGNORE INTO config (key, value) 
            VALUES (?, ?)
            ''',
            (key, value)
        )
    
    conn.commit()
    conn.close()

def get_config_value(key: str, default: str = None) -> str:
    """Get a configuration value from the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    
    value = row[0] if row else default
    logger.debug(f"Retrieved config {key}={value}")
    return value

def set_config_value(key: str, value: str) -> None:
    """Set a configuration value in the database."""
    logger.info(f"Setting config {key}={value}")
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)',
        (key, value)
    )
    conn.commit()
    conn.close()
    logger.info(f"Saved config {key}={value}")

def get_all_config() -> Dict[str, str]:
    """Get all configuration values from the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM config')
    rows = c.fetchall()
    conn.close()
    
    return {key: value for key, value in rows}

# Initialize config table on module load
init_config_table() 