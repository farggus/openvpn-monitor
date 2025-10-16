FROM python:3.12-slim

# Install system utilities needed for server status collection
# - iputils-ping: for ping command (network connectivity checks)
# - iproute2: for ip command (network interface inspection)
# - curl: for HTTP requests (fallback if requests library fails)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    iproute2 \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app ./app
COPY logger.py .
COPY supervisord.conf /etc/supervisord.conf

# Copy translations
COPY translations ./translations

# Compile translations
RUN python translations/compile_translations.py

# Install supervisor
RUN pip install supervisor

# Create data directory and set ownership
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Environment variables
ENV FLASK_APP=app
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Switch to non-root user
USER appuser

# Use supervisord to run both Flask and logger
CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisord.conf"]
