FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# Install Node.js and git for running the frontend and cloning repos
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    # Add Docker GPG key and repository, then install docker-ce-cli
    && apt-get install -y ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy frontend source for development mode option
COPY frontend /app/frontend

# Copy backend code
COPY backend /app/backend

# Copy start script
COPY start_service.py /app/

# Install backend dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install frontend dependencies
RUN cd frontend && npm install

EXPOSE 5173 8020

# Set environment variable to indicate we're in Docker
ENV IN_DOCKER=true

# Command to run the application
CMD ["python", "start_service.py"] 