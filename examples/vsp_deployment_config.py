"""VSP Protocol Deployment Configuration.

This file shows how to configure and deploy the enhanced VSP protocol
in production environments with proper TLS, clustering, and monitoring.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class VSPServerConfig:
    """Configuration for VSP server deployment."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 9000
    worker_count: int = 4
    
    # QUIC settings
    enable_quic: bool = True
    quic_port: int = 9001
    max_concurrent_streams: int = 1000
    max_idle_timeout_seconds: int = 60
    
    # TLS settings
    cert_file: str = "/etc/ssl/certs/vsp-server.crt"
    key_file: str = "/etc/ssl/private/vsp-server.key"
    enable_tls: bool = True
    
    # Compression settings
    default_compression: str = "zstd"
    compression_level: int = 3
    
    # Service registry settings
    registry_cache_ttl_seconds: int = 300
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 5
    
    # Load balancing
    load_balancing_algorithm: str = "weighted_round_robin"
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = True
    log_level: str = "INFO"


@dataclass
class VSPClientConfig:
    """Configuration for VSP client connections."""

    # Connection settings
    connect_timeout_ms: int = 5000
    request_timeout_ms: int = 30000
    max_retries: int = 3
    
    # Transport settings
    enable_adaptive_transport: bool = True
    prefer_quic: bool = True
    tcp_fallback: bool = True
    
    # Caching settings
    enable_response_cache: bool = True
    cache_ttl_seconds: int = 300
    max_cache_size: int = 10000
    
    # Compression settings
    enable_compression: bool = True
    compression_type: str = "zstd"
    
    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60


# Production deployment configurations
PRODUCTION_SERVER_CONFIG = VSPServerConfig(
    host="0.0.0.0",
    port=9000,
    worker_count=8,
    enable_quic=True,
    quic_port=9001,
    max_concurrent_streams=5000,
    max_idle_timeout_seconds=300,
    cert_file="/etc/ssl/certs/production-vsp.crt",
    key_file="/etc/ssl/private/production-vsp.key",
    enable_tls=True,
    default_compression="zstd",
    compression_level=6,
    registry_cache_ttl_seconds=600,
    health_check_interval_seconds=15,
    health_check_timeout_seconds=3,
    load_balancing_algorithm="least_response_time",
    circuit_breaker_threshold=10,
    circuit_breaker_timeout_seconds=120,
    enable_metrics=True,
    metrics_port=9090,
    tracing_enabled=True,
    log_level="WARN",
)

PRODUCTION_CLIENT_CONFIG = VSPClientConfig(
    connect_timeout_ms=3000,
    request_timeout_ms=60000,
    max_retries=5,
    enable_adaptive_transport=True,
    prefer_quic=True,
    tcp_fallback=True,
    enable_response_cache=True,
    cache_ttl_seconds=600,
    max_cache_size=50000,
    enable_compression=True,
    compression_type="zstd",
    circuit_breaker_threshold=10,
    circuit_breaker_timeout_seconds=120,
)

# Development configurations
DEVELOPMENT_SERVER_CONFIG = VSPServerConfig(
    host="localhost",
    port=8000,
    worker_count=2,
    enable_quic=True,
    quic_port=8001,
    enable_tls=False,  # Use self-signed certs in dev
    default_compression="none",  # Disable compression for easier debugging
    log_level="DEBUG",
    tracing_enabled=True,
)

DEVELOPMENT_CLIENT_CONFIG = VSPClientConfig(
    connect_timeout_ms=10000,
    request_timeout_ms=30000,
    max_retries=1,
    enable_response_cache=False,  # Disable cache for development
    enable_compression=False,
    circuit_breaker_threshold=3,
)

# High-throughput configurations for heavy workloads
HIGH_THROUGHPUT_SERVER_CONFIG = VSPServerConfig(
    host="0.0.0.0",
    port=9000,
    worker_count=16,
    enable_quic=True,
    quic_port=9001,
    max_concurrent_streams=10000,
    max_idle_timeout_seconds=600,
    default_compression="zstd",
    compression_level=1,  # Fast compression
    registry_cache_ttl_seconds=1800,
    health_check_interval_seconds=60,
    load_balancing_algorithm="least_connections",
    circuit_breaker_threshold=20,
    log_level="ERROR",  # Minimal logging for performance
)

HIGH_THROUGHPUT_CLIENT_CONFIG = VSPClientConfig(
    connect_timeout_ms=2000,
    request_timeout_ms=10000,
    max_retries=2,
    enable_adaptive_transport=True,
    enable_response_cache=True,
    cache_ttl_seconds=1800,
    max_cache_size=100000,
    enable_compression=True,
    compression_type="zstd",
    circuit_breaker_threshold=15,
)


def get_config(environment: str, component: str) -> Any:
    """Get configuration for specific environment and component."""
    configs = {
        "production": {
            "server": PRODUCTION_SERVER_CONFIG,
            "client": PRODUCTION_CLIENT_CONFIG,
        },
        "development": {
            "server": DEVELOPMENT_SERVER_CONFIG,
            "client": DEVELOPMENT_CLIENT_CONFIG,
        },
        "high_throughput": {
            "server": HIGH_THROUGHPUT_SERVER_CONFIG,
            "client": HIGH_THROUGHPUT_CLIENT_CONFIG,
        },
    }
    
    if environment not in configs:
        msg = f"Unknown environment: {environment}"
        raise ValueError(msg)
    
    if component not in configs[environment]:
        msg = f"Unknown component: {component}"
        raise ValueError(msg)
    
    return configs[environment][component]


# Docker Compose configuration for production deployment
DOCKER_COMPOSE_TEMPLATE = """
version: '3.8'

services:
  vsp-server:
    image: velithon/vsp-server:latest
    ports:
      - "9000:9000"   # TCP/HTTP
      - "9001:9001"   # QUIC
      - "9090:9090"   # Metrics
    environment:
      - VSP_HOST=0.0.0.0
      - VSP_PORT=9000
      - VSP_QUIC_PORT=9001
      - VSP_WORKERS=8
      - VSP_LOG_LEVEL=INFO
      - VSP_ENABLE_TLS=true
      - VSP_CERT_FILE=/certs/server.crt
      - VSP_KEY_FILE=/certs/server.key
    volumes:
      - ./certs:/certs:ro
      - ./logs:/app/logs
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  vsp-registry:
    image: velithon/vsp-registry:latest
    ports:
      - "8500:8500"
    environment:
      - REGISTRY_PORT=8500
      - REGISTRY_CACHE_TTL=600
    deploy:
      replicas: 2

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:

networks:
  default:
    driver: bridge
"""

# Kubernetes deployment configuration
KUBERNETES_DEPLOYMENT_TEMPLATE = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vsp-server
  labels:
    app: vsp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vsp-server
  template:
    metadata:
      labels:
        app: vsp-server
    spec:
      containers:
      - name: vsp-server
        image: velithon/vsp-server:latest
        ports:
        - containerPort: 9000
          name: tcp-port
        - containerPort: 9001
          name: quic-port
        - containerPort: 9090
          name: metrics-port
        env:
        - name: VSP_HOST
          value: "0.0.0.0"
        - name: VSP_PORT
          value: "9000"
        - name: VSP_QUIC_PORT
          value: "9001"
        - name: VSP_WORKERS
          value: "4"
        - name: VSP_LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 9090
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 9090
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: certs
          mountPath: /certs
          readOnly: true
      volumes:
      - name: certs
        secret:
          secretName: vsp-tls-certs
---
apiVersion: v1
kind: Service
metadata:
  name: vsp-server-service
spec:
  selector:
    app: vsp-server
  ports:
  - name: tcp
    port: 9000
    targetPort: 9000
  - name: quic
    port: 9001
    targetPort: 9001
    protocol: UDP
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
"""
