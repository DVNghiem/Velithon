# API Keys

This guide covers implementing API key authentication and management in Velithon applications.

## Basic API Key Authentication

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from velithon.di import inject, Provide, ServiceContainer
import secrets
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List
from functools import wraps

@dataclass
class APIKey:
    id: str
    name: str
    key_hash: str
    user_id: str
    scopes: List[str]
    is_active: bool = True
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

class APIKeyService:
    def __init__(self):
        # Mock storage - replace with database
        self.api_keys: Dict[str, APIKey] = {}
        self.key_prefix = "velithon_"
    
    def generate_api_key(self) -> str:
        """Generate a new API key."""
        return self.key_prefix + secrets.token_urlsafe(32)
    
    def hash_key(self, key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def create_api_key(
        self, 
        user_id: str, 
        name: str, 
        scopes: List[str] = None,
        expires_in_days: int = None
    ) -> tuple[str, APIKey]:
        """Create a new API key."""
        key = self.generate_api_key()
        key_hash = self.hash_key(key)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            id=secrets.token_urlsafe(16),
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            scopes=scopes or [],
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        
        self.api_keys[api_key.id] = api_key
        return key, api_key
    
    def verify_api_key(self, key: str) -> Optional[APIKey]:
        """Verify API key and return associated data."""
        if not key.startswith(self.key_prefix):
            return None
        
        key_hash = self.hash_key(key)
        
        for api_key in self.api_keys.values():
            if (api_key.key_hash == key_hash and 
                api_key.is_active and
                (not api_key.expires_at or api_key.expires_at > datetime.utcnow())):
                
                # Update usage statistics
                api_key.last_used_at = datetime.utcnow()
                api_key.usage_count += 1
                
                return api_key
        
        return None
    
    def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        return [
            api_key for api_key in self.api_keys.values()
            if api_key.user_id == user_id
        ]
    
    def revoke_api_key(self, key_id: str, user_id: str = None) -> bool:
        """Revoke an API key."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False
        
        if user_id and api_key.user_id != user_id:
            return False
        
        api_key.is_active = False
        return True
    
    def has_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if API key has required scope."""
        return required_scope in api_key.scopes or "admin" in api_key.scopes

def require_api_key(scopes: List[str] = None):
    """Decorator to require API key authentication."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Check for API key in header
            api_key = request.headers.get("X-API-Key")
            
            # Also check query parameter as fallback
            if not api_key:
                api_key = request.query_params.get("api_key")
            
            if not api_key:
                return JSONResponse(
                    {"error": "API key required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "ApiKey"}
                )
            
            api_key_service = ServiceContainer.get(APIKeyService)
            key_data = api_key_service.verify_api_key(api_key)
            
            if not key_data:
                return JSONResponse(
                    {"error": "Invalid or expired API key"},
                    status_code=401
                )
            
            # Check scopes if required
            if scopes:
                for scope in scopes:
                    if not api_key_service.has_scope(key_data, scope):
                        return JSONResponse(
                            {"error": f"Scope '{scope}' required"},
                            status_code=403
                        )
            
            # Add API key data to request state
            request.state.api_key = key_data
            request.state.user_id = key_data.user_id
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

app = Velithon()

# Register services
ServiceContainer.register(APIKeyService, APIKeyService())

@app.post("/api-keys")
async def create_api_key(request: Request):
    """Create a new API key."""
    data = await request.json()
    
    # In production, you'd get user_id from JWT token or session
    user_id = data.get("user_id", "user1")  # Mock user ID
    name = data.get("name")
    scopes = data.get("scopes", [])
    expires_in_days = data.get("expires_in_days")
    
    if not name:
        return JSONResponse(
            {"error": "API key name is required"},
            status_code=400
        )
    
    api_key_service = ServiceContainer.get(APIKeyService)
    key, api_key_data = api_key_service.create_api_key(
        user_id=user_id,
        name=name,
        scopes=scopes,
        expires_in_days=expires_in_days
    )
    
    return JSONResponse({
        "api_key": key,  # Return once, then never show again
        "id": api_key_data.id,
        "name": api_key_data.name,
        "scopes": api_key_data.scopes,
        "expires_at": api_key_data.expires_at.isoformat() if api_key_data.expires_at else None,
        "created_at": api_key_data.created_at.isoformat(),
        "message": "Store this API key securely. It will not be shown again."
    })

@app.get("/api-keys")
async def list_api_keys(request: Request):
    """List user's API keys (without showing the actual keys)."""
    # In production, get user_id from authentication
    user_id = request.query_params.get("user_id", "user1")
    
    api_key_service = ServiceContainer.get(APIKeyService)
    api_keys = api_key_service.get_user_api_keys(user_id)
    
    return JSONResponse({
        "api_keys": [
            {
                "id": key.id,
                "name": key.name,
                "scopes": key.scopes,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "usage_count": key.usage_count
            }
            for key in api_keys
        ]
    })

@app.delete("/api-keys/{key_id}")
async def revoke_api_key(request: Request):
    """Revoke an API key."""
    key_id = request.path_params["key_id"]
    # In production, get user_id from authentication
    user_id = request.query_params.get("user_id", "user1")
    
    api_key_service = ServiceContainer.get(APIKeyService)
    success = api_key_service.revoke_api_key(key_id, user_id)
    
    if not success:
        return JSONResponse(
            {"error": "API key not found or access denied"},
            status_code=404
        )
    
    return JSONResponse({
        "message": "API key revoked successfully"
    })

# Protected endpoints using API key authentication

@app.get("/api/public")
async def public_endpoint(request: Request):
    """Public endpoint - no authentication required."""
    return JSONResponse({
        "message": "This is a public endpoint",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.get("/api/protected")
@require_api_key()
async def protected_endpoint(request: Request):
    """Protected endpoint requiring any valid API key."""
    api_key = request.state.api_key
    return JSONResponse({
        "message": "Access granted",
        "api_key_name": api_key.name,
        "scopes": api_key.scopes,
        "user_id": api_key.user_id
    })

@app.get("/api/read-data")
@require_api_key(scopes=["read"])
async def read_data(request: Request):
    """Endpoint requiring 'read' scope."""
    return JSONResponse({
        "data": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ]
    })

@app.post("/api/write-data")
@require_api_key(scopes=["write"])
async def write_data(request: Request):
    """Endpoint requiring 'write' scope."""
    data = await request.json()
    return JSONResponse({
        "message": "Data written successfully",
        "data": data,
        "written_by": request.state.user_id
    })

@app.delete("/api/delete-data/{item_id}")
@require_api_key(scopes=["delete"])
async def delete_data(request: Request):
    """Endpoint requiring 'delete' scope."""
    item_id = request.path_params["item_id"]
    return JSONResponse({
        "message": f"Item {item_id} deleted successfully",
        "deleted_by": request.state.user_id
    })

@app.get("/api/admin")
@require_api_key(scopes=["admin"])
async def admin_endpoint(request: Request):
    """Admin-only endpoint."""
    return JSONResponse({
        "message": "Admin access granted",
        "system_info": {
            "version": "1.0.0",
            "uptime": "24 hours",
            "active_keys": len(ServiceContainer.get(APIKeyService).api_keys)
        }
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Advanced API Key Features

### Rate Limiting with API Keys

```python
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)  # api_key_id -> list of request timestamps
        self.limits = {
            "default": {"requests": 100, "window": 3600},  # 100 requests per hour
            "premium": {"requests": 1000, "window": 3600},  # 1000 requests per hour
            "admin": {"requests": 10000, "window": 3600}    # 10000 requests per hour
        }
    
    def is_allowed(self, api_key: APIKey) -> tuple[bool, dict]:
        """Check if request is allowed within rate limits."""
        now = datetime.utcnow()
        key_id = api_key.id
        
        # Determine rate limit tier
        tier = "admin" if "admin" in api_key.scopes else "default"
        if "premium" in api_key.scopes:
            tier = "premium"
        
        limit_config = self.limits[tier]
        window_start = now - timedelta(seconds=limit_config["window"])
        
        # Clean old requests
        self.requests[key_id] = [
            req_time for req_time in self.requests[key_id]
            if req_time > window_start
        ]
        
        # Check if under limit
        current_requests = len(self.requests[key_id])
        if current_requests >= limit_config["requests"]:
            return False, {
                "error": "Rate limit exceeded",
                "limit": limit_config["requests"],
                "window": limit_config["window"],
                "current": current_requests,
                "reset_at": (window_start + timedelta(seconds=limit_config["window"])).isoformat()
            }
        
        # Add current request
        self.requests[key_id].append(now)
        
        return True, {
            "limit": limit_config["requests"],
            "remaining": limit_config["requests"] - current_requests - 1,
            "reset_at": (window_start + timedelta(seconds=limit_config["window"])).isoformat()
        }

def rate_limit(func):
    """Decorator to apply rate limiting."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if hasattr(request.state, "api_key"):
            rate_limiter = ServiceContainer.get(RateLimiter)
            allowed, info = rate_limiter.is_allowed(request.state.api_key)
            
            if not allowed:
                return JSONResponse(
                    info,
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(info.get("limit", 0)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": info.get("reset_at", "")
                    }
                )
            
            # Add rate limit headers
            response = await func(request, *args, **kwargs)
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = info["reset_at"]
            
            return response
        
        return await func(request, *args, **kwargs)
    return wrapper

# Register rate limiter
ServiceContainer.register(RateLimiter, RateLimiter())

@app.get("/api/rate-limited")
@require_api_key()
@rate_limit
async def rate_limited_endpoint(request: Request):
    """Endpoint with rate limiting."""
    return JSONResponse({
        "message": "Request successful",
        "timestamp": datetime.utcnow().isoformat()
    })
```

### API Key Analytics

```python
from dataclasses import dataclass, field
from typing import Dict, List
from collections import defaultdict
import json

@dataclass
class APIKeyUsage:
    key_id: str
    endpoint: str
    method: str
    timestamp: datetime
    status_code: int
    response_time: float
    user_agent: str = None
    ip_address: str = None

class AnalyticsService:
    def __init__(self):
        self.usage_logs: List[APIKeyUsage] = []
        self.daily_stats = defaultdict(lambda: defaultdict(int))
    
    def log_request(
        self, 
        api_key: APIKey, 
        request: Request, 
        status_code: int, 
        response_time: float
    ):
        """Log API key usage."""
        usage = APIKeyUsage(
            key_id=api_key.id,
            endpoint=request.url.path,
            method=request.method,
            timestamp=datetime.utcnow(),
            status_code=status_code,
            response_time=response_time,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None
        )
        
        self.usage_logs.append(usage)
        
        # Update daily stats
        date_key = usage.timestamp.date().isoformat()
        self.daily_stats[api_key.id][date_key] += 1
    
    def get_key_analytics(self, key_id: str, days: int = 30) -> Dict:
        """Get analytics for specific API key."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Filter logs for this key and date range
        relevant_logs = [
            log for log in self.usage_logs
            if (log.key_id == key_id and 
                start_date <= log.timestamp.date() <= end_date)
        ]
        
        # Calculate statistics
        total_requests = len(relevant_logs)
        unique_endpoints = len(set(log.endpoint for log in relevant_logs))
        
        status_codes = defaultdict(int)
        methods = defaultdict(int)
        endpoints = defaultdict(int)
        
        for log in relevant_logs:
            status_codes[log.status_code] += 1
            methods[log.method] += 1
            endpoints[log.endpoint] += 1
        
        # Daily usage
        daily_usage = {}
        for i in range(days):
            date = (end_date - timedelta(days=i)).isoformat()
            daily_usage[date] = self.daily_stats[key_id].get(date, 0)
        
        return {
            "key_id": key_id,
            "period_days": days,
            "total_requests": total_requests,
            "unique_endpoints": unique_endpoints,
            "status_codes": dict(status_codes),
            "methods": dict(methods),
            "top_endpoints": dict(sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:10]),
            "daily_usage": daily_usage,
            "avg_response_time": sum(log.response_time for log in relevant_logs) / max(total_requests, 1)
        }

def track_usage(func):
    """Decorator to track API key usage."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        start_time = datetime.utcnow()
        
        response = await func(request, *args, **kwargs)
        
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        # Log usage if API key is present
        if hasattr(request.state, "api_key"):
            analytics_service = ServiceContainer.get(AnalyticsService)
            analytics_service.log_request(
                api_key=request.state.api_key,
                request=request,
                status_code=response.status_code,
                response_time=response_time
            )
        
        return response
    return wrapper

# Register analytics service
ServiceContainer.register(AnalyticsService, AnalyticsService())

@app.get("/api-keys/{key_id}/analytics")
async def get_api_key_analytics(request: Request):
    """Get analytics for a specific API key."""
    key_id = request.path_params["key_id"]
    days = int(request.query_params.get("days", 30))
    
    # In production, verify user owns this API key
    analytics_service = ServiceContainer.get(AnalyticsService)
    analytics = analytics_service.get_key_analytics(key_id, days)
    
    return JSONResponse(analytics)

# Apply tracking to protected endpoints
@app.get("/api/tracked")
@require_api_key()
@track_usage
async def tracked_endpoint(request: Request):
    """Endpoint with usage tracking."""
    # Simulate some processing time
    await asyncio.sleep(0.1)
    
    return JSONResponse({
        "message": "This request is being tracked",
        "timestamp": datetime.utcnow().isoformat()
    })
```

## Testing API Key Authentication

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_create_api_key():
    """Test API key creation."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api-keys", json={
            "user_id": "test_user",
            "name": "Test API Key",
            "scopes": ["read", "write"],
            "expires_in_days": 30
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "api_key" in data
        assert data["api_key"].startswith("velithon_")
        assert data["name"] == "Test API Key"
        assert data["scopes"] == ["read", "write"]

@pytest.mark.asyncio
async def test_api_key_authentication():
    """Test API key authentication."""
    # First create an API key
    api_key_service = APIKeyService()
    key, key_data = api_key_service.create_api_key(
        user_id="test_user",
        name="Test Key",
        scopes=["read"]
    )
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test with valid API key
        response = await client.get(
            "/api/protected",
            headers={"X-API-Key": key}
        )
        assert response.status_code == 200
        
        # Test with invalid API key
        response = await client.get(
            "/api/protected",
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_api_key_scopes():
    """Test API key scope enforcement."""
    api_key_service = APIKeyService()
    
    # Create key with only read scope
    read_key, _ = api_key_service.create_api_key(
        user_id="test_user",
        name="Read Key",
        scopes=["read"]
    )
    
    # Create key with write scope
    write_key, _ = api_key_service.create_api_key(
        user_id="test_user",
        name="Write Key",
        scopes=["write"]
    )
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Read key can access read endpoint
        response = await client.get(
            "/api/read-data",
            headers={"X-API-Key": read_key}
        )
        assert response.status_code == 200
        
        # Read key cannot access write endpoint
        response = await client.post(
            "/api/write-data",
            json={"test": "data"},
            headers={"X-API-Key": read_key}
        )
        assert response.status_code == 403
        
        # Write key can access write endpoint
        response = await client.post(
            "/api/write-data",
            json={"test": "data"},
            headers={"X-API-Key": write_key}
        )
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_api_key_revocation():
    """Test API key revocation."""
    api_key_service = APIKeyService()
    key, key_data = api_key_service.create_api_key(
        user_id="test_user",
        name="Test Key",
        scopes=["read"]
    )
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Key works initially
        response = await client.get(
            "/api/protected",
            headers={"X-API-Key": key}
        )
        assert response.status_code == 200
        
        # Revoke the key
        revoke_response = await client.delete(
            f"/api-keys/{key_data.id}?user_id=test_user"
        )
        assert revoke_response.status_code == 200
        
        # Key no longer works
        response = await client.get(
            "/api/protected",
            headers={"X-API-Key": key}
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality."""
    api_key_service = APIKeyService()
    key, _ = api_key_service.create_api_key(
        user_id="test_user",
        name="Test Key",
        scopes=["read"]
    )
    
    # Mock a lower rate limit for testing
    rate_limiter = ServiceContainer.get(RateLimiter)
    rate_limiter.limits["default"] = {"requests": 2, "window": 60}
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # First two requests should succeed
        for i in range(2):
            response = await client.get(
                "/api/rate-limited",
                headers={"X-API-Key": key}
            )
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
        
        # Third request should be rate limited
        response = await client.get(
            "/api/rate-limited",
            headers={"X-API-Key": key}
        )
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
```

## Best Practices

1. **Secure Storage**: Never store API keys in plain text
2. **Key Rotation**: Implement regular key rotation policies
3. **Scope Limitation**: Use minimal required scopes
4. **Rate Limiting**: Implement appropriate rate limits
5. **Monitoring**: Track API key usage and anomalies
6. **Expiration**: Set reasonable expiration times
7. **Revocation**: Provide easy key revocation mechanisms
8. **Audit Logging**: Log all API key operations
9. **HTTPS Only**: Always use HTTPS for API key transmission
10. **Documentation**: Provide clear API key usage documentation
