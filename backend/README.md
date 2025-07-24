# Backend API Documentation

This document describes the available APIs for the Toolbox MCP Server Manager backend.

## Overview

The backend is a FastAPI application that provides a REST API for managing MCP (Model Context Protocol) servers. It includes functionality for:
- Repository management (Git repos with MCP servers)
- Configuration management
- Docker container deployment
- Vector database integration for semantic search

## Getting Started

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python run.py
```

The server will start on `http://localhost:8020` by default.

### Configuration

The backend uses environment variables and configuration files. Key settings include:
- `QDRANT_HOST`: Qdrant vector database host (default: localhost)
- `QDRANT_PORT`: Qdrant vector database port (default: 6333)
- `CONTAINER_HOST`: Docker host for remote Docker deployments

## API Documentation

### Base URL
```
http://localhost:8020
```

### Interactive API Documentation
- Swagger UI: `http://localhost:8020/api/docs`
- ReDoc: `http://localhost:8020/api/redoc`

## API Endpoints

### 1. Repository API (`/api/repositories`)

#### List All Repositories
```http
GET /api/repositories/
```

**Response:**
```json
[
  {
    "name": "example-mcp-server",
    "description": "An example MCP server",
    "command": "python -m example_server",
    "args": [],
    "transport": "stdio",
    "url": "",
    "env": {},
    "repo_url": "https://github.com/example/mcp-server.git",
    "has_dockerfile": true,
    "deploy_as_container": false,
    "deployment_status": "not_deployed"
  }
]
```

#### Get Repository by Name
```http
GET /api/repositories/{name}
```

**Parameters:**
- `name` (path): Repository name

**Response:** Repository object

#### Create Repository
```http
POST /api/repositories/
```

**Request Body:**
```json
{
  "name": "my-mcp-server",
  "repo_url": "https://github.com/example/mcp-server.git",
  "description": "My MCP server",
  "command": "python -m my_server",
  "args": ["--port", "8080"],
  "env": {
    "API_KEY": {
      "value": "your-api-key",
      "status": "Required"
    }
  },
  "transport": "stdio",
  "deploy_as_container": false,
  "is_external_config": false
}
```

**Response:** Created repository object

#### Update Repository
```http
PUT /api/repositories/{repo_name}
```

**Parameters:**
- `repo_name` (path): Repository name

**Request Body:** Partial repository object with fields to update

**Response:** Updated repository object

#### Delete Repository
```http
DELETE /api/repositories/{name}
```

**Parameters:**
- `name` (path): Repository name

**Response:** 204 No Content

#### Search Repositories
```http
POST /api/repositories/search
```

**Request Body:**
```json
{
  "query": "search term",
  "limit": 5
}
```

**Response:** Array of matching repositories

#### Fetch Repository Details
```http
POST /api/repositories/details
```

**Request Body:**
```json
{
  "repo_url": "https://github.com/example/mcp-server.git"
}
```

**Response:**
```json
{
  "name": "mcp-server",
  "repo_url": "https://github.com/example/mcp-server.git",
  "description": "Auto-generated description",
  "command": "python -m server",
  "args": [],
  "env": {},
  "has_dockerfile": true,
  "has_docker_compose": false,
  "docker_image_name_suggestion": "mcp-server:latest",
  "exposed_port_suggestion": 8080,
  "dockerfile_content": "FROM python:3.9\n...",
  "error": null
}
```

#### List Container Repositories
```http
GET /api/repositories/containers/
```

**Response:** Array of repositories configured for container deployment

#### Get Dockerfile Content
```http
GET /api/repositories/{name}/dockerfile
```

**Parameters:**
- `name` (path): Repository name

**Response:** Plain text Dockerfile content

#### Deploy Container
```http
POST /api/repositories/{repo_name}/deploy
```

**Parameters:**
- `repo_name` (path): Repository name

**Request Body:**
```json
{
  "image_name": "my-mcp-server:latest",
  "container_args": {
    "restart": "unless-stopped"
  },
  "env_vars": {
    "API_KEY": {
      "value": "your-api-key",
      "status": "Required"
    }
  },
  "attempt_local_build": true,
  "attempt_push_to_registry": false,
  "use_docker_compose": false,
  "host_port_mapping": 8080,
  "actual_container_port": 8080,
  "container_command": "python -m server",
  "container_command_args": ["--port", "8080"]
}
```

**Response:** 202 Accepted (deployment started in background)

#### Finalize Deployment
```http
POST /api/repositories/repositories/finalize-deployment
```

**Request Body:**
```json
{
  "original_repo_name": "my-mcp-server",
  "host_port": 8080,
  "mcp_path": "/mcp",
  "final_env_vars": {
    "API_KEY": "your-api-key"
  }
}
```

**Response:** Created external repository object

#### Synchronize Local Repository
```http
POST /api/repositories/sync-local/{repo_name}
```

**Parameters:**
- `repo_name` (path): Repository name

**Response:** Synchronized repository information

#### Repository Roots Management

##### Add Root to Repository
```http
POST /api/repositories/{name}/roots
```

**Parameters:**
- `name` (path): Repository name

**Request Body:**
```json
{
  "uri": "file:///path/to/directory",
  "name": "project_root",
  "server_uri_alias": "project"
}
```

**Response:** Created root object

##### Get Repository Roots
```http
GET /api/repositories/{name}/roots
```

**Parameters:**
- `name` (path): Repository name

**Response:** Array of root objects

### 2. Configuration API (`/api/config`)

#### Get YAML Configuration
```http
GET /api/config/yaml
```

**Response:** Plain text YAML configuration

#### Get JSON Configuration
```http
GET /api/config/json
```

**Response:**
```json
{
  "mcp": {
    "servers": {
      "server-name": {
        "command": "python -m server",
        "args": [],
        "env": {}
      }
    }
  }
}
```

#### Generate Configuration File
```http
POST /api/config/generate
```

**Query Parameters:**
- `output_path` (optional): Output file path

**Response:**
```json
{
  "message": "Configuration file generation to 'mcp_servers.yaml' started",
  "file_path": "/path/to/mcp_servers.yaml"
}
```

#### Download Configuration File
```http
GET /api/config/download
```

**Response:** File download (application/x-yaml)

#### Get Settings
```http
GET /api/config/settings
```

**Response:**
```json
{
  "QDRANT_HOST": "localhost",
  "QDRANT_PORT": "6333",
  "COLLECTION_NAME": "mcp_servers",
  "QDRANT_STATUS": "connected"
}
```

#### Update Settings
```http
POST /api/config/settings
```

**Request Body:**
```json
{
  "items": [
    {
      "key": "QDRANT_HOST",
      "value": "localhost"
    },
    {
      "key": "QDRANT_PORT",
      "value": "6333"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Settings updated successfully",
  "updated_settings": ["QDRANT_HOST", "QDRANT_PORT"],
  "connection_status": {
    "status": "connected",
    "message": "Successfully connected to Qdrant"
  }
}
```

#### Test Qdrant Connection
```http
GET /api/config/test-qdrant
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully connected to Qdrant",
  "settings": {
    "host": "localhost",
    "port": "6333",
    "collection": "mcp_servers"
  }
}
```

#### Get Qdrant Status
```http
GET /api/config/qdrant-status
```

**Response:**
```json
{
  "status": "connected",
  "message": "Successfully connected to Qdrant"
}
```

#### Get Collection Status
```http
GET /api/config/collection-status
```

**Response:**
```json
{
  "status": "connected",
  "message": "Collection 'mcp_servers' exists and is accessible",
  "collection_name": "mcp_servers",
  "vector_count": 42
}
```

#### Initialize Collections
```http
POST /api/config/initialize-collections
```

**Response:**
```json
{
  "status": "success",
  "message": "Collections initialized successfully! Collection 'mcp_servers' is ready.",
  "collection_name": "mcp_servers"
}
```

#### Get Docker Status
```http
GET /api/config/docker-status
```

**Response:**
```json
{
  "status": "available",
  "method": "socket",
  "message": "Docker socket available at /var/run/docker.sock"
}
```

### 3. Docker API (`/api/docker`)

#### Check Port Availability
```http
POST /api/docker/check-port
```

**Request Body:**
```json
{
  "port": 8080
}
```

**Response:**
```json
{
  "port": 8080,
  "status": "available",
  "message": "Port 8080 is available."
}
```

## Data Models

### Repository
```json
{
  "name": "string",
  "description": "string",
  "command": "string",
  "args": ["string"],
  "transport": "stdio|http|sse|streamable_http",
  "url": "string",
  "read_timeout_seconds": 30,
  "read_transport_sse_timeout_seconds": 300,
  "headers": "{}",
  "api_key": "string",
  "env": {
    "VAR_NAME": {
      "value": "string",
      "status": "Required|Optional"
    }
  },
  "roots_table": "string",
  "repo_url": "string",
  "docker_image_name_suggestion": "string",
  "has_dockerfile": false,
  "deploy_as_container": false,
  "is_external_config": false,
  "container_args_template": {},
  "container_args_user": {},
  "deployment_status": "not_deployed|deployed|failed",
  "image_name_override": "string",
  "host_port_mapping": 8080,
  "actual_container_port": 8080,
  "last_build_attempt_local": false,
  "last_push_attempt_registry": false,
  "last_deployment_used_compose": false
}
```

### Environment Variable Detail
```json
{
  "value": "string",
  "status": "Required|Optional"
}
```

### Server Root
```json
{
  "server_name": "string",
  "uri": "string",
  "name": "string",
  "server_uri_alias": "string"
}
```

## CLI Usage

The backend also provides a CLI interface:

```bash
# List all repositories
python cli.py list

# Generate YAML configuration
python cli.py generate-yaml -o /path/to/config.yaml

# Print YAML to stdout
python cli.py generate-yaml --print
```

## Adding Repositories via Script

You can add repositories programmatically using the `add_server.py` script:

```bash
python add_server.py https://github.com/example/mcp-server.git
```

## Error Handling

The API uses standard HTTP status codes:
- `200`: Success
- `201`: Created
- `202`: Accepted (async operation started)
- `204`: No Content
- `400`: Bad Request
- `404`: Not Found
- `422`: Unprocessable Entity
- `500`: Internal Server Error

Error responses include details:
```json
{
  "detail": "Error description"
}
```

## CORS Configuration

The API supports CORS for frontend integration with origins:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://192.168.194.33:5173`
- `http://0.0.0.0:5173`

## Dependencies

Key dependencies include:
- FastAPI: Web framework
- Uvicorn: ASGI server
- Pydantic: Data validation
- SQLAlchemy: Database ORM
- Qdrant: Vector database client
- OpenAI: AI integration
- Docker: Container management

## Environment Variables

- `QDRANT_HOST`: Qdrant server host
- `QDRANT_PORT`: Qdrant server port
- `COLLECTION_NAME`: Vector database collection name
- `CONTAINER_HOST`: Docker host for remote deployments
- `OPENAI_API_KEY`: OpenAI API key for repository analysis

## Development

To run in development mode:
```bash
python run.py --host 0.0.0.0 --port 8020
```

For production deployment, use a proper ASGI server like Gunicorn with Uvicorn workers. 