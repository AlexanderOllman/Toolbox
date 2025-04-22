import sqlite3
import json
from typing import List, Dict, Any, Optional
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mcp_servers.db')

def get_connection():
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize the database with required tables."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS servers (
            name TEXT PRIMARY KEY,
            description TEXT,
            command TEXT,
            args TEXT
        )
        '''
    )
    conn.commit()
    conn.close()

def get_repositories() -> List[Dict[str, Any]]:
    """Get all repositories from the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT name, description, command, args FROM servers')
    rows = c.fetchall()
    conn.close()
    
    repositories = []
    for idx, (name, description, command, args_json) in enumerate(rows):
        args = json.loads(args_json) if args_json else []
        repositories.append({
            "id": idx + 1,
            "name": name,
            "description": description,
            "command": command,
            "args": args
        })
    return repositories

def get_repository(name: str) -> Optional[Dict[str, Any]]:
    """Get a repository by name."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT name, description, command, args FROM servers WHERE name = ?', (name,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    name, description, command, args_json = row
    args = json.loads(args_json) if args_json else []
    return {
        "id": 1,  # This would be replaced with a real ID in a proper DB
        "name": name,
        "description": description,
        "command": command,
        "args": args
    }

def add_repository(name: str, description: str, command: str, args: List[str]) -> Dict[str, Any]:
    """Add a repository to the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'INSERT OR REPLACE INTO servers (name, description, command, args) VALUES (?, ?, ?, ?)',
        (name, description, command, json.dumps(args))
    )
    conn.commit()
    conn.close()
    
    return {
        "id": 1,  # This would be replaced with a real ID in a proper DB
        "name": name,
        "description": description,
        "command": command,
        "args": args
    }

def delete_repository(name: str) -> bool:
    """Delete a repository by name."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM servers WHERE name = ?', (name,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# Initialize database on module load
init_db() 