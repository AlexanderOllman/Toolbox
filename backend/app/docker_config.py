import os
import logging

logger = logging.getLogger(__name__)

def configure_docker_environment():
    """
    Configure environment variables for Docker environment.
    This allows the application to connect to services on the host machine.
    """
    if os.environ.get('IN_DOCKER'):
        qdrant_host = os.environ.get('QDRANT_HOST', 'host.docker.internal')
        qdrant_port = os.environ.get('QDRANT_PORT', '7333')
        
        # Set environment variables for application to use
        os.environ['QDRANT_HOST'] = qdrant_host
        os.environ['QDRANT_PORT'] = qdrant_port
        
        logger.info(f"Docker environment detected. Using Qdrant at {qdrant_host}:{qdrant_port}")
    else:
        logger.info("Not running in Docker, using default configuration") 