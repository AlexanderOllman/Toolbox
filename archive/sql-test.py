# add_server.py
import os
import subprocess
import sqlite3
import json
from openai import OpenAI
import re
import tiktoken


def clone_repo(repo_url, base_dir=None):
    if base_dir is None:
        base_dir = os.path.join(os.path.expanduser('~'), 'mcp')
    os.makedirs(base_dir, exist_ok=True)
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git','')
    dest = os.path.join(base_dir, repo_name)
    if not os.path.exists(dest):
        subprocess.run(['git', 'clone', repo_url, dest], check=True)
    return repo_name, dest


def extract_readme(repo_path):
    for fname in ['README.md', 'README.rst', 'README']:
        path = os.path.join(repo_path, fname)
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    return ''


def count_tokens(text, model="gpt-4o"):
    """Count tokens for a given text string using the appropriate tokenizer."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")  # Default encoding for newer models
        return len(encoding.encode(text))


def get_model_cost(model, prompt_tokens, completion_tokens):
    """Get estimated cost for token usage with specified model."""
    costs = {
        "gpt-4.1-nano": {
            "prompt": 0.0001,  # $0.10 per 1k tokens
            "completion": 0.0003,  # $0.30 per 1k tokens
        }
    }
    
    if model not in costs:
        return 0.0
    
    model_costs = costs[model]
    prompt_cost = (prompt_tokens / 1000) * model_costs["prompt"]
    completion_cost = (completion_tokens / 1000) * model_costs["completion"]
    
    return prompt_cost + completion_cost


def get_repo_info_from_gpt(readme_text):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = (
        f"""Based on the following README, extract:
1. A concise description of the repository's purpose and functionality
2. The command needed to run this project
3. The arguments for that command. If any arguments reference a source directory, make it the "mcp" directory in the relative path.

Return your answer in JSON format with these keys:
- "description": the repository description
- "command": the main command to run the repository
- "args": an array of arguments to pass to the command

README:
{readme_text}"""
    )
    
    model = 'gpt-4.1-nano'
    prompt_tokens = count_tokens(prompt, model)
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        response_format={"type": "json_object"}
    )
    
    completion_tokens = resp.usage.completion_tokens if hasattr(resp, 'usage') and hasattr(resp.usage, 'completion_tokens') else 0
    total_tokens = prompt_tokens + completion_tokens
    cost = get_model_cost(model, prompt_tokens, completion_tokens)
    
    print(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
    print(f"Estimated cost: ${cost:.6f}")
    
    try:
        result = json.loads(resp.choices[0].message.content.strip())
        return result
    except json.JSONDecodeError:
        # Fallback if response isn't valid JSON
        content = resp.choices[0].message.content.strip()
        print(f"Error parsing JSON response: {content}")
        return {
            "description": content,
            "command": None,
            "args": []
        }


def init_db(db_path='mcp_servers.db'):
    conn = sqlite3.connect(db_path)
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
    return conn


def add_server_entry(conn, name, description, command, args):
    c = conn.cursor()
    c.execute(
        'INSERT OR REPLACE INTO servers (name, description, command, args) VALUES (?, ?, ?, ?)',
        (name, description, command, json.dumps(args))
    )
    conn.commit()


def main():
    repo_url = input("Enter a Repo: ").strip()
    if not repo_url:
        print("No repository URL provided. Exiting.")
        return

    name, repo_path = clone_repo(repo_url)
    readme = extract_readme(repo_path)
    if not readme:
        print(f"README not found in {name}.")
        return

    repo_info = get_repo_info_from_gpt(readme)
    
    description = repo_info.get("description", "No description available")
    command = repo_info.get("command")
    args = repo_info.get("args", [])
    
    if not command:
        print("Could not extract run command from README.")
        return

    conn = init_db()
    add_server_entry(conn, name, description, command, args)
    conn.close()

    print(f"Added server '{name}' with command '{command}' and args {args} to database.")


if __name__ == '__main__':
    main()

