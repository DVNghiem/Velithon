# CLI and Server Configuration

## Command Line Interface

The Velithon CLI provides comprehensive server configuration:

```bash
velithon run --help
```

## Basic Usage

```bash
# Basic run
velithon run --app main:app

# With custom host and port
velithon run --app main:app --host 0.0.0.0 --port 8080

# With multiple workers
velithon run --app main:app --workers 4

# Development mode with auto-reload
velithon run --app main:app --reload --log-level DEBUG
```

## Logging Configuration

```bash
# Enable file logging
velithon run --app main:app --log-to-file --log-file app.log

# JSON format logging
velithon run --app main:app --log-format json --log-level INFO

# Log rotation
velithon run --app main:app --log-to-file --max-bytes 10485760 --backup-count 7
```

## SSL Configuration

```bash
# Enable HTTPS
velithon run --app main:app \
    --ssl-certificate cert.pem \
    --ssl-keyfile key.pem \
    --ssl-keyfile-password mypassword
```

## HTTP Configuration

```bash
# HTTP/2 support
velithon run --app main:app --http 2

# HTTP/1 settings
velithon run --app main:app \
    --http1-keep-alive \
    --http1-header-read-timeout 30000

# HTTP/2 settings
velithon run --app main:app \
    --http2-max-concurrent-streams 100 \
    --http2-initial-connection-window-size 1048576
```

## Performance Tuning

```bash
# Threading configuration
velithon run --app main:app \
    --runtime-threads 4 \
    --blocking-threads 10 \
    --runtime-mode mt

# Event loop selection
velithon run --app main:app --loop uvloop

# Backpressure control
velithon run --app main:app --backpressure 1000
```
