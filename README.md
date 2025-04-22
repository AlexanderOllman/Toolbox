# Toolbox - MCP Server Manager

A web application for managing MCP servers and generating configuration files.

## Features

- Repository management (add, view, delete)
- Automatic extraction of information from README files using GPT
- YAML and JSON configuration generation
- Modern UI with React and Tailwind CSS
- Command-line tools for repository management and config generation

## Project Structure

The project is divided into two main parts:

- **Backend**: FastAPI server for API endpoints
- **Frontend**: React application with Tailwind CSS

## Prerequisites

- Python 3.8+
- Node.js 18+
- Git
- OpenAI API key

## Getting Started

### Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the FastAPI server:

```bash
python run.py
```

The API will be available at http://localhost:8000.

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

The web application will be available at http://localhost:5173.

## API Documentation

Once the backend is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Command-Line Tools

The application includes two command-line tools:

### Add Server Tool

This tool allows you to add Git repositories to the database:

```bash
python backend/add_server.py https://github.com/username/repo.git
```

Optional arguments:
- `--name`: Custom name for the repository
- `--description`: Custom description for the repository
- `--command`: Custom command for running the repository
- `--args`: Custom arguments for the command

### Configuration Tool

This tool provides functionality to manage the configuration:

```bash
python backend/cli.py generate-yaml
```

Available commands:
- `generate-yaml`: Generate a YAML configuration file
  - `-o, --output`: Specify the output file path
  - `-p, --print`: Print the YAML to stdout
- `list`: List all repositories in the database

## Development Notes

- The OpenAI API key is hardcoded in `backend/app/services/openai_service.py`. In a production environment, this should be replaced with an environment variable.
- The database is a SQLite file stored at `backend/mcp_servers.db`. Make sure this file is backed up regularly.

## License

MIT 