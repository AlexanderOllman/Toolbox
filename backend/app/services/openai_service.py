import json
import tiktoken
from openai import OpenAI
import os
from app.services.config_service import get_config_value

# Initialize OpenAI client - use API key from config or fallback to environment variable
api_key = get_config_value("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=api_key)

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

def get_repo_info_from_gpt(readme_text):
    """Extract repository information from README text using GPT."""
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
    
    try:
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
        
        result = json.loads(resp.choices[0].message.content.strip())
        return result
    except Exception as e:
        print(f"Error in GPT processing: {str(e)}")
        # Fallback if there's an error
        return {
            "description": "Could not extract description from README",
            "command": None,
            "args": []
        } 