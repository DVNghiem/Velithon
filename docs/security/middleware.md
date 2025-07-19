# Security Middleware

This guide covers implementing security middleware in Velithon applications to protect against common vulnerabilities.

## CORS (Cross-Origin Resource Sharing)

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse, Response
import re
from typing import List, Optional, Union

class CORSMiddleware:
    def __init__(
        self,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 600
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        
        # Compile origin patterns
        self.origin_patterns = []
        for origin in self.allow_origins:
            if origin == "*":
                self.origin_patterns.append(re.compile(r".*"))
            else:
                # Escape special regex characters except *
                pattern = re.escape(origin).replace(r"\*", ".*")
                self.origin_patterns.append(re.compile(f"^{pattern}$"))
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return False
        
        for pattern in self.origin_patterns:
            if pattern.match(origin):
                return True
        
        return False
    
    def add_cors_headers(self, response: Response, origin: str = None) -> Response:
        """Add CORS headers to response."""
        if origin and self.is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if self.expose_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        return response
    
    async def __call__(self, request: Request, call_next):
        """CORS middleware handler."""
        origin = request.headers.get("Origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            
            if origin and self.is_origin_allowed(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
                response.headers["Access-Control-Max-Age"] = str(self.max_age)
                
                if self.allow_credentials:
                    response.headers["Access-Control-Allow-Credentials"] = "true"
            
            return response
        
        # Process actual request
        response = await call_next(request)
        return self.add_cors_headers(response, origin)

app = Velithon()

# Add CORS middleware
cors_middleware = CORSMiddleware(
    allow_origins=["http://localhost:3000", "https://example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    allow_credentials=True,
    expose_headers=["X-Total-Count"],
    max_age=3600
)

app.add_middleware(cors_middleware)
```

## Rate Limiting Middleware

```python
import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Tuple
import hashlib

class RateLimitMiddleware:
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        key_func: callable = None
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.key_func = key_func or self._default_key_func
        
        # Store request timestamps
        self.minute_requests: Dict[str, deque] = defaultdict(deque)
        self.hour_requests: Dict[str, deque] = defaultdict(deque)
        self.burst_requests: Dict[str, deque] = defaultdict(deque)
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function using client IP."""
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _clean_old_requests(self, request_queue: deque, window_seconds: int):
        """Remove old requests outside the time window."""
        current_time = time.time()
        while request_queue and current_time - request_queue[0] > window_seconds:
            request_queue.popleft()
    
    def is_rate_limited(self, key: str) -> Tuple[bool, Dict[str, any]]:
        """Check if request should be rate limited."""
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(self.minute_requests[key], 60)
        self._clean_old_requests(self.hour_requests[key], 3600)
        self._clean_old_requests(self.burst_requests[key], 1)  # 1 second burst window
        
        # Check burst limit (1 second window)
        if len(self.burst_requests[key]) >= self.burst_limit:
            return True, {
                "error": "Burst rate limit exceeded",
                "limit": self.burst_limit,
                "window": "1 second",
                "retry_after": 1
            }
        
        # Check minute limit
        if len(self.minute_requests[key]) >= self.requests_per_minute:
            oldest_request = self.minute_requests[key][0]
            retry_after = 60 - (current_time - oldest_request)
            return True, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_minute,
                "window": "1 minute",
                "retry_after": int(retry_after)
            }
        
        # Check hour limit
        if len(self.hour_requests[key]) >= self.requests_per_hour:
            oldest_request = self.hour_requests[key][0]
            retry_after = 3600 - (current_time - oldest_request)
            return True, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_hour,
                "window": "1 hour",
                "retry_after": int(retry_after)
            }
        
        return False, {}
    
    def record_request(self, key: str):
        """Record a request for rate limiting."""
        current_time = time.time()
        self.minute_requests[key].append(current_time)
        self.hour_requests[key].append(current_time)
        self.burst_requests[key].append(current_time)
    
    async def __call__(self, request: Request, call_next):
        """Rate limiting middleware handler."""
        key = self.key_func(request)
        
        is_limited, limit_info = self.is_rate_limited(key)
        
        if is_limited:
            headers = {
                "X-RateLimit-Limit": str(limit_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(limit_info["retry_after"])
            }
            
            return JSONResponse(
                {"error": limit_info["error"], "retry_after": limit_info["retry_after"]},
                status_code=429,
                headers=headers
            )
        
        # Record the request
        self.record_request(key)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        current_minute_count = len(self.minute_requests[key])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.requests_per_minute - current_minute_count))
        
        return response

# Add rate limiting middleware
rate_limit_middleware = RateLimitMiddleware(
    requests_per_minute=100,
    requests_per_hour=2000,
    burst_limit=20
)

app.add_middleware(rate_limit_middleware)
```

## Security Headers Middleware

```python
class SecurityHeadersMiddleware:
    def __init__(
        self,
        force_https: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        content_type_nosniff: bool = True,
        frame_options: str = "DENY",
        xss_protection: bool = True,
        referrer_policy: str = "strict-origin-when-cross-origin",
        content_security_policy: str = None,
        permissions_policy: str = None
    ):
        self.force_https = force_https
        self.hsts_max_age = hsts_max_age
        self.content_type_nosniff = content_type_nosniff
        self.frame_options = frame_options
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
        self.content_security_policy = content_security_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'"
        )
        self.permissions_policy = permissions_policy or (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
    
    async def __call__(self, request: Request, call_next):
        """Security headers middleware handler."""
        # Check if HTTPS is required
        if self.force_https and request.url.scheme != "https":
            # In production, you might want to redirect to HTTPS
            if request.method in ["GET", "HEAD"]:
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(https_url, status_code=301)
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        if self.force_https and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains"
        
        if self.content_type_nosniff:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options
        
        if self.xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        if self.referrer_policy:
            response.headers["Referrer-Policy"] = self.referrer_policy
        
        if self.content_security_policy:
            response.headers["Content-Security-Policy"] = self.content_security_policy
        
        if self.permissions_policy:
            response.headers["Permissions-Policy"] = self.permissions_policy
        
        # Remove server information
        response.headers.pop("Server", None)
        
        return response

# Add security headers middleware
security_headers_middleware = SecurityHeadersMiddleware(
    force_https=True,
    frame_options="DENY",
    content_security_policy=(
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https:"
    )
)

app.add_middleware(security_headers_middleware)
```

## Request Validation Middleware

```python
import json
from typing import Optional, Dict, Any

class RequestValidationMiddleware:
    def __init__(
        self,
        max_content_length: int = 10 * 1024 * 1024,  # 10MB
        allowed_content_types: List[str] = None,
        max_query_params: int = 100,
        max_headers: int = 100,
        validate_json: bool = True
    ):
        self.max_content_length = max_content_length
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain"
        ]
        self.max_query_params = max_query_params
        self.max_headers = max_headers
        self.validate_json = validate_json
    
    def validate_content_length(self, request: Request) -> Optional[Response]:
        """Validate request content length."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_content_length:
                    return JSONResponse(
                        {"error": f"Request too large. Maximum size: {self.max_content_length} bytes"},
                        status_code=413
                    )
            except ValueError:
                return JSONResponse(
                    {"error": "Invalid Content-Length header"},
                    status_code=400
                )
        return None
    
    def validate_content_type(self, request: Request) -> Optional[Response]:
        """Validate request content type."""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in self.allowed_content_types:
                return JSONResponse(
                    {"error": f"Unsupported content type: {content_type}"},
                    status_code=415
                )
        return None
    
    def validate_query_params(self, request: Request) -> Optional[Response]:
        """Validate query parameters."""
        if len(request.query_params) > self.max_query_params:
            return JSONResponse(
                {"error": f"Too many query parameters. Maximum: {self.max_query_params}"},
                status_code=400
            )
        return None
    
    def validate_headers(self, request: Request) -> Optional[Response]:
        """Validate request headers."""
        if len(request.headers) > self.max_headers:
            return JSONResponse(
                {"error": f"Too many headers. Maximum: {self.max_headers}"},
                status_code=400
            )
        return None
    
    async def validate_json_body(self, request: Request) -> Optional[Response]:
        """Validate JSON body if present."""
        if (self.validate_json and 
            request.method in ["POST", "PUT", "PATCH"] and
            request.headers.get("content-type", "").startswith("application/json")):
            
            try:
                body = await request.body()
                if body:
                    json.loads(body.decode())
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {"error": f"Invalid JSON: {str(e)}"},
                    status_code=400
                )
            except UnicodeDecodeError:
                return JSONResponse(
                    {"error": "Invalid UTF-8 encoding in request body"},
                    status_code=400
                )
        
        return None
    
    async def __call__(self, request: Request, call_next):
        """Request validation middleware handler."""
        # Validate content length
        validation_error = self.validate_content_length(request)
        if validation_error:
            return validation_error
        
        # Validate content type
        validation_error = self.validate_content_type(request)
        if validation_error:
            return validation_error
        
        # Validate query parameters
        validation_error = self.validate_query_params(request)
        if validation_error:
            return validation_error
        
        # Validate headers
        validation_error = self.validate_headers(request)
        if validation_error:
            return validation_error
        
        # Validate JSON body
        validation_error = await self.validate_json_body(request)
        if validation_error:
            return validation_error
        
        # Process request
        return await call_next(request)

# Add request validation middleware
validation_middleware = RequestValidationMiddleware(
    max_content_length=5 * 1024 * 1024,  # 5MB
    max_query_params=50,
    max_headers=50
)

app.add_middleware(validation_middleware)
```

## CSRF Protection Middleware

```python
import secrets
import hmac
import hashlib
from typing import Set

class CSRFMiddleware:
    def __init__(
        self,
        secret_key: str,
        safe_methods: Set[str] = None,
        csrf_header_name: str = "X-CSRFToken",
        csrf_cookie_name: str = "csrftoken",
        csrf_field_name: str = "csrf_token"
    ):
        self.secret_key = secret_key.encode()
        self.safe_methods = safe_methods or {"GET", "HEAD", "OPTIONS", "TRACE"}
        self.csrf_header_name = csrf_header_name
        self.csrf_cookie_name = csrf_cookie_name
        self.csrf_field_name = csrf_field_name
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token."""
        # Generate random salt
        salt = secrets.token_bytes(16)
        
        # Create HMAC with secret key
        hmac_obj = hmac.new(self.secret_key, salt, hashlib.sha256)
        token = salt + hmac_obj.digest()
        
        # Return base64 encoded token
        import base64
        return base64.b64encode(token).decode()
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token."""
        try:
            import base64
            token_bytes = base64.b64decode(token.encode())
            
            if len(token_bytes) < 48:  # 16 (salt) + 32 (hmac) = 48
                return False
            
            salt = token_bytes[:16]
            provided_hmac = token_bytes[16:]
            
            # Calculate expected HMAC
            expected_hmac = hmac.new(self.secret_key, salt, hashlib.sha256).digest()
            
            # Compare HMACs securely
            return hmac.compare_digest(expected_hmac, provided_hmac)
            
        except Exception:
            return False
    
    async def get_csrf_token_from_request(self, request: Request) -> Optional[str]:
        """Extract CSRF token from request."""
        # Check header first
        token = request.headers.get(self.csrf_header_name)
        if token:
            return token
        
        # Check form data for POST requests
        if request.method == "POST":
            try:
                form = await request.form()
                return form.get(self.csrf_field_name)
            except:
                pass
        
        return None
    
    async def __call__(self, request: Request, call_next):
        """CSRF protection middleware handler."""
        # Skip CSRF check for safe methods
        if request.method in self.safe_methods:
            response = await call_next(request)
            
            # Add CSRF token to response for safe methods
            if request.method == "GET":
                csrf_token = self.generate_csrf_token()
                response.set_cookie(
                    self.csrf_cookie_name,
                    csrf_token,
                    httponly=False,  # JavaScript needs access
                    samesite="strict",
                    secure=request.url.scheme == "https"
                )
            
            return response
        
        # Validate CSRF token for unsafe methods
        csrf_token = await self.get_csrf_token_from_request(request)
        
        if not csrf_token or not self.validate_csrf_token(csrf_token):
            return JSONResponse(
                {"error": "CSRF token missing or invalid"},
                status_code=403
            )
        
        return await call_next(request)

# Add CSRF protection middleware
csrf_middleware = CSRFMiddleware(
    secret_key="your-secret-key-here",
    csrf_header_name="X-CSRFToken"
)

app.add_middleware(csrf_middleware)
```

## IP Whitelist/Blacklist Middleware

```python
import ipaddress
from typing import List, Union

class IPFilterMiddleware:
    def __init__(
        self,
        whitelist: List[Union[str, ipaddress.IPv4Network, ipaddress.IPv6Network]] = None,
        blacklist: List[Union[str, ipaddress.IPv4Network, ipaddress.IPv6Network]] = None,
        block_private_ips: bool = False
    ):
        self.whitelist = self._parse_ip_list(whitelist) if whitelist else None
        self.blacklist = self._parse_ip_list(blacklist) if blacklist else []
        self.block_private_ips = block_private_ips
    
    def _parse_ip_list(self, ip_list: List[Union[str, ipaddress.IPv4Network, ipaddress.IPv6Network]]):
        """Parse IP list into network objects."""
        parsed_list = []
        
        for ip in ip_list:
            if isinstance(ip, str):
                try:
                    # Try to parse as network first, then as single IP
                    if "/" in ip:
                        parsed_list.append(ipaddress.ip_network(ip, strict=False))
                    else:
                        parsed_list.append(ipaddress.ip_network(f"{ip}/32" if ":" not in ip else f"{ip}/128", strict=False))
                except ValueError:
                    # Invalid IP format, skip
                    continue
            else:
                parsed_list.append(ip)
        
        return parsed_list
    
    def is_ip_allowed(self, ip_str: str) -> bool:
        """Check if IP is allowed."""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        
        # Check if IP is private and private IPs are blocked
        if self.block_private_ips and ip.is_private:
            return False
        
        # Check blacklist first
        for blocked_network in self.blacklist:
            if ip in blocked_network:
                return False
        
        # Check whitelist if defined
        if self.whitelist:
            for allowed_network in self.whitelist:
                if ip in allowed_network:
                    return True
            return False  # IP not in whitelist
        
        return True  # No whitelist defined, allow by default
    
    async def __call__(self, request: Request, call_next):
        """IP filtering middleware handler."""
        client_ip = request.client.host if request.client else "unknown"
        
        if not self.is_ip_allowed(client_ip):
            return JSONResponse(
                {"error": "Access denied from this IP address"},
                status_code=403
            )
        
        return await call_next(request)

# Add IP filtering middleware
ip_filter_middleware = IPFilterMiddleware(
    # whitelist=["192.168.1.0/24", "10.0.0.0/8"],  # Allow only these networks
    blacklist=["192.168.100.0/24", "10.0.50.0/24"],  # Block these networks
    block_private_ips=False
)

app.add_middleware(ip_filter_middleware)
```

## Testing Security Middleware

```python
import pytest
import httpx
from unittest.mock import patch

@pytest.mark.asyncio
async def test_cors_middleware():
    """Test CORS middleware functionality."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test preflight request
        response = await client.options(
            "/api/test",
            headers={"Origin": "https://example.com"}
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting middleware."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Make requests up to the limit
        for i in range(10):  # Assuming burst limit is 10
            response = await client.get("/api/test")
            if i < 9:
                assert response.status_code != 429
            else:
                # Last request should be rate limited
                assert response.status_code == 429

@pytest.mark.asyncio
async def test_security_headers():
    """Test security headers middleware."""
    async with httpx.AsyncClient(app=app, base_url="https://test") as client:
        response = await client.get("/api/test")
        
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

@pytest.mark.asyncio
async def test_request_validation():
    """Test request validation middleware."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test invalid JSON
        response = await client.post(
            "/api/test",
            content='{"invalid": json}',
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]

@pytest.mark.asyncio
async def test_csrf_protection():
    """Test CSRF protection middleware."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # GET request should work and provide CSRF token
        response = await client.get("/api/test")
        assert response.status_code == 200
        assert "csrftoken" in response.cookies
        
        # POST without CSRF token should fail
        response = await client.post("/api/test", json={"test": "data"})
        assert response.status_code == 403
        assert "CSRF token" in response.json()["error"]

@pytest.mark.asyncio
async def test_ip_filtering():
    """Test IP filtering middleware."""
    with patch('velithon.Request.client') as mock_client:
        mock_client.host = "192.168.100.50"  # Blocked IP
        
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/test")
            assert response.status_code == 403
            assert "Access denied" in response.json()["error"]

def test_cors_origin_validation():
    """Test CORS origin validation."""
    cors = CORSMiddleware(allow_origins=["https://example.com", "*.mydomain.com"])
    
    assert cors.is_origin_allowed("https://example.com")
    assert cors.is_origin_allowed("https://sub.mydomain.com")
    assert not cors.is_origin_allowed("https://evil.com")

def test_rate_limit_key_function():
    """Test rate limit key function."""
    rate_limiter = RateLimitMiddleware()
    
    # Mock request
    class MockRequest:
        def __init__(self, ip):
            self.client = type('obj', (object,), {'host': ip})
    
    request = MockRequest("192.168.1.1")
    key = rate_limiter.key_func(request)
    assert key == "ip:192.168.1.1"

def test_csrf_token_generation_and_validation():
    """Test CSRF token generation and validation."""
    csrf = CSRFMiddleware("test-secret-key")
    
    # Generate token
    token = csrf.generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Validate token
    assert csrf.validate_csrf_token(token)
    assert not csrf.validate_csrf_token("invalid-token")
    assert not csrf.validate_csrf_token("")

def test_ip_network_parsing():
    """Test IP network parsing."""
    ip_filter = IPFilterMiddleware(
        whitelist=["192.168.1.0/24", "10.0.0.1"],
        blacklist=["192.168.1.100/32"]
    )
    
    assert ip_filter.is_ip_allowed("192.168.1.50")  # In whitelist
    assert not ip_filter.is_ip_allowed("192.168.1.100")  # In blacklist
    assert not ip_filter.is_ip_allowed("10.0.0.2")  # Not in whitelist
```

## Complete Security Stack Example

```python
app = Velithon()

# Apply security middleware in order
app.add_middleware(
    IPFilterMiddleware(
        blacklist=["192.168.100.0/24"],
        block_private_ips=False
    )
)

app.add_middleware(
    RateLimitMiddleware(
        requests_per_minute=100,
        requests_per_hour=2000,
        burst_limit=20
    )
)

app.add_middleware(
    RequestValidationMiddleware(
        max_content_length=10 * 1024 * 1024,
        max_query_params=100
    )
)

app.add_middleware(
    CSRFMiddleware(
        secret_key="your-csrf-secret-key",
        csrf_header_name="X-CSRFToken"
    )
)

app.add_middleware(
    SecurityHeadersMiddleware(
        force_https=True,
        content_security_policy=(
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:"
        )
    )
)

app.add_middleware(
    CORSMiddleware(
        allow_origins=["https://yourfrontend.com"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-CSRFToken"],
        allow_credentials=True
    )
)

@app.get("/api/secure")
async def secure_endpoint(request: Request):
    """Secure endpoint protected by all middleware."""
    return JSONResponse({
        "message": "This endpoint is protected by multiple security layers",
        "client_ip": request.client.host if request.client else "unknown",
        "headers": dict(request.headers)
    })

if __name__ == "__main__":
    # Run with: velithon run --app middleware_example:app --host 0.0.0.0 --port 8000
    print("Run with: velithon run --app middleware_example:app --host 0.0.0.0 --port 8000")
```

## Best Practices

1. **Layered Security**: Use multiple middleware layers for defense in depth
2. **Order Matters**: Apply middleware in the correct order (IP filtering first, etc.)
3. **Configuration**: Make middleware configurable for different environments
4. **Performance**: Consider performance impact of security checks
5. **Logging**: Log security events and violations
6. **Testing**: Thoroughly test security middleware
7. **Updates**: Keep security policies and configurations up to date
8. **Monitoring**: Monitor for security violations and attacks
9. **Documentation**: Document security policies and configurations
10. **Regular Audits**: Regularly audit and review security middleware effectiveness
