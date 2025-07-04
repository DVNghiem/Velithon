# Development Server

Learn how to set up and run Velithon applications in development mode with hot reloading and debugging features.

## Overview

Velithon provides excellent development server capabilities with hot reloading, automatic error handling, and debugging tools to enhance your development experience.

## Basic Development Setup

```python
from velithon import Velithon

app = Velithon(
    debug=True,  # Enable debug mode
    reload=True  # Enable hot reloading
)

@app.get("/")
async def root():
    return {"message": "Development server is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="debug"
    )
```

## Running with Uvicorn

```bash
# Basic development server
uvicorn main:app --reload --port 8000

# With debug logging
uvicorn main:app --reload --log-level debug

# Bind to all interfaces (for testing from other devices)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Custom configuration
uvicorn main:app \
    --reload \
    --reload-dir src \
    --reload-exclude "*.pyc" \
    --port 8000 \
    --log-config logging.yaml
```

## Development Configuration

```python
import os
from velithon import Velithon

# Environment-based configuration
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "127.0.0.1")

app = Velithon(
    debug=DEBUG,
    title="My API" + (" (Development)" if DEBUG else ""),
    description="API in development mode" if DEBUG else "Production API"
)

# Development-only routes
if DEBUG:
    @app.get("/dev/info")
    async def dev_info():
        return {
            "debug": DEBUG,
            "environment": os.getenv("ENV", "development"),
            "python_version": os.sys.version,
            "platform": os.sys.platform
        }

# Run configuration
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    )
```

## Hot Reloading Configuration

```python
# uvicorn_config.py
import os

# Development server configuration
RELOAD_DIRS = [
    "src",
    "app",
    "velithon_app"
]

RELOAD_INCLUDES = [
    "*.py",
    "*.yaml", 
    "*.yml",
    "*.json",
    "*.env"
]

RELOAD_EXCLUDES = [
    "*.pyc",
    "*.pyo",
    "__pycache__",
    ".pytest_cache",
    "*.log"
]

# Uvicorn run configuration
def run_dev_server():
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=RELOAD_DIRS,
        reload_includes=RELOAD_INCLUDES,
        reload_excludes=RELOAD_EXCLUDES,
        log_level="debug",
        use_colors=True,
        access_log=True
    )

if __name__ == "__main__":
    run_dev_server()
```

## Development Middleware

```python
from velithon import Request, Response
import time
import traceback

@app.middleware("http")
async def development_middleware(request: Request, call_next):
    # Add development headers
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Add timing information
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Debug-Mode"] = "true"
        
        return response
        
    except Exception as exc:
        # Enhanced error handling in development
        error_trace = traceback.format_exc()
        print(f"Error in {request.url}: {error_trace}")
        
        return Response(
            content={
                "error": str(exc),
                "traceback": error_trace.split("\n") if app.debug else None,
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "headers": dict(request.headers)
                }
            },
            status_code=500,
            media_type="application/json"
        )
```

## Database Development Setup

```python
from velithon.di import ServiceContainer

# Development database configuration
class DevelopmentDatabase:
    def __init__(self):
        self.url = "sqlite:///./dev.db"  # Local SQLite for development
        self.echo = True  # Log all SQL queries
        self.pool_pre_ping = True
    
    async def create_tables(self):
        """Create tables for development"""
        # Implementation for table creation
        pass
    
    async def seed_data(self):
        """Seed development data"""
        # Implementation for seeding test data
        pass

class DevelopmentContainer(ServiceContainer):
    database = DevelopmentDatabase()

# Initialize development data
@app.on_event("startup")
async def startup():
    if app.debug:
        db = DevelopmentContainer.database
        await db.create_tables()
        await db.seed_data()
```

## Development Logging

```python
import logging
import sys

def setup_development_logging():
    """Configure logging for development"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # File handler for errors
    file_handler = logging.FileHandler('development.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.ERROR)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.DEBUG)

# Setup logging
if DEBUG:
    setup_development_logging()
```

## Environment Variables

```bash
# .env file for development
DEBUG=true
ENV=development
HOST=127.0.0.1
PORT=8000
DATABASE_URL=sqlite:///./dev.db
LOG_LEVEL=debug
RELOAD=true

# Security (use weak keys in development only)
SECRET_KEY=development-secret-key-not-for-production
JWT_SECRET=dev-jwt-secret

# External services (use test/sandbox endpoints)
EXTERNAL_API_URL=https://api-sandbox.example.com
PAYMENT_API_KEY=test_key_123
```

## Development Scripts

```python
# scripts/dev.py
#!/usr/bin/env python3
"""Development server startup script"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Setup development environment"""
    # Load environment variables
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    # Set development defaults
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("LOG_LEVEL", "debug")

def install_dependencies():
    """Install development dependencies"""
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"
    ])

def run_server():
    """Run development server"""
    subprocess.run([
        "uvicorn", "main:app",
        "--reload",
        "--reload-dir", "src",
        "--host", os.getenv("HOST", "127.0.0.1"), 
        "--port", os.getenv("PORT", "8000"),
        "--log-level", os.getenv("LOG_LEVEL", "debug")
    ])

if __name__ == "__main__":
    setup_environment()
    
    if "--install" in sys.argv:
        install_dependencies()
    
    run_server()
```

## Make Development Easier

```makefile
# Makefile for development tasks
.PHONY: dev install-dev test lint format

dev:
	python scripts/dev.py

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest -v --cov=src

lint:
	ruff check src/
	mypy src/

format:
	ruff format src/
	isort src/

clean:
	find . -type d -name __pycache__ -delete
	find . -name "*.pyc" -delete
	rm -f development.log

reset-db:
	rm -f dev.db
	python -c "from main import app; import asyncio; asyncio.run(app.startup())"
```

## Development Best Practices

1. **Use environment variables** for configuration
2. **Enable debug mode** during development
3. **Set up hot reloading** for faster iteration
4. **Configure comprehensive logging** 
5. **Use development databases** (SQLite, etc.)
6. **Add development-only routes** for debugging
7. **Implement proper error handling** with stack traces
8. **Use development middleware** for enhanced debugging
9. **Set up automated testing** workflows
10. **Document development setup** for team members
