# Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install tmux and curl (for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Make app directory readable by all (for running as non-root user)
RUN chmod -R a+rX /app

# Default port (can be overridden by MATE_PORT env var)
ENV MATE_PORT=8765
EXPOSE 8765

# Run the application using the configured port
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${MATE_PORT}"
