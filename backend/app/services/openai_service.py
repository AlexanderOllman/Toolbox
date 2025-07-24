import json
import tiktoken
from openai import OpenAI
import os
from app.services.config_service import get_config_value

# Initialize OpenAI client - use API key from config or fallback to environment variable
api_key = get_config_value("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

# Initialize client only if API key is available
client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized.")
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}. OpenAI features will be disabled.")
        client = None # Ensure client is None if initialization fails
else:
    print("OPENAI_API_KEY not found in config or environment. OpenAI features will be disabled.")

def count_tokens(text, model="gpt-4"):
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

def get_repo_info_from_gpt(readme_text, dockerfile_text=None):
    """Extract repository information from README and optionally Dockerfile text using GPT."""
    
    if not client:
        print("OpenAI client not available. Skipping GPT processing for repo info.")
        return {
            "description": "OpenAI features disabled (API key not configured). Repository content not analyzed.",
            "command": None,
            "args": [],
            "env": {},
            "docker_image_name_suggestion": None
        }

    readme_section = f"""README Content:
```
{readme_text}
```""" if readme_text else "No README content provided." 

    dockerfile_section = f"""Dockerfile Content:
```
{dockerfile_text}
```""" if dockerfile_text else "No Dockerfile content provided."

    prompt = (
        f"""Analyze the following repository content (README and optionally Dockerfile) to extract information for configuring and running an MCP server, primarily as a Docker container.

{readme_section}

{dockerfile_section}

Instructions:

1.  **Description**: Provide a concise description of what the code in the repository does and main functionality based on the README. Ensure that you provide a good description of what the code does and what it could be used for by a user or an automated agent
2.  **Docker Image Name Suggestion**: Based on the repository URL (if inferable from README context like git clone commands) or general repository name, suggest a Docker image name. Format as `username/repository-name:latest` or `repository-name:latest`. If no clear basis, return null.
3.  **Primary Execution Command & Arguments (for Docker Container)**:
    *   **Priority 1: Dockerfile Analysis**: If Dockerfile content is provided, identify the `ENTRYPOINT` and/or `CMD`. This is the preferred source for the command and arguments used to start the application *inside the container*.
        *   If both `ENTRYPOINT` (shell or exec form) and `CMD` (exec or shell form) are present, understand how they combine. The `CMD` often provides default arguments to the `ENTRYPOINT`.
        *   Extract the effective command and any default arguments.
    *   **Priority 2: README Analysis (for Docker context)**: If the Dockerfile doesn't provide a clear start command (e.g., it's just `bash`) or no Dockerfile is provided, scan the README for `docker run` examples. Extract the image name and the command/args executed *inside* the container from these examples.
    *   **Priority 3: README Analysis (for Non-Containerized Fallback)**: If no Docker-specific command can be found, fall back to identifying the primary command and arguments for *non-containerized* execution, using the hierarchy provided below. This is a last resort if container context is missing.
        *   Hierarchy for non-containerized: `uvx`, `npx`, `python -m`, `python <script>`, `node <script>`, `uv run`, `npm run`/`yarn <script>`, direct executable.
    *   The extracted `command` should be the main executable or script. `args` should be an array of its arguments.
    *   **Distinguish from installation or build commands** (like `docker build`, `pip install`, `npm install`). We need the command to *run* the application.
4.  **Environment Variables**: (Same instructions as before - analyze README for env vars, classify as Mandatory/Optional, provide example values).

Return your answer ONLY as a valid JSON object with the following keys:
-   `"description"`: (string) The repository description.
-   `"docker_image_name_suggestion"`: (string or null) Suggested Docker image name.
-   `"command"`: (string or null) The primary command, prioritized for Docker execution.
-   `"args"`: (array of strings) Arguments for the command.
-   `"env"`: (object) Environment variables (structure: `{{ "VAR_NAME": {{ "value": "val", "status": "Mandatory|Optional" }} }}`).

Example for a Dockerized Python app (Dockerfile has `ENTRYPOINT ["python", "app/main.py"]` and `CMD ["--port", "8000"]`):
`{{ "description": "...", "docker_image_name_suggestion": "myuser/my-python-app:latest", "command": "python", "args": ["app/main.py", "--port", "8000"], "env": {{ ... }} }}`

Example from README `docker run myimage server --host 0.0.0.0` (if Dockerfile is uninformative):
`{{ "description": "...", "docker_image_name_suggestion": "myimage", "command": "server", "args": ["--host", "0.0.0.0"], "env": {{ ... }} }}`
"""
    )
    
    model = 'gpt-4.1-nano'
    prompt_tokens = count_tokens(prompt, model)
    
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            response_format={"type": "json_object"}
        )
        
        completion_tokens = resp.usage.completion_tokens if hasattr(resp, 'usage') and hasattr(resp.usage, 'completion_tokens') else 0
        # total_tokens = prompt_tokens + completion_tokens # This line was in the original, but seems unused. Will keep commented for now.
        # cost = get_model_cost(model, prompt_tokens, completion_tokens) # This line was in the original, but seems unused. Will keep commented for now.
        
        # print(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}") # Debugging line, can be commented out
        # print(f"Estimated cost: ${cost:.6f}") # Debugging line, can be commented out
        
        result = json.loads(resp.choices[0].message.content.strip())
        return result
    except Exception as e:
        print(f"Error in GPT processing: {str(e)}")
        # Fallback if there's an error
        return {
            "description": "Could not extract description from repository content (GPT processing error).",
            "docker_image_name_suggestion": None,
            "command": None,
            "args": [],
            "env": {},
            "docker_image_name_suggestion": None
        } 
