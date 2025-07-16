# Prometheus Metrics

Velithon provides built-in Prometheus metrics collection through middleware that automatically tracks HTTP request metrics and exposes them in Prometheus format for monitoring and observability.

## 🌟 Features

- **Automatic Metrics Collection**: Collects HTTP request metrics without code changes
- **Prometheus Compatible**: Exports metrics in standard Prometheus text format
- **Performance Optimized**: Multiple middleware variants for different performance needs
- **Customizable**: Configurable metrics collection and path normalization
- **Zero Dependencies**: Built-in implementation without external Prometheus libraries

## 📊 Collected Metrics

### HTTP Request Metrics

- **`velithon_http_requests_total`** (Counter): Total number of HTTP requests
  - Labels: `method`, `path`, `status_code`

- **`velithon_http_request_duration_seconds`** (Histogram): Request duration in seconds
  - Labels: `method`, `path`
  - Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10

- **`velithon_http_request_size_bytes`** (Histogram): Request size in bytes
  - Labels: `method`, `path`

- **`velithon_http_response_size_bytes`** (Histogram): Response size in bytes
  - Labels: `method`, `path`

### Application Metrics

- **`velithon_http_requests_active`** (Gauge): Number of currently active requests
- **`velithon_app_uptime_seconds`** (Counter): Application uptime in seconds

## 🚀 Quick Start

### Basic Usage

```python
from velithon import Velithon
from velithon.middleware import Middleware, PrometheusMiddleware

app = Velithon(
    middleware=[
        Middleware(PrometheusMiddleware)
    ]
)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}
```

### Custom Configuration

```python
from velithon.middleware import Middleware, PrometheusMiddleware

app = Velithon(
    middleware=[
        Middleware(
            PrometheusMiddleware,
            metrics_path="/custom-metrics",  # Custom metrics endpoint
            collect_request_size=True,       # Collect request sizes
            collect_response_size=True,      # Collect response sizes
            exclude_paths=["/health", "/ping"],  # Exclude health checks
        )
    ]
)
```

## 🏎️ High-Performance Usage

For high-throughput applications, use `FastPrometheusMiddleware`:

```python
from velithon.middleware import Middleware, FastPrometheusMiddleware

app = Velithon(
    middleware=[
        Middleware(
            FastPrometheusMiddleware,
            metrics_path="/metrics",
            # Automatic cleanup of old metrics data
            # Optimized for high request rates
        )
    ]
)
```

## 🔧 Advanced Configuration

### Custom Path Normalization

Group similar paths together for better metrics aggregation:

```python
def normalize_api_path(path: str) -> str:
    import re
    # Replace user IDs with placeholder
    path = re.sub(r'/users/\d+', '/users/{id}', path)
    # Replace API versions
    path = re.sub(r'/api/v\d+/', '/api/v{version}/', path)
    return path

app = Velithon(
    middleware=[
        Middleware(
            PrometheusMiddleware,
            path_normalizer=normalize_api_path
        )
    ]
)
```

### Exclude Specific Paths

Exclude health checks and internal endpoints from metrics:

```python
app = Velithon(
    middleware=[
        Middleware(
            PrometheusMiddleware,
            exclude_paths=[
                "/health",
                "/ready", 
                "/ping",
                "/internal/status"
            ]
        )
    ]
)
```

## 📈 Metrics Endpoint

By default, metrics are exposed at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Example output:
```
# HELP velithon_http_requests_total Total number of HTTP requests
# TYPE velithon_http_requests_total counter
velithon_http_requests_total{method="GET",path="/users/{id}",status_code="200"} 42
velithon_http_requests_total{method="POST",path="/users",status_code="201"} 5

# HELP velithon_http_request_duration_seconds HTTP request duration in seconds
# TYPE velithon_http_request_duration_seconds histogram
velithon_http_request_duration_seconds_bucket{method="GET",path="/users/{id}",le="0.005"} 10
velithon_http_request_duration_seconds_bucket{method="GET",path="/users/{id}",le="0.01"} 25
velithon_http_request_duration_seconds_bucket{method="GET",path="/users/{id}",le="+Inf"} 42
velithon_http_request_duration_seconds_count{method="GET",path="/users/{id}"} 42
velithon_http_request_duration_seconds_sum{method="GET",path="/users/{id}"} 1.23

# HELP velithon_http_requests_active Number of active HTTP requests
# TYPE velithon_http_requests_active gauge
velithon_http_requests_active 3

# HELP velithon_app_uptime_seconds Application uptime in seconds
# TYPE velithon_app_uptime_seconds counter
velithon_app_uptime_seconds 3600.5
```

## 🐳 Docker & Prometheus Setup

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'velithon-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    depends_on:
      - app
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
```

## 📊 Grafana Dashboard

### Sample Queries

**Request Rate:**
```promql
rate(velithon_http_requests_total[5m])
```

**Average Response Time:**
```promql
rate(velithon_http_request_duration_seconds_sum[5m]) / 
rate(velithon_http_request_duration_seconds_count[5m])
```

**Error Rate:**
```promql
rate(velithon_http_requests_total{status_code=~"5.."}[5m]) / 
rate(velithon_http_requests_total[5m])
```

**95th Percentile Response Time:**
```promql
histogram_quantile(0.95, 
  rate(velithon_http_request_duration_seconds_bucket[5m])
)
```

## ⚡ Performance Considerations

### Middleware Variants

1. **`PrometheusMiddleware`**: Standard implementation
   - Good for most applications
   - Full feature set

2. **`FastPrometheusMiddleware`**: Optimized implementation  
   - Automatic metric cleanup
   - Reduced memory usage
   - Better for high-throughput apps

3. **`RustPrometheusMiddleware`**: Alias for `FastPrometheusMiddleware`
   - Compatible with Rust middleware optimizer

### Optimization Tips

1. **Use path normalization** to avoid metric explosion
2. **Exclude health check endpoints** from metrics
3. **Use FastPrometheusMiddleware** for high-traffic applications
4. **Monitor metric cardinality** to prevent memory issues

### Memory Management

The `FastPrometheusMiddleware` automatically:
- Cleans up old duration data every 5 minutes
- Keeps only the last 1000 requests per endpoint
- Prevents memory leaks in long-running applications

## 🔍 Monitoring Best Practices

### Alerting Rules

```yaml
groups:
  - name: velithon_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(velithon_http_requests_total{status_code=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: High error rate detected
          
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(velithon_http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High response time detected
```

### Dashboard Panels

1. **Request Rate by Endpoint**
2. **Response Time Distribution** 
3. **Error Rate by Status Code**
4. **Active Requests**
5. **Application Uptime**

## 🎯 Integration Examples

### With Authentication

```python
from velithon.middleware import Middleware, AuthenticationMiddleware, PrometheusMiddleware

app = Velithon(
    middleware=[
        # Authentication first
        Middleware(AuthenticationMiddleware),
        # Then metrics collection
        Middleware(PrometheusMiddleware),
    ]
)
```

### With Multiple Middleware

```python
from velithon.middleware import (
    Middleware, CORSMiddleware, LoggingMiddleware, 
    PrometheusMiddleware, CompressionMiddleware
)

app = Velithon(
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"]),
        Middleware(PrometheusMiddleware),
        Middleware(LoggingMiddleware),
        Middleware(CompressionMiddleware),
    ]
)
```

## 🔗 See Also

- [Middleware Guide](middleware.md)
- [Performance Optimization](../advanced/performance.md)
- [Deployment Guide](../deployment/production.md)
- [Monitoring Guide](../deployment/monitoring.md)
