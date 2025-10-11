#!/bin/bash
# safer_nuclear_reset.sh

echo "🛑 Stopping all containers..."
podman ps -aq | xargs -r podman stop

echo "🗑️ Removing all containers..."
podman ps -aq | xargs -r podman rm -f

echo "🧹 Removing all pods..."
podman pod ps -aq | xargs -r podman pod rm -f

echo "🧹 Pruning system resources..."
podman system prune -f

echo "🔨 Rebuilding API image..."
podman-compose build

echo "🚀 Starting all containers..."
podman-compose up -d

echo "✅ Safe nuclear reset complete."
