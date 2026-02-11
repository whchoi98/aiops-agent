#!/bin/bash
set -e

echo "Starting Steampipe service (PostgreSQL mode)..."
steampipe service start --listen local --port 9193 --database-password steampipe_aiops

# Wait for Steampipe to be ready
for i in $(seq 1 10); do
    if steampipe service status 2>/dev/null | grep -q "running"; then
        echo "Steampipe service is ready."
        break
    fi
    echo "Waiting for Steampipe service... ($i/10)"
    sleep 2
done

echo "Starting MCP HTTP server on port 8080..."
exec python /app/ecs/mcp_server.py
