#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${YELLOW}Building and starting Toolbox Docker containers...${NC}"

# Check if docker-compose.yml has been configured
echo -e "${YELLOW}Important: Make sure your docker-compose.yml has the correct Qdrant configuration.${NC}"
echo -e "${YELLOW}The file includes multiple options that you can uncomment based on your setup:${NC}"
echo -e "  1. host.docker.internal (default, works on most systems)"
echo -e "  2. Direct IP address (e.g., 192.168.194.33)"
echo -e "  3. Docker service name (if running Qdrant in another container)"
echo -e ""
read -p "Press Enter to continue or Ctrl+C to cancel and edit your configuration..."

# Build and start the Docker containers
docker compose up --build -d

# Check if containers started successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Toolbox containers are now running!${NC}"
    echo -e "${GREEN}Access the application at:${NC}"
    echo -e "  - Frontend: http://localhost:5173"
    echo -e "  - Backend API: http://localhost:8020"
    echo -e "\n${YELLOW}To view logs:${NC}"
    echo -e "  docker-compose logs -f"
    echo -e "\n${YELLOW}To stop the containers:${NC}"
    echo -e "  docker-compose down"
    echo -e "\n${YELLOW}Qdrant Connection:${NC}"
    echo -e "  The application is configured to connect to Qdrant using the settings in docker-compose.yml"
    echo -e "  If you experience connection issues, check the logs and adjust the QDRANT_HOST value."
else
    echo -e "${RED}Failed to start Toolbox containers. Check the logs above for errors.${NC}"
    exit 1
fi 