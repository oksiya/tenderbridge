#!/bin/bash

# Kill all running podman containers first instead of hard-killing the podman daemon
echo "Stopping all running podman containers..."
podman stop $(podman ps -aq) 2>/dev/null

# Remove all containers
echo "Removing all podman containers..."
podman rm -f $(podman ps -aq) 2>/dev/null

# Remove unused volumes
echo "Removing unused podman volumes..."
podman volume prune -f

# Remove unused networks
echo "Removing unused podman networks..."
podman network prune -f

# Build containers using podman-compose
echo "Building containers..."
podman-compose build

# Start containers
echo "Starting containers..."
podman-compose up
