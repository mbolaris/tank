# Tank World - Production Dockerfile
# Optimized for Oracle Cloud Always Free ARM instances

# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 tankworld \
    && useradd --uid 1000 --gid tankworld --shell /bin/bash --create-home tankworld

# Copy requirements first for better caching
COPY backend/requirements.txt ./backend/
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r backend/requirements.txt \
    && pip install psutil

# Copy application code
COPY core/ ./core/
COPY backend/ ./backend/
COPY main.py ./

# Create data directories
RUN mkdir -p /app/data /app/logs \
    && chown -R tankworld:tankworld /app

# Switch to non-root user
USER tankworld

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
