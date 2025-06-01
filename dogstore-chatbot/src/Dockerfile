# Use a multi-stage build to get datadog-init binary
FROM datadog/serverless-init:1 AS datadog-init

# Python runtime
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy app files
COPY . .

# Copy datadog-init from the previous stage
COPY --from=datadog-init /datadog-init /app/datadog-init

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install system packages for lab features
RUN apt-get update && apt-get install -y \
    curl \
    bc \
    build-essential \
    kmod \
    supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose Streamlit (8501) and Flask (8080)
EXPOSE 8501 8080

# Healthcheck for Streamlit
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment variables for Datadog
ENV DD_SERVICE=chatbot-app
ENV DD_ENV=production
ENV DD_VERSION=1.0.0
ENV DD_APPSEC_ENABLED=true
ENV DD_TRACE_ENABLED=true
ENV DD_LOGS_INJECTION=true
ENV DD_AGENT_HOST=datadog-agent

# Use datadog-init to wrap supervisor
CMD ["/app/datadog-init", "supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]