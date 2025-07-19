# Production Deployment

Learn how to deploy Velithon applications to production environments with optimal performance, security, and reliability.

## Overview

This guide covers production deployment strategies, configuration, and best practices for running Velithon applications in production environments.

## Production Application Setup

```python
import os
from velithon import Velithon

# Production configuration
app = Velithon(
    debug=False,  # Disable debug mode
    title="My Production API",
    description="Production API built with Velithon",
    version="1.0.0",
    docs_url=None if os.getenv("DISABLE_DOCS") else "/docs",  # Optionally disable docs
    redoc_url=None if os.getenv("DISABLE_DOCS") else "/redoc"
)

# Production middleware
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": "production"}
```

## Server Configuration

### Using Granian (Recommended)

```bash
# Run with Granian (Built-in RSGI server)
velithon run --app main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --runtime-mode mt \
    --loop auto \
    --http auto \
    --log-level INFO

# Alternative: Direct Granian usage
granian --interface rsgi main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --threading-mode workers \
    --loop uvloop \
    --http auto
```

### Granian Configuration File

```python
# granian_config.py
import multiprocessing
import os

# Application
app = "main:app"
interface = "rsgi"

# Server socket  
host = "0.0.0.0"
port = int(os.getenv('PORT', '8000'))

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
runtime_mode = "mt"  # Multi-threaded mode
threading_mode = "workers"

# Performance
loop = "uvloop"  # Use uvloop for better performance
http = "auto"    # HTTP/1.1 and HTTP/2 support

# Logging
log_level = os.getenv('LOG_LEVEL', 'INFO')

# Process naming
process_name = 'velithon-api'
```
tmp_upload_dir = None

# SSL (if using HTTPS directly)
# keyfile = "/path/to/private.key"
# certfile = "/path/to/certificate.crt"
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["gunicorn", "--config", "gunicorn.conf.py", "main:app"]
```

### Multi-stage Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/home/appuser/.local/bin:$PATH

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Set work directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["gunicorn", "--config", "gunicorn.conf.py", "main:app"]
```

### Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DEBUG=false
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    server {
        listen 80;
        server_name example.com www.example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name example.com www.example.com;

        ssl_certificate /etc/nginx/ssl/certificate.crt;
        ssl_certificate_key /etc/nginx/ssl/private.key;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

        location / {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            access_log off;
            proxy_pass http://api;
        }
    }
}
```

## Environment Configuration

```bash
# .env.production
ENV=production
DEBUG=false
SECRET_KEY=your-super-secret-production-key
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
REDIS_URL=redis://localhost:6379

# Security
ALLOWED_HOSTS=example.com,www.example.com
CORS_ORIGINS=https://example.com,https://www.example.com

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
LOG_LEVEL=info

# External services
PAYMENT_API_KEY=live_key_123
EMAIL_API_KEY=live_email_key
```

## Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: velithon-api
  labels:
    app: velithon-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: velithon-api
  template:
    metadata:
      labels:
        app: velithon-api
    spec:
      containers:
      - name: api
        image: myregistry/velithon-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: velithon-api-service
spec:
  selector:
    app: velithon-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: velithon-api-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: velithon-api-service
            port:
              number: 80
```

## Monitoring and Logging

```python
# monitoring.py
import logging
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

# Sentry integration
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENV", "production"),
    traces_sample_rate=0.1
)

# Add Sentry middleware
app.add_middleware(SentryAsgiMiddleware)

# Structured logging
def setup_production_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/var/log/app/app.log")
        ]
    )

setup_production_logging()
```

## Security Checklist

- [ ] Disable debug mode
- [ ] Use strong secret keys
- [ ] Configure HTTPS/TLS
- [ ] Set security headers
- [ ] Implement rate limiting
- [ ] Use environment variables for secrets
- [ ] Regular security updates
- [ ] Database connection security
- [ ] Input validation and sanitization
- [ ] CORS configuration

## Performance Optimization

- [ ] Enable gzip compression
- [ ] Configure connection pooling
- [ ] Implement caching strategies
- [ ] Optimize database queries
- [ ] Use CDN for static assets
- [ ] Monitor response times
- [ ] Scale horizontally when needed
- [ ] Use async/await properly

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] Health checks working
- [ ] Monitoring setup
- [ ] Backup strategy in place
- [ ] Error tracking configured
- [ ] Load balancer configured
- [ ] Security hardening complete
- [ ] Documentation updated
