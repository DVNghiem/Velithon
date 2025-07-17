"""Production deployment example with Prometheus monitoring.

This example shows how to deploy a Velithon application with Prometheus
monitoring in a production environment using Docker and docker-compose.
"""

# docker-compose.yml
DOCKER_COMPOSE_CONTENT = """
version: '3.8'

services:
  # Velithon application
  velithon-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - VELITHON_ENV=production
      - VELITHON_LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Prometheus monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
    depends_on:
      - velithon-app
    restart: unless-stopped

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    depends_on:
      - prometheus
    restart: unless-stopped

  # Alertmanager for alerts
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  default:
    name: velithon-monitoring
"""

# monitoring/prometheus.yml
PROMETHEUS_CONFIG = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Velithon application metrics
  - job_name: 'velithon-app'
    static_configs:
      - targets: ['velithon-app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
    scrape_timeout: 10s

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Optional: Node exporter for system metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
"""

# monitoring/alerts.yml
ALERTING_RULES = """
groups:
  - name: velithon_alerts
    rules:
      # High error rate alert
      - alert: VelithonHighErrorRate
        expr: |
          (
            rate(velithon_http_requests_total{status_code=~"5.."}[5m]) /
            rate(velithon_http_requests_total[5m])
          ) > 0.05
        for: 2m
        labels:
          severity: warning
          service: velithon-app
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"

      # High response time alert
      - alert: VelithonHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(velithon_http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
          service: velithon-app
        annotations:
          summary: "High response time detected"
          description: "95th percentile latency is {{ $value }}s for the last 5 minutes"

      # Service down alert
      - alert: VelithonServiceDown
        expr: up{job="velithon-app"} == 0
        for: 1m
        labels:
          severity: critical
          service: velithon-app
        annotations:
          summary: "Velithon service is down"
          description: "Velithon application has been down for more than 1 minute"

      # High memory usage alert (if node-exporter is available)
      - alert: VelithonHighMemoryUsage
        expr: |
          (
            node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes
          ) / node_memory_MemTotal_bytes > 0.85
        for: 5m
        labels:
          severity: warning
          service: velithon-app
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value | humanizePercentage }}"

  - name: infrastructure_alerts
    rules:
      # Prometheus storage space alert
      - alert: PrometheusStorageFull
        expr: |
          prometheus_tsdb_wal_size_bytes / prometheus_tsdb_wal_max_size_bytes > 0.8
        for: 5m
        labels:
          severity: warning
          service: prometheus
        annotations:
          summary: "Prometheus storage almost full"
          description: "Prometheus WAL is {{ $value | humanizePercentage }} full"
"""

# monitoring/alertmanager.yml
ALERTMANAGER_CONFIG = """
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@example.com'

route:
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/'
    
  # Example email configuration
  - name: 'email-alerts'
    email_configs:
      - to: 'admin@example.com'
        subject: 'Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}

  # Example Slack configuration
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: 'Velithon Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
"""

# Dockerfile
DOCKERFILE_CONTENT = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash velithon
USER velithon

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""

# main.py - Production application
MAIN_APP_CONTENT = """
import logging
import os
from velithon import Velithon
from velithon.middleware import (
    Middleware, 
    FastPrometheusMiddleware,
    LoggingMiddleware,
    CORSMiddleware,
    CompressionMiddleware
)
from velithon.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('VELITHON_LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create application with monitoring
app = Velithon(
    middleware=[
        # CORS for web frontends
        Middleware(CORSMiddleware, allow_origins=["*"]),
        
        # Prometheus metrics collection
        Middleware(
            FastPrometheusMiddleware,
            metrics_path="/metrics",
            exclude_paths=["/health", "/ready", "/ping"],
        ),
        
        # Request logging
        Middleware(LoggingMiddleware),
        
        # Response compression
        Middleware(CompressionMiddleware),
    ]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "service": "velithon-app"})

# Ready check endpoint  
@app.get("/ready")
async def ready_check():
    return JSONResponse({"status": "ready", "service": "velithon-app"})

# Sample API endpoints
@app.get("/")
async def root():
    return JSONResponse({"message": "Velithon API with Prometheus monitoring"})

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Simulate some processing time
    import asyncio
    await asyncio.sleep(0.01)
    
    return JSONResponse({
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    })

@app.post("/users")
async def create_user(data: dict):
    # Simulate processing
    import asyncio
    await asyncio.sleep(0.05)
    
    return JSONResponse(
        {"message": "User created successfully", "data": data},
        status_code=201
    )

@app.get("/error")
async def trigger_error():
    # Endpoint for testing error metrics
    raise Exception("Test error for monitoring")

if __name__ == "__main__":
    print("Starting Velithon application with Prometheus monitoring...")
    print("Endpoints:")
    print("  - Health: http://localhost:8000/health")
    print("  - Metrics: http://localhost:8000/metrics") 
    print("  - API: http://localhost:8000/")
"""

# requirements.txt
REQUIREMENTS_CONTENT = """
velithon>=0.4.3
"""

if __name__ == '__main__':
    print('Production Deployment Example with Prometheus Monitoring')
    print('=' * 60)
    print()
    print('This example includes:')
    print('- Velithon app with Prometheus metrics')
    print('- Prometheus server for metrics collection')
    print('- Grafana for visualization')
    print('- Alertmanager for alerting')
    print()
    print('To deploy:')
    print('1. Create the files shown above')
    print('2. Run: docker-compose up -d')
    print('3. Access:')
    print('   - App: http://localhost:8000')
    print('   - Metrics: http://localhost:8000/metrics')
    print('   - Prometheus: http://localhost:9090')
    print('   - Grafana: http://localhost:3000 (admin/admin123)')
    print('   - Alertmanager: http://localhost:9093')
