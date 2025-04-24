from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Toolbox API",
    description="API for managing repositories and MCP servers",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.194.33:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Toolbox API"}

# Import and include routers
from app.api.repositories import router as repo_router
from app.api.config import router as config_router

app.include_router(repo_router, prefix="/api/repositories", tags=["repositories"])
app.include_router(config_router, prefix="/api/config", tags=["configuration"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8020, reload=True) 