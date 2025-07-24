import asyncio
import logging
import os
import uuid
from typing import Dict, List, Optional, Tuple, Any
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MCPContainerConfig:
    """Simple configuration for running an MCP server in a container."""
    repo_path: str                    # Local path to the cloned repository
    image_name: Optional[str] = None  # Docker image name, auto-generated if None
    command: Optional[str] = None     # Command to run inside container
    args: Optional[List[str]] = None  # Arguments for the command
    env_vars: Optional[Dict[str, str]] = None  # Environment variables
    timeout_seconds: int = 60         # Container startup timeout
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env_vars is None:
            self.env_vars = {}

@dataclass
class MCPContainer:
    """Represents a running MCP server container."""
    container_id: str
    image_name: str
    process: Optional[subprocess.Popen] = None
    cleanup_callbacks: List[callable] = None
    
    def __post_init__(self):
        if self.cleanup_callbacks is None:
            self.cleanup_callbacks = []

class MCPContainerService:
    """
    Clean, simple service for running MCP servers in isolated Docker containers.
    Focused specifically on testing use cases.
    """
    
    def __init__(self):
        self.running_containers: Dict[str, MCPContainer] = {}
        self._check_docker()
    
    def _check_docker(self):
        """Verify Docker is available and running."""
        try:
            result = subprocess.run(['docker', 'version'], 
                                 capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f"Docker not available: {result.stderr}")
            logger.info("Docker connectivity verified")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"Docker not available: {e}")
    
    async def run_mcp_server(self, config: MCPContainerConfig) -> MCPContainer:
        """
        Run an MCP server in an isolated container.
        Returns MCPContainer instance for communication and cleanup.
        """
        logger.info(f"Starting MCP server from {config.repo_path}")
        
        # Generate unique container name
        container_name = f"mcp-test-{uuid.uuid4().hex[:8]}"
        
        try:
            # Build or ensure image exists
            image_name = await self._ensure_image(config, container_name)
            
            # Run container with MCP-specific setup
            container_id = await self._run_container(config, image_name, container_name)
            
            # Create container instance
            container = MCPContainer(
                container_id=container_id,
                image_name=image_name
            )
            
            # Wait for container to be ready
            await self._wait_for_ready(container_id, config.timeout_seconds)
            
            self.running_containers[container_id] = container
            logger.info(f"MCP server ready: {container_name} ({container_id[:12]})")
            
            return container
            
        except Exception as e:
            # Cleanup on failure
            await self._cleanup_container(container_name)
            raise RuntimeError(f"Failed to start MCP server: {e}") from e
    
    async def _ensure_image(self, config: MCPContainerConfig, container_name: str) -> str:
        """Build or pull the Docker image for the MCP server."""
        
        # Use provided image name or generate one
        if config.image_name:
            image_name = config.image_name
            logger.info(f"Using provided image: {image_name}")
        else:
            image_name = f"mcp-test-{container_name}"
            logger.info(f"Building image: {image_name}")
        
        # Check if Dockerfile exists
        dockerfile_path = Path(config.repo_path) / "Dockerfile"
        if dockerfile_path.exists():
            # Build from Dockerfile
            await self._build_image(config.repo_path, image_name)
        else:
            # Try to pull image or create a generic one
            if config.image_name:
                await self._pull_image(image_name)
            else:
                # Create a generic image for the repo
                await self._create_generic_image(config, image_name)
        
        return image_name
    
    async def _build_image(self, repo_path: str, image_name: str):
        """Build Docker image from Dockerfile."""
        logger.info(f"Building image {image_name} from {repo_path}")
        
        cmd = [
            'docker', 'build',
            '-t', image_name,
            '-f', 'Dockerfile',
            '.'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Docker build failed:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"Successfully built image: {image_name}")
    
    async def _pull_image(self, image_name: str):
        """Pull Docker image from registry."""
        logger.info(f"Pulling image: {image_name}")
        
        process = await asyncio.create_subprocess_exec(
            'docker', 'pull', image_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Docker pull failed:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"Successfully pulled image: {image_name}")
    
    async def _create_generic_image(self, config: MCPContainerConfig, image_name: str):
        """Create a generic Docker image for repos without Dockerfile."""
        logger.info(f"Creating generic image for: {image_name}")
        
        # Detect the runtime based on files in the repo
        repo_path = Path(config.repo_path)
        
        # Create temporary Dockerfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            dockerfile_content = self._generate_dockerfile(repo_path, config)
            f.write(dockerfile_content)
            temp_dockerfile = f.name
        
        try:
            cmd = [
                'docker', 'build',
                '-t', image_name,
                '-f', temp_dockerfile,
                str(repo_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = f"Generic image build failed:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Successfully created generic image: {image_name}")
            
        finally:
            os.unlink(temp_dockerfile)
    
    def _generate_dockerfile(self, repo_path: Path, config: MCPContainerConfig) -> str:
        """Generate a Dockerfile based on the repository contents."""
        
        # Detect the runtime
        if (repo_path / "package.json").exists():
            # Node.js project
            base_image = "node:18-slim"
            install_cmd = "npm install"
            default_cmd = config.command or "node index.js"
        elif (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
            # Python project
            base_image = "python:3.11-slim"
            install_cmd = "pip install -r requirements.txt" if (repo_path / "requirements.txt").exists() else "pip install -e ."
            default_cmd = config.command or "python -m server"
        else:
            # Generic Linux
            base_image = "ubuntu:22.04"
            install_cmd = "apt-get update && apt-get install -y python3 python3-pip nodejs npm"
            default_cmd = config.command or "python3 server.py"
        
        dockerfile = f"""
FROM {base_image}

WORKDIR /app
COPY . .

RUN {install_cmd}

CMD {default_cmd}
"""
        return dockerfile.strip()
    
    async def _run_container(self, config: MCPContainerConfig, image_name: str, container_name: str) -> str:
        """Run the Docker container with MCP-specific configuration."""
        
        cmd = [
            'docker', 'run',
            '--name', container_name,
            '--rm',                    # Auto-remove when stopped
            '-i',                      # Interactive (for stdio)
            '--detach',               # Run in background
        ]
        
        # Add environment variables
        for key, value in config.env_vars.items():
            cmd.extend(['-e', f'{key}={value}'])
        
        # Add the image and command
        cmd.append(image_name)
        if config.command:
            cmd.append(config.command)
            cmd.extend(config.args)
        
        logger.info(f"Running container: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Container start failed:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        container_id = stdout.decode().strip()
        logger.info(f"Container started: {container_name} ({container_id[:12]})")
        
        return container_id
    
    async def _wait_for_ready(self, container_id: str, timeout_seconds: int):
        """Wait for the container to be ready to accept connections."""
        logger.info(f"Waiting for container {container_id[:12]} to be ready...")
        
        for attempt in range(timeout_seconds):
            try:
                # Check if container is still running
                process = await asyncio.create_subprocess_exec(
                    'docker', 'inspect', '--format={{.State.Running}}', container_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    raise RuntimeError(f"Container inspection failed: {stderr.decode()}")
                
                if stdout.decode().strip() != "true":
                    # Get container logs for debugging
                    logs = await self._get_container_logs(container_id)
                    raise RuntimeError(f"Container stopped unexpectedly:\n{logs}")
                
                # Container is running - it's ready for MCP communication
                logger.info(f"Container {container_id[:12]} is ready")
                return
                
            except Exception as e:
                if attempt == timeout_seconds - 1:
                    logs = await self._get_container_logs(container_id)
                    raise RuntimeError(f"Container not ready after {timeout_seconds}s: {e}\nLogs:\n{logs}")
                
                await asyncio.sleep(1)
    
    async def _get_container_logs(self, container_id: str) -> str:
        """Get container logs for debugging."""
        try:
            process = await asyncio.create_subprocess_exec(
                'docker', 'logs', container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return f"STDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}"
        except Exception as e:
            return f"Failed to get logs: {e}"
    
    async def execute_in_container(self, container: MCPContainer, command: List[str]) -> Tuple[str, str]:
        """Execute a command inside the running container."""
        cmd = ['docker', 'exec', '-i', container.container_id] + command
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        return stdout.decode(), stderr.decode()
    
    async def cleanup_container(self, container: MCPContainer):
        """Clean up a running container."""
        container_id = container.container_id
        
        if container_id in self.running_containers:
            del self.running_containers[container_id]
        
        await self._cleanup_container(container_id)
    
    async def _cleanup_container(self, container_id_or_name: str):
        """Clean up container by ID or name."""
        try:
            logger.info(f"Cleaning up container: {container_id_or_name}")
            
            # Stop and remove container
            process = await asyncio.create_subprocess_exec(
                'docker', 'rm', '-f', container_id_or_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            logger.info(f"Container cleaned up: {container_id_or_name}")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup container {container_id_or_name}: {e}")
    
    async def cleanup_all(self):
        """Clean up all running containers."""
        logger.info("Cleaning up all MCP test containers...")
        
        containers = list(self.running_containers.values())
        for container in containers:
            await self.cleanup_container(container)
        
        logger.info("All containers cleaned up")

# Global instance
mcp_container_service = MCPContainerService() 