#!/bin/bash
# Fully safe "nuclear reset" for Podman + podman-compose
# Siyabonga's tenderbridge reset script

set -e

PROJECT_DIR=~/dev/tenderbridge

echo "🛑 Stopping all containers..."
podman ps -aq | xargs -r podman stop

echo "🗑️ Removing all containers..."
for c in $(podman ps -aq); do
    podman rm -f "$c" || true
done

echo "🧹 Removing all pods..."
for p in $(podman pod ps --format "{{.ID}}"); do
    podman pod rm -f "$p" || true
done

echo "🧽 Pruning system resources..."
podman system prune -f

cd "$PROJECT_DIR"

echo "🔨 Rebuilding API image..."
podman-compose build

echo "🚀 Starting all containers (DB + API)..."
podman-compose up -d

# Detect the API container name
API_CONTAINER=$(podman ps --format "{{.Names}}" | grep api || true)

if [ -n "$API_CONTAINER" ]; then
    echo "🪵 Opening logs for container: $API_CONTAINER"
    # Try to open logs in a new terminal window
    if command -v gnome-terminal &>/dev/null; then
        gnome-terminal -- bash -c "podman logs -f $API_CONTAINER"
    elif command -v x-terminal-emulator &>/dev/null; then
        x-terminal-emulator -e bash -c "podman logs -f $API_CONTAINER"
    else
        echo "⚠️ Could not open a new terminal window. Showing logs here instead..."
        podman logs -f "$API_CONTAINER"
    fi
else
    echo "⚠️ API container not found. Logs unavailable."
fi

echo "✅ Safe nuclear reset complete!"
