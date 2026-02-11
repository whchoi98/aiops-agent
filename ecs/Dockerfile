FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user (steampipe plugins require user home)
RUN useradd -m -s /bin/bash appuser

# Install Steampipe
RUN /bin/sh -c "$(curl -fsSL https://steampipe.io/install/steampipe.sh)"

# Install Steampipe plugins as appuser
USER appuser
RUN steampipe plugin install aws kubernetes
USER root

# Python dependencies
COPY ecs/requirements.txt /app/ecs/requirements.txt
RUN pip install --no-cache-dir -r /app/ecs/requirements.txt

# Application code
COPY tools/ /app/tools/
COPY ecs/mcp_server.py /app/ecs/mcp_server.py
COPY ecs/entrypoint.sh /app/ecs/entrypoint.sh
RUN chmod +x /app/ecs/entrypoint.sh

WORKDIR /app
USER appuser

EXPOSE 8080

ENTRYPOINT ["/app/ecs/entrypoint.sh"]
