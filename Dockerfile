# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install uv for faster package installation
RUN pip install uv

# Copy dependency files
COPY requirements.txt pyproject.toml ./

# Install dependencies
RUN uv pip install --system -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local /usr/local

# Copy application source code
COPY src/ ./src/

# Create data directory with proper permissions
RUN mkdir -p /data && chown appuser:appuser /data

# Create logs directory in working directory with proper permissions
# 应用程序会尝试创建 ./logs 目录，需要提前创建并设置权限
RUN mkdir -p ./logs && chown appuser:appuser ./logs

# Create log directory for additional logging (if needed)
RUN mkdir -p /var/log/notify && chown appuser:appuser /var/log/notify

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 18888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:18888/health')" || exit 1

# Command to run the application
CMD ["python", "-m", "src.main"]