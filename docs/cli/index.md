# CLI Overview

Velithon provides a powerful command-line interface (CLI) for running applications, exporting documentation, and managing development workflows. The CLI is designed to be flexible and production-ready.

## 🚀 Quick Start

```bash
# Basic usage
velithon run

# Run with custom host and port
velithon run --host 0.0.0.0 --port 8080

# Run with multiple workers
velithon run --workers 4

# Run with specific app module
velithon run --app myproject.main:app
```

## 📋 Available Commands

### run

Run the Velithon application server.

```bash
velithon run [OPTIONS]
```

**Common Options:**
- `--app`: Application module and instance (default: `simple_app:app`)
- `--host`: Host to bind to (default: `127.0.0.1`)
- `--port`: Port to bind to (default: `8000`)
- `--workers`: Number of worker processes (default: `1`)
- `--reload`: Enable auto-reload on file changes
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### export-docs

Export API documentation to various formats.

```bash
velithon export-docs [OPTIONS]
```

**Options:**
- `--format`: Output format (markdown, html, pdf, json)
- `--output`: Output file path
- `--app`: Application module to export docs from

## 🔧 Configuration Options

### Server Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--host` | `str` | `127.0.0.1` | Host to bind to |
| `--port` | `int` | `8000` | Port to bind to |
| `--workers` | `int` | `1` | Number of worker processes |
| `--reload` | `bool` | `False` | Enable auto-reload |

### Logging Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--log-level` | `str` | `INFO` | Logging level |
| `--log-format` | `str` | `text` | Log format (text, json) |
| `--log-file` | `str` | `velithon.log` | Log file path |
| `--log-to-file` | `bool` | `False` | Enable file logging |
| `--max-bytes` | `int` | `10MB` | Max log file size |
| `--backup-count` | `int` | `7` | Number of backup log files |

### Performance Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--blocking-threads` | `int` | `None` | Number of blocking threads |
| `--runtime-threads` | `int` | `1` | Number of runtime threads |
| `--runtime-mode` | `str` | `st` | Runtime mode (st, mt) |
| `--loop` | `str` | `auto` | Event loop (auto, asyncio, uvloop) |
| `--task-impl` | `str` | `asyncio` | Task implementation |

### HTTP Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--http` | `str` | `auto` | HTTP version (auto, 1, 2) |
| `--http1-buffer-size` | `int` | `None` | HTTP/1 buffer size |
| `--http1-keep-alive` | `bool` | `None` | Enable HTTP/1 keep-alive |
| `--http2-max-concurrent-streams` | `int` | `None` | HTTP/2 max streams |

### SSL Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--ssl-certificate` | `str` | `None` | SSL certificate file |
| `--ssl-keyfile` | `str` | `None` | SSL private key file |
| `--ssl-keyfile-password` | `str` | `None` | SSL key password |

## 📝 Configuration Files

### Using Configuration Files

Create a `velithon.toml` file in your project root:

```toml
[server]
host = "0.0.0.0"
port = 8000
workers = 4
reload = false

[logging]
level = "INFO"
format = "json"
to_file = true
file = "logs/velithon.log"
max_bytes = 10485760  # 10MB
backup_count = 7

[performance]
runtime_mode = "mt"
runtime_threads = 4
loop = "uvloop"

[ssl]
certificate = "certs/server.crt"
keyfile = "certs/server.key"
```

Load configuration:

```bash
velithon run --config velithon.toml
```

### Environment Variables

Configure using environment variables:

```bash
export VELITHON_HOST=0.0.0.0
export VELITHON_PORT=8080
export VELITHON_WORKERS=4
export VELITHON_LOG_LEVEL=DEBUG

velithon run
```

## 🚀 Development Workflow

### Development Server

```bash
# Start development server with auto-reload
velithon run --reload --log-level DEBUG

# Development with custom app
velithon run --app myapp:app --reload --host 0.0.0.0
```

### Production Deployment

```bash
# Production server
velithon run \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level INFO \
  --log-to-file \
  --runtime-mode mt \
  --loop uvloop
```

### SSL/TLS Configuration

```bash
# HTTPS server
velithon run \
  --ssl-certificate /path/to/cert.pem \
  --ssl-keyfile /path/to/key.pem \
  --host 0.0.0.0 \
  --port 443
```

## 🔍 Monitoring and Debugging

### Debug Mode

```bash
# Enable debug logging
velithon run --log-level DEBUG --log-format json

# With detailed performance metrics
velithon run --log-level DEBUG --runtime-mode mt --runtime-threads 2
```

### Health Checks

```bash
# Run with health check endpoint
velithon run --health-check /health

# Custom health check configuration
velithon run --health-check-interval 30 --health-check-timeout 5
```

## 📊 Performance Tuning

### High-Performance Configuration

```bash
# Optimized for high throughput
velithon run \
  --workers $(nproc) \
  --runtime-mode mt \
  --runtime-threads 4 \
  --loop uvloop \
  --http 2 \
  --blocking-threads 20
```

### Memory Optimization

```bash
# Memory-optimized configuration
velithon run \
  --workers 2 \
  --runtime-mode st \
  --runtime-threads 1 \
  --blocking-threads 10
```

## 🐳 Docker Integration

### Docker Development

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Development
CMD ["velithon", "run", "--host", "0.0.0.0", "--reload"]
```

### Docker Production

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Production
CMD ["velithon", "run", "--host", "0.0.0.0", "--workers", "4", "--runtime-mode", "mt"]
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
      - VELITHON_LOG_LEVEL=INFO
      - VELITHON_WORKERS=4
    command: >
      velithon run
      --host 0.0.0.0
      --port 8000
      --workers 4
      --log-level INFO
```

## 🔧 Custom CLI Commands

### Extending the CLI

```python
# cli_extensions.py
import click
from velithon.cli import cli

@cli.command()
@click.option('--env', default='development')
def migrate(env):
    """Run database migrations."""
    print(f"Running migrations for {env}")
    # Migration logic here

@cli.command()
@click.option('--format', default='json')
def export_config(format):
    """Export current configuration."""
    print(f"Exporting config in {format} format")
    # Export logic here
```

Register custom commands:

```python
# main.py
from velithon import Velithon
from cli_extensions import cli

app = Velithon()

if __name__ == "__main__":
    cli()
```

## 🎯 Common Use Cases

### Development

```bash
# Quick development setup
velithon run --reload --log-level DEBUG --host 0.0.0.0

# With specific Python path
PYTHONPATH=/path/to/project velithon run --app myapp:app
```

### Testing

```bash
# Test server
velithon run --port 8888 --workers 1 --log-level WARNING

# Integration testing
velithon run --app tests.test_app:app --port 9999
```

### Staging

```bash
# Staging environment
velithon run \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --log-level INFO \
  --log-to-file \
  --runtime-mode mt
```

### Production

```bash
# Production deployment
velithon run \
  --host 0.0.0.0 \
  --port 8000 \
  --workers $(nproc) \
  --log-level WARNING \
  --log-to-file \
  --runtime-mode mt \
  --loop uvloop \
  --ssl-certificate /etc/ssl/cert.pem \
  --ssl-keyfile /etc/ssl/key.pem
```

## 🔒 Security Configuration

### HTTPS Only

```bash
# Force HTTPS
velithon run \
  --ssl-certificate cert.pem \
  --ssl-keyfile key.pem \
  --host 0.0.0.0 \
  --port 443 \
  --security-headers
```

### Production Security

```bash
# Secure production setup
velithon run \
  --ssl-certificate /etc/ssl/certs/app.crt \
  --ssl-keyfile /etc/ssl/private/app.key \
  --host 0.0.0.0 \
  --port 443 \
  --workers 4 \
  --log-level WARNING \
  --security-headers \
  --no-server-header
```
