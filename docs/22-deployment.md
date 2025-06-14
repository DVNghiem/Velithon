# Deployment Guide

This guide covers different deployment strategies for Velithon applications in production environments.

## Table of Contents

1. [Basic Production Deployment](#basic-production-deployment)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Platform Deployment](#cloud-platform-deployment)
4. [Load Balancing and Scaling](#load-balancing-and-scaling)
5. [Environment Configuration](#environment-configuration)
6. [Security Considerations](#security-considerations)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Performance Optimization](#performance-optimization)

## Basic Production Deployment

### Prerequisites

- Python 3.10 or higher
- Process manager (systemd, supervisor, or PM2)
- Reverse proxy (nginx, Apache, or cloud load balancer)

### Installation

```bash
# Create a dedicated user for the application
sudo useradd -m -s /bin/bash velithon

# Switch to the velithon user
sudo su - velithon

# Create application directory
mkdir -p /home/velithon/app
cd /home/velithon/app

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Velithon
pip install velithon

# Copy your application files
# ... (your app files)
```

### Systemd Service Configuration

Create a systemd service file at `/etc/systemd/system/velithon-app.service`:

```ini
[Unit]
Description=Velithon Web Application
After=network.target

[Service]
Type=exec
User=velithon
Group=velithon
WorkingDirectory=/home/velithon/app
Environment=PATH=/home/velithon/app/venv/bin
Environment=PYTHONPATH=/home/velithon/app
ExecStart=/home/velithon/app/venv/bin/velithon run --app main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable velithon-app
sudo systemctl start velithon-app
sudo systemctl status velithon-app
```

### Nginx Configuration

Create an nginx configuration file at `/etc/nginx/sites-available/velithon-app`:

```nginx
upstream velithon_backend {
    server 127.0.0.1:8000;
    # Add more servers for load balancing
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml;

    location / {
        proxy_pass http://velithon_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (if needed)
    location /static/ {
        alias /home/velithon/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/velithon-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Docker Deployment

### Dockerfile

Create a `Dockerfile` in your project root:

```dockerfile
# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/velithon_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - velithon-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: velithon_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - velithon-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - velithon-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - velithon-network

volumes:
  postgres_data:

networks:
  velithon-network:
    driver: bridge
```

### Building and Running

```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale the application
docker-compose up -d --scale app=3

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Cloud Platform Deployment

### AWS Deployment with ECS

1. **Create ECR Repository**:
```bash
aws ecr create-repository --repository-name velithon-app
```

2. **Build and Push Docker Image**:
```bash
# Get login token
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# Build and tag image
docker build -t velithon-app .
docker tag velithon-app:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/velithon-app:latest

# Push image
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/velithon-app:latest
```

3. **ECS Task Definition** (`task-definition.json`):
```json
{
  "family": "velithon-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "velithon-app",
      "image": "<account-id>.dkr.ecr.us-west-2.amazonaws.com/velithon-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENV",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/velithon-app",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Platform (Cloud Run)

1. **Create Dockerfile** (as shown above)

2. **Deploy to Cloud Run**:
```bash
# Build and deploy
gcloud run deploy velithon-app \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8000 \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10
```

### Heroku Deployment

1. **Create `Procfile`**:
```
web: velithon run --app main:app --host 0.0.0.0 --port $PORT --workers 2
```

2. **Create `runtime.txt`**:
```
python-3.12.0
```

3. **Deploy**:
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set ENV=production

# Deploy
git push heroku main
```

## Load Balancing and Scaling

### Horizontal Scaling

1. **Multiple Workers**:
```bash
# Single server with multiple workers
velithon run --app main:app --workers 8 --host 0.0.0.0 --port 8000
```

2. **Multiple Servers**:
```bash
# Server 1
velithon run --app main:app --workers 4 --host 0.0.0.0 --port 8000

# Server 2
velithon run --app main:app --workers 4 --host 0.0.0.0 --port 8001

# Server 3
velithon run --app main:app --workers 4 --host 0.0.0.0 --port 8002
```

3. **Load Balancer Configuration** (nginx):
```nginx
upstream velithon_backend {
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
}
```

### Auto-scaling with Kubernetes

Create deployment configuration (`k8s-deployment.yaml`):

```yaml
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
        - name: ENV
          value: "production"
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
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: velithon-service
spec:
  selector:
    app: velithon-app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: velithon-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: velithon-app
  minReplicas: 3
  maxReplicas: 20
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

## Environment Configuration

### Environment Variables

Create a `.env` file for local development:

```bash
# Application
ENV=development
DEBUG=true
APP_NAME=Velithon App
APP_VERSION=1.0.0

# Server
HOST=127.0.0.1
PORT=8000
WORKERS=1
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-here
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# External Services
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AWS (if using)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-west-2
```

### Configuration Management

Create a `config.py` file:

```python
import os
from typing import List
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Application
    env: str = "development"
    debug: bool = False
    app_name: str = "Velithon App"
    app_version: str = "1.0.0"
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite:///./app.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "change-me-in-production"
    jwt_secret: str = "change-me-in-production"
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # File uploads
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_path: str = "./uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

## Security Considerations

### SSL/TLS Configuration

1. **Generate SSL Certificate** (Let's Encrypt):
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

2. **SSL Configuration in Application**:
```bash
velithon run --app main:app \
    --ssl-certificate /path/to/cert.pem \
    --ssl-keyfile /path/to/key.pem \
    --host 0.0.0.0 \
    --port 443
```

### Security Headers Middleware

```python
from velithon import Velithon
from velithon.responses import Response

app = Velithon()

@app.middleware
async def security_headers_middleware(request, call_next):
    response: Response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
```

### Environment Separation

Keep production secrets separate from code:

```python
# Use environment variables
import os

# Production
SECRET_KEY = os.environ.get("SECRET_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Or use external secret management
# AWS Secrets Manager, HashiCorp Vault, etc.
```

## Monitoring and Logging

### Application Logging

```python
import logging
from velithon import Velithon

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Velithon()

@app.middleware
async def logging_middleware(request, call_next):
    start_time = time.time()
    
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response
```

### Health Check Endpoints

```python
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return JSONResponse({"status": "healthy", "timestamp": time.time()})

@app.get("/ready")
async def readiness_check():
    """Readiness check with dependencies"""
    try:
        # Check database connection
        # await database.execute("SELECT 1")
        
        # Check Redis connection
        # await redis.ping()
        
        return JSONResponse({"status": "ready", "timestamp": time.time()})
    except Exception as e:
        return JSONResponse(
            {"status": "not ready", "error": str(e)}, 
            status_code=503
        )
```

### Metrics and Monitoring

Install monitoring tools:

```bash
pip install prometheus-client
```

Add metrics middleware:

```python
from prometheus_client import Counter, Histogram, generate_latest
from velithon.responses import PlainTextResponse

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware
async def metrics_middleware(request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(time.time() - start_time)
    
    return response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest())
```

## Performance Optimization

### Production Configuration

```bash
# Optimal production settings
velithon run \
    --app main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 8 \
    --runtime-mode mt \
    --loop uvloop \
    --http 2 \
    --backpressure 1000 \
    --log-level INFO \
    --log-format json
```

### Memory and CPU Optimization

1. **Worker Process Calculation**:
```bash
# CPU-bound applications
workers = (CPU_cores * 2) + 1

# I/O-bound applications
workers = CPU_cores * 4

# High-concurrency applications
workers = CPU_cores * 8
```

2. **Memory Considerations**:
```bash
# Monitor memory usage
ps aux | grep velithon

# Set memory limits in Docker
docker run --memory="512m" --cpus="1.0" your-app
```

### Database Optimization

```python
# Connection pooling
import asyncpg
from velithon import Velithon

app = Velithon()

@app.on_startup
async def setup_database():
    app.state.db_pool = await asyncpg.create_pool(
        database_url,
        min_size=10,
        max_size=50,
        command_timeout=60
    )

@app.on_shutdown
async def cleanup_database():
    await app.state.db_pool.close()
```

### Caching Strategy

```python
import redis.asyncio as redis
from velithon import Velithon

app = Velithon()

@app.on_startup
async def setup_redis():
    app.state.redis = redis.Redis.from_url("redis://localhost:6379")

@app.get("/api/data/{item_id}")
async def get_data(item_id: int):
    # Try cache first
    cached = await app.state.redis.get(f"data:{item_id}")
    if cached:
        return JSONResponse(json.loads(cached))
    
    # Fetch from database
    data = await fetch_from_db(item_id)
    
    # Cache result
    await app.state.redis.setex(
        f"data:{item_id}", 
        300,  # 5 minutes
        json.dumps(data)
    )
    
    return JSONResponse(data)
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**:
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

2. **Permission Denied**:
```bash
# Fix file permissions
chmod +x velithon
chown -R velithon:velithon /home/velithon/app
```

3. **SSL Certificate Issues**:
```bash
# Verify certificate
openssl x509 -in certificate.crt -text -noout

# Test SSL connection
openssl s_client -connect your-domain.com:443
```

4. **High Memory Usage**:
```bash
# Monitor memory
htop
# or
ps aux --sort=-%mem | head

# Restart services if needed
sudo systemctl restart velithon-app
```

### Debugging

Enable debug mode for troubleshooting:

```bash
velithon run --app main:app --log-level DEBUG --reload
```

Check application logs:

```bash
# Systemd logs
sudo journalctl -u velithon-app -f

# Application logs
tail -f /home/velithon/app/logs/app.log

# Docker logs
docker-compose logs -f app
```

This comprehensive deployment guide should help you deploy Velithon applications in various environments with proper security, monitoring, and performance optimization.
