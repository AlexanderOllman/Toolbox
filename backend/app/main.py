from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply Docker configuration first
from app.docker_config import configure_docker_environment
configure_docker_environment()

app = FastAPI(
    title="Toolbox API",
    description="API for managing repositories and MCP servers",
    version="0.1.0",
    # Disable automatic redirects for trailing slashes
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS - move this middleware to be first in the chain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://192.168.194.33:5173",
        "http://0.0.0.0:5173",
        "http://localhost:8020",
        "http://127.0.0.1:8020", 
        "http://192.168.194.33:8020",
        "http://0.0.0.0:8020"
    ],  # Allow multiple origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Toolbox API"}

# Import and include routers
from app.api.repositories import router as repo_router
from app.api.config import router as config_router
from app.api.docker_api import router as docker_api_router
from app.api.mcp_testing import router as mcp_testing_router

# Add routes without trailing slash handling
app.include_router(repo_router, prefix="/api/repositories", tags=["repositories"])
app.include_router(config_router, prefix="/api/config", tags=["configuration"])
app.include_router(docker_api_router, prefix="/api/docker", tags=["docker"])
app.include_router(mcp_testing_router, prefix="/api/mcp", tags=["mcp-testing"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8020, reload=True) 