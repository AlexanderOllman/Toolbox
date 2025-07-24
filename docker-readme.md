# Docker Setup for Toolbox

This document describes how to run the Toolbox application using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)
- Qdrant vector database (running either on your host machine or in another container)

## Getting Started

1. Clone the repository (if you haven't already):
   ```bash
   git clone <repository-url>
   cd Toolbox
   ```

2. Configure Qdrant connection in `docker-compose.yml`:
   
   The application needs to connect to a Qdrant server for vector database functionality. There are three main options:
   
   a. **Connect to Qdrant on host machine** (default):
      ```yaml
      - QDRANT_HOST=host.docker.internal
      # - QDRANT_PORT=6333
      ```
   
   b. **Connect to Qdrant using direct IP address**:
      ```yaml
      - QDRANT_HOST=192.168.194.33  # Replace with your host's IP
      # - QDRANT_PORT=6333
      ```
   
   c. **Connect to Qdrant running in another Docker container**:
      ```yaml
      - QDRANT_HOST=qdrant  # Name of the Qdrant service in docker-compose
      # - QDRANT_PORT=6333
      ```
      Uncomment the `qdrant` service section in the docker-compose.yml if you want to run Qdrant in Docker.

3. Build and start the Docker containers:
   ```bash
   ./docker-run.sh
   ```
   Or manually:
   ```bash
   docker-compose up -d
   ```

   This will build the Docker image and start the services in detached mode.

4. View the application logs:
   ```bash
   docker-compose logs -f
   ```

5. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8020

6. To stop the containers:
   ```bash
   docker-compose down
   ```

## Development Workflow

The Docker setup is configured for development with volume mounts:

- Backend code changes are reflected immediately due to the reload option
- Frontend code changes in the `src` directory are detected by Vite's hot module replacement

## Troubleshooting Qdrant Connection

If you encounter issues connecting to Qdrant:

1. **Check Docker logs**:
   ```bash
   docker-compose logs -f
   ```
   Look for messages about Qdrant connection failures or successes.

2. **Verify Qdrant is running** outside Docker by testing:
   ```bash
   curl http://localhost:6333/collections
   ```

3. **Try different connection methods** as specified in the Configuration section above:
   - host.docker.internal
   - Direct IP address
   - Docker service name

4. **Network configuration**: Ensure your Docker network configuration allows communication with the host or other containers.

## Production Deployment

For production deployment, you may want to modify the Dockerfile to:

1. Build the frontend for production:
   ```
   RUN cd frontend && npm run build
   ```

2. Serve the static files using a web server like Nginx

3. Configure the backend to run without the reload option

## Additional Troubleshooting

- If you encounter port conflicts, modify the port mappings in the `docker-compose.yml` file
- For persistence of database files, add additional volume mounts in the `docker-compose.yml` 