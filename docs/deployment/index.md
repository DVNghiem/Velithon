# Deployment

This guide covers deploying Velithon applications to various environments, from development to production.

## Overview

Velithon applications can be deployed using multiple strategies:

- **Direct Deployment**: Run directly with Granian RSGI server
- **Container Deployment**: Docker and Kubernetes
- **Cloud Deployment**: AWS, Google Cloud, Azure
- **Serverless**: Function-as-a-Service platforms
- **Reverse Proxy**: Nginx, Apache, Cloudflare

## 🚀 Quick Deployment

### Local Development

```bash
# Install Velithon
pip install velithon

# Create your application
python main.py

# Or use CLI
velithon run --app main:app --host 0.0.0.0 --port 8000
```

### Production with Granian

```bash
# Run with multiple workers
velithon run --app main:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL/TLS
velithon run --app main:app --ssl-certificate cert.pem --ssl-keyfile key.pem

# With custom configuration
velithon run \
  --app main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level INFO \
  --http 2 \
  --runtime-mode mt
```

## 🐳 Docker Deployment

### Basic Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-stage Dockerfile

```dockerfile
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=mydb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

## ☁️ Cloud Deployment

### AWS Deployment

#### AWS ECS (Elastic Container Service)

```yaml
# task-definition.json
{
  "family": "velithon-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "velithon-app",
      "image": "your-registry/velithon-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@db:5432/mydb"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/velithon-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### AWS Lambda (Serverless)

```python
# lambda_function.py
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/")
async def root():
    return JSONResponse({"message": "Hello from Lambda!"})

# Lambda handler
def lambda_handler(event, context):
    # Convert API Gateway event to Velithon request
    # Implementation depends on your setup
    pass
```

### Google Cloud Platform

#### Google Cloud Run

```dockerfile
# Dockerfile for Cloud Run
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run expects PORT environment variable
ENV PORT=8000

CMD exec velithon run --app main:app --host 0.0.0.0 --port $PORT
```

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/velithon-app', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/velithon-app']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'velithon-app'
      - '--image'
      - 'gcr.io/$PROJECT_ID/velithon-app'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
```

### Azure

#### Azure Container Instances

```yaml
# azure-deployment.yaml
apiVersion: 2019-12-01
location: eastus
properties:
  containers:
  - name: velithon-app
    properties:
      image: your-registry/velithon-app:latest
      ports:
      - port: 8000
      environmentVariables:
      - name: DATABASE_URL
        value: "postgresql://user:pass@db:5432/mydb"
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 8000
```

## 🚢 Kubernetes Deployment

### Basic Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: velithon-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: velithon-app
  template:
    metadata:
      labels:
        app: velithon-app
    spec:
      containers:
      - name: velithon-app
        image: your-registry/velithon-app:latest
        ports:
        - containerPort: 8000
        env:
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
  name: velithon-app-service
spec:
  selector:
    app: velithon-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Kubernetes with Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: velithon-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: velithon-app-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: velithon-app-service
            port:
              number: 80
```

## 🔧 Production Configuration

### Environment Variables

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
WORKERS=4
```

### Application Configuration

```python
# config.py
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/mydb"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str = "your-secret-key"
    
    # Logging
    log_level: str = "INFO"
    
    # Server
    workers: int = 4
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Production Application

```python
# main.py
import os
from velithon import Velithon
from velithon.middleware import (
    LoggingMiddleware,
    CORSMiddleware,
    CompressionMiddleware,
    PrometheusMiddleware
)
from velithon.responses import JSONResponse

# Load configuration
from config import settings

app = Velithon(
    title="Production API",
    description="Production-ready Velithon application",
    version="1.0.0",
    middleware=[
        LoggingMiddleware(
            log_level=settings.log_level,
            log_format="json"
        ),
        CORSMiddleware(
            origins=["https://your-domain.com"],
            allow_credentials=True
        ),
        CompressionMiddleware(),
        PrometheusMiddleware()
    ]
)

@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    })

@app.get("/")
async def root():
    return JSONResponse({"message": "Production API"})

if __name__ == "__main__":
    app._serve(
        app="main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level
    )
```

## 🔒 Security Configuration

### SSL/TLS Configuration

```python
# ssl_config.py
import ssl

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(
    certfile="path/to/cert.pem",
    keyfile="path/to/key.pem"
)

# Run with SSL
app._serve(
    app="main:app",
    ssl_certificate="path/to/cert.pem",
    ssl_keyfile="path/to/key.pem"
)
```

### Security Headers

```python
from velithon.middleware import SecurityMiddleware

app = Velithon(
    middleware=[
        SecurityMiddleware(
            add_security_headers=True,
            content_security_policy="default-src 'self'",
            strict_transport_security="max-age=31536000; includeSubDomains"
        )
    ]
)
```

## 📊 Monitoring & Logging

### Prometheus Metrics

```python
from velithon.middleware import PrometheusMiddleware

app = Velithon(
    middleware=[
        PrometheusMiddleware(
            metrics_path="/metrics",
            include_http_requests_total=True,
            include_http_request_duration_seconds=True
        )
    ]
)
```

### Structured Logging

```python
import logging
from velithon.logging import configure_logger

# Configure logging
configure_logger(
    level="INFO",
    format="json",
    include_correlation_id=True
)

logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World"}
```

## 🚀 Performance Optimization

### Worker Configuration

```bash
# Calculate optimal workers
# Formula: (2 x CPU cores) + 1
# For 4 CPU cores: (2 x 4) + 1 = 9 workers

velithon run --app main:app --workers 9
```

### Caching Strategy

```python
from velithon.cache import Cache

cache = Cache(redis_url="redis://localhost:6379")

@app.get("/cached-data")
async def get_cached_data():
    # Try to get from cache
    cached = await cache.get("data_key")
    if cached:
        return cached
    
    # Generate data
    data = {"expensive": "data"}
    
    # Cache for 1 hour
    await cache.set("data_key", data, expire=3600)
    
    return data
```

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio httpx
    - name: Run tests
      run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker image
      run: |
        docker build -t your-registry/velithon-app:${{ github.sha }} .
        docker push your-registry/velithon-app:${{ github.sha }}
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/velithon-app velithon-app=your-registry/velithon-app:${{ github.sha }}
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-asyncio httpx
    - pytest

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t your-registry/velithon-app:$CI_COMMIT_SHA .
    - docker push your-registry/velithon-app:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/velithon-app velithon-app=your-registry/velithon-app:$CI_COMMIT_SHA
```

## 📈 Scaling Strategies

### Horizontal Scaling

```yaml
# horizontal-pod-autoscaler.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: velithon-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: velithon-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing

```python
# Load balancer configuration
from velithon.middleware import ProxyMiddleware

app = Velithon(
    middleware=[
        ProxyMiddleware(
            upstream_urls=[
                "http://backend1:8000",
                "http://backend2:8000",
                "http://backend3:8000"
            ],
            health_check_path="/health",
            load_balancing_strategy="round_robin"
        )
    ]
)
```

This comprehensive deployment guide covers all aspects of deploying Velithon applications from development to production, ensuring high performance, security, and scalability.