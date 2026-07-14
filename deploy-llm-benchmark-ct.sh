#!/bin/bash

echo "====================================================="
echo "🚀 Starting llm-benchmark-ct Deployment Script"
echo "====================================================="

# 1. Define persistent storage path
VOLUME_PATH="/opt/ct/llm-benchmark"

# 2. Create required directories
echo "Creating persistent volumes at $VOLUME_PATH..."
sudo mkdir -p "$VOLUME_PATH"
sudo chown -R $(whoami) $(dirname "$VOLUME_PATH") # Ensure current user has access if needed

# 3. Copy repository files into the persistent directory (simulating production setup)
echo "Copying repository contents to $VOLUME_PATH/..."
# Note: In a real scenario, we would copy the built image/files. Here we simulate copying the project structure.
cp -r * "$VOLUME_PATH"/

# 4. Run Docker Compose
echo "Starting Docker containers in detached mode..."
# Assuming docker-compose.yml is in the current working directory or accessible path
docker compose up -d

# 5. Check container status
echo "Waiting for container to start..."
sleep 5
echo "Checking container health..."
docker ps

echo "====================================================="
echo "✅ Deployment Complete!"
echo "Container status check completed. Review 'docker ps' output."
echo "====================================================="