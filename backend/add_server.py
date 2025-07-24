#!/usr/bin/env python
"""
Add a repository to the MCP Server Manager database.
This script replicates the functionality of the original sql-test.py
"""

import os
import sys
import subprocess
import argparse

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.openai_service import get_repo_info_from_gpt
from app.services.database import add_repository, init_db
from app.services.config_service import get_mcp_repo_path


def clone_repo(repo_url, base_dir=None):
    """Clone a Git repository if it doesn't already exist."""
    if base_dir is None:
        base_dir = get_mcp_repo_path()
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
    dest = os.path.join(base_dir, repo_name)
    
    if not os.path.exists(dest):
        print(f"Cloning repository {repo_url}...")
        subprocess.run(['git', 'clone', repo_url, dest], check=True)
    else:
        print(f"Repository already exists at {dest}, skipping clone.")
    
    return repo_name, dest


def extract_readme(repo_path):
    """Extract README content from repository."""
    for fname in ['README.md', 'README.rst', 'README']:
        path = os.path.join(repo_path, fname)
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    return ''


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Add a repository to MCP Server Manager")
    parser.add_argument("repo_url", nargs="?", help="URL of the Git repository to add")
    parser.add_argument("--name", help="Custom name for the repository (defaults to repo name)")
    parser.add_argument("--description", help="Custom description for the repository")
    parser.add_argument("--command", help="Custom command for the repository")
    parser.add_argument("--args", nargs="+", help="Custom arguments for the command")
    
    args = parser.parse_args()
    
    # Initialize the database
    init_db()
    
    # If no repo URL provided, prompt the user
    repo_url = args.repo_url
    if not repo_url:
        repo_url = input("Enter a Repo: ").strip()
        if not repo_url:
            print("No repository URL provided. Exiting.")
            return
    
    try:
        # Clone the repository
        name, repo_path = clone_repo(repo_url)
        custom_name = args.name or name
        
        # Extract README
        readme = extract_readme(repo_path)
        if not readme:
            print(f"README not found in {name}.")
            if not args.description and not args.command:
                print("No README found and no custom description/command provided. Exiting.")
                return
        
        # Get repository info from GPT or use provided values
        if args.description and args.command:
            # Use provided values
            description = args.description
            command = args.command
            arguments = args.args or []
            
            print("Using provided repository information.")
        else:
            # Try to extract info from README using GPT
            print("Analyzing README with GPT...")
            repo_info = get_repo_info_from_gpt(readme)
            
            description = args.description or repo_info.get("description", "No description available")
            command = args.command or repo_info.get("command")
            arguments = args.args or repo_info.get("args", [])
            
            if not command:
                print("Could not extract run command from README.")
                command = input("Enter command: ").strip()
        
        # Construct the data dictionary for the add_repository service
        repo_data_dict = {
            "name": custom_name,
            "description": description,
            "command": command,
            "args": arguments,
            "repo_url": repo_url,
            # Add default values for other fields based on RepositoryBase model
            "transport": "stdio",
            "url": "",
            "read_timeout_seconds": None,
            "read_transport_sse_timeout_seconds": 300,
            "headers": "{}",
            "api_key": "",
            "env": {},
            "roots_table": ""
        }

        # Add to database using the dictionary
        add_repository(repo_data_dict)

        print(f"Added server '{custom_name}' with command '{command}' and args {arguments} to database.")
        
        # Note: Automatic testing is not triggered from CLI tool since it doesn't have
        # FastAPI background tasks. Users can trigger tests via the web interface or API.
    
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 