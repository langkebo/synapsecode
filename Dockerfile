# Multi-stage build for optimized Docker image
FROM python:3.9-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libcurl4-openssl-dev \
    libgeos-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.6.1

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies (only production)
RUN poetry install --only=main --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SYNAPSE_CONFIG_PATH=/data/homeserver.yaml

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libffi7 \
    libssl3 \
    libjpeg62-turbo \
    libxml2 \
    libxslt1.1 \
    zlib1g \
    libcurl4 \
    libgeos-c1v5 \
    curl \
    jq \
    postgresql-client \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r synapse && useradd -r -g synapse synapse

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=synapse:synapse . .

# Create necessary directories
RUN mkdir -p /data /media /logs /etc/synapse && \
    chown -R synapse:synapse /data /media /logs /etc/synapse

# Switch to non-root user
USER synapse

# Create health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8008/_matrix/client/versions || exit 1

# Expose port
EXPOSE 8008

# Set entrypoint
ENTRYPOINT ["dumb-init", "--"]

# Set default command
CMD ["python", "-m", "synapse.app.homeserver"]