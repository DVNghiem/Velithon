# Deployment

Velithon applications can be deployed in various environments from development to production. This guide covers deployment strategies, configuration, and best practices.

## Overview

Velithon is built on Granian (RSGI) for high-performance deployment. This section covers different deployment scenarios and optimization strategies.

## Development Deployment

### Local Development Server

```python
from velithon import Velithon

app = Velithon()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8000,
        debug=True,
        reload=True
    )
```

### Using the CLI

```bash
# Basic development server
velithon run app:app

# With custom host and port
velithon run app:app --host 0.0.0.0 --port 8080

# With reload for development
velithon run app:app --reload

# With debug mode
velithon run app:app --debug
```

## Production Deployment

### Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VELITHON_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["velithon", "run", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - VELITHON_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
```

### Nginx Configuration

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server web:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

        # Static files
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API requests
        location / {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

## Cloud Deployment

### AWS ECS

#### Task Definition

```json
{
  "family": "velithon-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
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
          "name": "VELITHON_ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:ssm:region:account:parameter/app/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/velithon-app",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Run

#### cloudbuild.yaml

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/velithon-app:$COMMIT_SHA', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/velithon-app:$COMMIT_SHA']
  
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'velithon-app'
      - '--image'
      - 'gcr.io/$PROJECT_ID/velithon-app:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--port'
      - '8000'
      - '--memory'
      - '1Gi'
      - '--cpu'
      - '1'
      - '--max-instances'
      - '100'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/velithon-app:$COMMIT_SHA'
```

### Azure Container Instances

```yaml
apiVersion: 2019-12-01
location: eastus
name: velithon-app
properties:
  containers:
  - name: velithon-app
    properties:
      image: yourregistry.azurecr.io/velithon-app:latest
      ports:
      - port: 8000
        protocol: TCP
      resources:
        requests:
          cpu: 1
          memoryInGB: 2
      environmentVariables:
      - name: VELITHON_ENV
        value: production
      - name: DATABASE_URL
        secureValue: postgresql://user:pass@host:5432/db
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 8000
    dnsNameLabel: velithon-app
```

## Kubernetes Deployment

### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: velithon-app
  labels:
    app: velithon-app
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
        image: velithon-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: VELITHON_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
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

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: velithon-app-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
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
            name: velithon-app-service
            port:
              number: 80
```

## Configuration Management

### Environment-based Configuration

```python
import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # App settings
    app_name: str = "Velithon App"
    version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    
    # Database
    database_url: str
    
    # Redis
    redis_url: Optional[str] = None
    
    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    
    # External services
    email_api_key: Optional[str] = None
    sentry_dsn: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Application factory
def create_app() -> Velithon:
    app = Velithon(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug
    )
    
    # Configure based on environment
    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn)
    
    return app

app = create_app()
```

### Environment Files

#### .env.development

```bash
VELITHON_ENV=development
DEBUG=true
HOST=127.0.0.1
PORT=8000
WORKERS=1
DATABASE_URL=sqlite:///./dev.db
SECRET_KEY=dev-secret-key
```

#### .env.production

```bash
VELITHON_ENV=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=4
DATABASE_URL=postgresql://user:pass@db:5432/prod
SECRET_KEY=super-secret-production-key
SENTRY_DSN=https://your-sentry-dsn
```

## Health Checks

### Application Health Checks

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse
import asyncio
import psutil
from datetime import datetime

app = Velithon()

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return OptimizedJSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        # Check database connection
        await check_database()
        
        # Check Redis connection
        await check_redis()
        
        return OptimizedJSONResponse({
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return OptimizedJSONResponse({
            "status": "not ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=503)

@app.get("/metrics")
async def metrics():
    """System metrics endpoint"""
    return OptimizedJSONResponse({
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "load_average": psutil.getloadavg(),
        "timestamp": datetime.utcnow().isoformat()
    })

async def check_database():
    """Check database connectivity"""
    # Implement your database check
    pass

async def check_redis():
    """Check Redis connectivity"""
    # Implement your Redis check
    pass
```

## Monitoring and Logging

### Structured Logging

```python
import logging
import json
from datetime import datetime
from velithon.middleware import Middleware

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
            
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
            
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)
logger.handlers[0].setFormatter(JSONFormatter())
logger.handlers[1].setFormatter(JSONFormatter())

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, protocol):
        if scope["type"] == "http":
            start_time = datetime.utcnow()
            
            # Add request ID
            import uuid
            request_id = str(uuid.uuid4())
            scope["request_id"] = request_id
            
            logger.info(
                "Request started",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "query_string": scope["query_string"].decode()
                }
            )
            
            try:
                await self.app(scope, protocol)
            except Exception as e:
                logger.error(
                    "Request failed",
                    extra={
                        "request_id": request_id,
                        "error": str(e)
                    }
                )
                raise
            finally:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    "Request completed",
                    extra={
                        "request_id": request_id,
                        "duration": duration
                    }
                )
        else:
            await self.app(scope, protocol)

app = Velithon(middleware=[Middleware(LoggingMiddleware)])
```

### Application Performance Monitoring

```python
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Configure Sentry
sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.ERROR
)

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[sentry_logging],
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment=os.getenv("VELITHON_ENV", "development")
)

# Custom metrics middleware
class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
        self.request_count = 0
        self.error_count = 0
    
    async def __call__(self, scope, protocol):
        if scope["type"] == "http":
            self.request_count += 1
            
            try:
                await self.app(scope, protocol)
            except Exception as e:
                self.error_count += 1
                sentry_sdk.capture_exception(e)
                raise
        else:
            await self.app(scope, protocol)

app = Velithon(middleware=[Middleware(MetricsMiddleware)])
```

## Performance Optimization

### Production Optimizations

```python
from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.gzip import GzipMiddleware
from velithon.middleware.cors import CORSMiddleware

app = Velithon(
    # Disable debug mode
    debug=False,
    
    # Enable response compression
    middleware=[
        Middleware(GzipMiddleware, minimum_size=1024),
        Middleware(CORSMiddleware, 
                  allow_origins=["https://yourdomain.com"],
                  allow_methods=["GET", "POST"],
                  allow_headers=["*"])
    ]
)

# Connection pooling for database
import asyncpg

async def create_db_pool():
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=5,
        max_size=20,
        command_timeout=60
    )

# Cache configuration
import aioredis

async def create_redis_pool():
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20
    )
```

### Auto-scaling Configuration

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: velithon-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: velithon-app
  minReplicas: 2
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

## Next Steps

- [Production Configuration →](production.md)
- [Deployment →](development.md)