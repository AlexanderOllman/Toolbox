from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services import docker_service # Assuming docker_service is in app.services

router = APIRouter()

class PortCheckRequest(BaseModel):
    port: int

@router.post("/check-port", summary="Check if a host port is available")
async def check_host_port(request: PortCheckRequest):
    """
    Checks if a given port is available on the Docker host machine.
    """
    try:
        is_available = await docker_service.check_host_port_availability(request.port)
        if is_available:
            return {"port": request.port, "status": "available", "message": f"Port {request.port} is available."}
        else:
            return {"port": request.port, "status": "unavailable", "message": f"Port {request.port} is currently in use or not bindable."}
    except Exception as e:
        # Log the exception e
        print(f"Error checking port {request.port}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check port availability: {str(e)}") 