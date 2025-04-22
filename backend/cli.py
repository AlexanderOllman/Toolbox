#!/usr/bin/env python
"""
CLI tool for Toolbox - MCP Server Manager
"""

import argparse
import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.config_service import generate_yaml_config, get_default_config_path
from app.services.database import get_repositories


def generate_yaml_command(args):
    """Generate YAML configuration file."""
    output_path = args.output or get_default_config_path()
    yaml_str = generate_yaml_config(output_path)
    if args.print:
        print(yaml_str)


def list_repos_command(args):
    """List all repositories."""
    repositories = get_repositories()
    
    if not repositories:
        print("No repositories found.")
        return
    
    print(f"Found {len(repositories)} repositories:")
    for idx, repo in enumerate(repositories, 1):
        print(f"\n{idx}. {repo['name']}")
        print(f"   Description: {repo['description']}")
        print(f"   Command: {repo['command']}")
        print(f"   Args: {', '.join(repo['args']) if repo['args'] else 'None'}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Toolbox - MCP Server Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Generate YAML command
    generate_parser = subparsers.add_parser("generate-yaml", help="Generate YAML configuration")
    generate_parser.add_argument("-o", "--output", help="Output file path")
    generate_parser.add_argument("-p", "--print", action="store_true", help="Print YAML to stdout")
    
    # List repositories command
    list_parser = subparsers.add_parser("list", help="List all repositories")
    
    args = parser.parse_args()
    
    if args.command == "generate-yaml":
        generate_yaml_command(args)
    elif args.command == "list":
        list_repos_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 