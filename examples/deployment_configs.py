# Example deployment files for Velithon applications

"""Health check endpoints for production deployment."""
import time
from velithon import Velithon
from velithon.responses import JSONResponse


def setup_health_routes(app: Velithon):
    """Set up health check routes."""
    
    @app.get("/health")
    async def health_check():
        """Provide basic health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0"
        })
    
    @app.get("/ready")
    async def readiness_check():
        """Check readiness with dependencies."""
        checks = {}
        overall_status = "ready"
        
        try:
            # Check database connection
            if hasattr(app.state, 'db'):
                await app.state.db.health_check()
                checks["database"] = "healthy"
            
            # Check Redis connection
            if hasattr(app.state, 'cache'):
                await app.state.cache.health_check()
                checks["cache"] = "healthy"
                
        except Exception as e:
            overall_status = "not ready"
            checks["error"] = str(e)
        
        status_code = 200 if overall_status == "ready" else 503
        
        return JSONResponse({
            "status": overall_status,
            "checks": checks,
            "timestamp": time.time()
        }, status_code=status_code)
    
    @app.get("/metrics")
    async def metrics_endpoint():
        """Provide Prometheus metrics endpoint."""
        try:
            from prometheus_client import generate_latest  # noqa: F401
            return generate_latest()
        except ImportError:
            return JSONResponse({"error": "Metrics not available"}, status_code=404)


# Example systemd service file content
SYSTEMD_SERVICE = """
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
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/velithon/app/logs /home/velithon/app/uploads

[Install]
WantedBy=multi-user.target
"""

# Example nginx configuration
NGINX_CONFIG = """
upstream velithon_backend {
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    
    # Health check (requires nginx-plus or third-party module)
    # health_check;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

# Caching
proxy_cache_path /var/cache/nginx/velithon levels=1:2 keys_zone=velithon_cache:10m max_size=100m inactive=60m use_temp_path=off;

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Main application
    location / {
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://velithon_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # Caching for static content
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|eot|svg)$ {
            proxy_cache velithon_cache;
            proxy_cache_valid 200 1h;
            proxy_cache_valid 404 1m;
            add_header X-Cache-Status $upstream_cache_status;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API rate limiting
    location /api/auth/login {
        limit_req zone=login burst=5 nodelay;
        
        proxy_pass http://velithon_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health checks (allow without rate limiting)
    location ~ ^/(health|ready|metrics)$ {
        access_log off;
        proxy_pass http://velithon_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static files (if served by nginx)
    location /static/ {
        alias /home/velithon/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Security
        location ~* \.(php|jsp|cgi|pl|py)$ {
            deny all;
        }
    }
    
    # Uploads (if served by nginx)
    location /uploads/ {
        alias /home/velithon/app/uploads/;
        expires 1d;
        add_header Cache-Control "public";
        
        # Security
        location ~* \.(php|jsp|cgi|pl|py|exe|sh)$ {
            deny all;
        }
    }
    
    # Deny access to sensitive files
    location ~ /\.(env|git|svn|htaccess|htpasswd) {
        deny all;
    }
    
    # Deny access to backup files
    location ~ \.(bak|backup|old|orig|save|tmp)$ {
        deny all;
    }
}
"""

# Example Docker Compose for production
DOCKER_COMPOSE = """
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://velithon:${DB_PASSWORD}@db:5432/velithon_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    restart: unless-stopped
    networks:
      - velithon-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: velithon_db
      POSTGRES_USER: velithon
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    restart: unless-stopped
    networks:
      - velithon-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U velithon -d velithon_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - velithon-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - velithon-network

  # Monitoring (optional)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks:
      - velithon-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    restart: unless-stopped
    networks:
      - velithon-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  velithon-network:
    driver: bridge
"""

if __name__ == "__main__":
    print("This file contains deployment configuration examples for Velithon applications.")
    print("Copy the relevant sections to your deployment configuration files.")
