# Production Deployment Example

This example demonstrates a complete Velithon application ready for production deployment.

## Project Structure

```
production-example/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── nginx.conf            # Nginx configuration
├── .env.example          # Environment variables template
├── .dockerignore         # Docker ignore file
├── health.py             # Health check endpoints
├── middleware/
│   ├── __init__.py
│   ├── security.py       # Security middleware
│   ├── logging.py        # Logging middleware
│   └── metrics.py        # Monitoring middleware
├── api/
│   ├── __init__.py
│   ├── routes.py         # API routes
│   └── models.py         # Pydantic models
├── services/
│   ├── __init__.py
│   ├── database.py       # Database service
│   └── cache.py          # Cache service
├── static/               # Static files
├── templates/            # Templates (if needed)
└── tests/               # Test files
    ├── __init__.py
    ├── test_api.py
    └── test_health.py
```

## Application Code

### main.py
```python
import asyncio
import logging
from contextlib import asynccontextmanager
from velithon import Velithon
from velithon.responses import JSONResponse

from config import settings
from health import setup_health_routes
from middleware.security import SecurityMiddleware
from middleware.logging import LoggingMiddleware
from middleware.metrics import MetricsMiddleware
from api.routes import setup_api_routes
from services.database import DatabaseService
from services.cache import CacheService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: Velithon):
    """Application lifespan manager"""
    logger.info("Starting application...")
    
    # Initialize services
    app.state.db = DatabaseService(settings.database_url)
    app.state.cache = CacheService(settings.redis_url)
    
    await app.state.db.connect()
    await app.state.cache.connect()
    
    logger.info("Application started successfully")
    
    yield
    
    logger.info("Shutting down application...")
    
    # Cleanup services
    await app.state.db.disconnect()
    await app.state.cache.disconnect()
    
    logger.info("Application shutdown complete")

# Create application instance
app = Velithon(lifespan=lifespan)

# Add middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

# Setup routes
setup_health_routes(app)
setup_api_routes(app)

@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse({
        "message": "Welcome to Velithon Production Example",
        "version": settings.app_version,
        "environment": settings.env
    })

if __name__ == "__main__":
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    # This is for development only
    # In production, use: velithon run --app main:app
    app.run(
        host=settings.host,
        port=settings.port,
        workers=1 if settings.debug else settings.workers
    )
```

### config.py
```python
from typing import List, Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # Application
    app_name: str = "Velithon Production Example"
    app_version: str = "1.0.0"
    env: str = "development"
    debug: bool = False
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 4
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite:///./app.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    
    # Security
    secret_key: str = "change-me-in-production"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE"]
    cors_headers: List[str] = ["*"]
    
    # File uploads
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_path: str = "./uploads"
    allowed_extensions: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".pdf"]
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Monitoring
    enable_metrics: bool = True
    metrics_path: str = "/metrics"
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(',')]
        return v
    
    @validator('debug', pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

### requirements.txt
```
velithon>=0.3.1
uvloop>=0.19.0
redis>=5.0.0
asyncpg>=0.29.0
prometheus-client>=0.20.0
python-multipart>=0.0.20
aiofiles>=23.0.0
pydantic[email]>=2.11.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### Dockerfile
```dockerfile
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
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads static \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### .env.example
```bash
# Application Configuration
APP_NAME=Velithon Production Example
APP_VERSION=1.0.0
ENV=production
DEBUG=false

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/velithon_db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10

# Security Configuration
SECRET_KEY=your-super-secret-key-here-change-in-production
JWT_SECRET=your-jwt-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com,https://admin.your-domain.com
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_HEADERS=*

# File Upload Configuration
MAX_FILE_SIZE=10485760  # 10MB in bytes
UPLOAD_PATH=./uploads
ALLOWED_EXTENSIONS=.jpg,.jpeg,.png,.gif,.pdf,.docx

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Monitoring
ENABLE_METRICS=true
METRICS_PATH=/metrics

# External Services (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Cloud Storage (Optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET_NAME=your-bucket-name
```

This production example provides a solid foundation for deploying Velithon applications with proper configuration management, security, monitoring, and scalability considerations.

## Deployment Commands

### Local Development
```bash
# Copy environment file
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Docker Development
```bash
# Build and run with Docker Compose
docker-compose up --build

# Scale services
docker-compose up --scale app=3
```

### Production Deployment
```bash
# Build production image
docker build -t velithon-prod .

# Run with proper configuration
docker run -d \
  --name velithon-app \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  velithon-prod
```
