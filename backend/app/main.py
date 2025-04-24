from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_origins=["http://localhost:5173"],  # Be more specific with origins
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

# Add routes without trailing slash handling
app.include_router(repo_router, prefix="/api/repositories", tags=["repositories"])
app.include_router(config_router, prefix="/api/config", tags=["configuration"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8020, reload=True) 