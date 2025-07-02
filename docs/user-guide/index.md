# User Guide Overview

Welcome to the comprehensive Velithon user guide. This section covers all aspects of building production-ready applications with Velithon's powerful RSGI framework.

## 📚 What You'll Learn

Velithon is far more than a simple web framework. It's a comprehensive platform for building high-performance, scalable applications with advanced features:

<div class="grid cards" markdown>

-   **🏗️ Core Concepts**

    ---

    **Application Architecture** - RSGI protocol, dependency injection, lifecycle management
    
    **Routing System** - Advanced routing with path parameters, route groups, middleware
    
    **Request/Response** - Comprehensive handling of HTTP requests and optimized responses

-   **🌐 HTTP Features**

    ---

    **Endpoints** - REST APIs, GraphQL support, OpenAPI documentation
    
    **Request Handling** - Body parsing, validation, file uploads, form data
    
    **Response Types** - JSON optimization, streaming, SSE, proxy responses
    
    **Middleware** - Authentication, CORS, compression, logging, sessions

-   **🚀 Advanced Features**

    ---

    **WebSocket System** - Channels, rooms, heartbeat monitoring, user roles
    
    **Server-Sent Events** - Real-time streaming with structured events
    
    **Background Tasks** - Async task processing with concurrency control
    
    **Template Engine** - Jinja2 integration with optimized rendering
    
    **File Upload Handling** - Secure file processing with validation
    
    **Error Handling** - Comprehensive error management and custom handlers
    
    **Best Practices** - Production-ready patterns and optimizations
    
    **Proxy & Gateway** - High-performance reverse proxy with load balancing

-   **🔐 Security & Auth**

    ---

    **Authentication** - JWT, OAuth2, API Keys, Basic Auth, session management
    
    **Authorization** - Role-based permissions, dependency injection security
    
    **Security Best Practices** - HTTPS, CSRF protection, rate limiting

-   **⚡ Performance**

    ---

    **JSON Optimization** - Ultra-fast orjson serialization, batch processing
    
    **Memory Management** - Efficient resource usage, connection pooling
    
    **Caching** - Built-in caching strategies, Redis integration
    
    **Monitoring** - Performance metrics, health checks, observability

-   **🏢 Enterprise Features**

    ---

    **VSP (Velithon Service Protocol)** - Service mesh, discovery, load balancing
    
    **Microservices** - Service communication, circuit breakers, distributed tracing
    
    **Deployment** - Docker, Kubernetes, cloud-native architectures

</div>

## 🎯 Framework Architecture

Velithon is built on several key architectural principles:

### RSGI Protocol Foundation

Unlike traditional ASGI frameworks, Velithon uses **RSGI (Rust Server Gateway Interface)** through Granian:

- **10x Performance**: Achieves 110,000+ requests/second
- **Memory Efficiency**: Minimal memory footprint with Rust optimizations
- **HTTP/2 Native**: Full HTTP/2 support with push capabilities
- **WebSocket Excellence**: Native WebSocket handling without overhead

### Advanced Dependency Injection

Velithon provides enterprise-grade dependency injection:

```python
from velithon.di import ServiceContainer, inject, Provide

# Register services
container = ServiceContainer()
container.register(DatabaseService, singleton=True)
container.register(CacheService, factory=create_cache)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: DatabaseService = Provide(DatabaseService),
    cache: CacheService = Provide(CacheService)
):
    # Services are automatically injected
    return await db.get_user(user_id)
```

### VSP Service Protocol

Velithon includes **VSP (Velithon Service Protocol)** for microservices:

```python
from velithon.vsp import VSPManager, ServiceMesh

# Service discovery and load balancing
vsp = VSPManager()
mesh = ServiceMesh()

# Register service
await vsp.register_service("user-service", "localhost:8001")

# Call remote service
response = await mesh.call("user-service", "/api/users", method="GET")
```

## 🔥 Key Features Deep Dive

### 1. WebSocket System

Advanced WebSocket capabilities with rooms, channels, and user management:

```python
from velithon.websocket import WebSocketEndpoint, Room, Channel

class ChatEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket):
        await self.join_room("general")
        await self.send_to_room("general", {"type": "user_joined"})
    
    async def on_message(self, websocket, data):
        await self.broadcast_to_room("general", data)
```

### 2. Security Framework

Comprehensive authentication and authorization:

```python
from velithon.security import (
    JWTHandler, OAuth2PasswordBearer, require_permission,
    HTTPBearer, APIKeyHeader
)

# Multiple auth schemes
jwt_auth = JWTHandler(secret_key="secret", algorithm="HS256")
oauth2_scheme = OAuth2PasswordBearer(token_url="token")
api_key_scheme = APIKeyHeader(name="X-API-Key")

@app.get("/admin/users")
@require_permission("admin:read")
async def get_all_users():
    return await db.get_all_users()
```

### 3. Performance Optimization

Built-in performance optimizations:

```python
from velithon.responses import OptimizedJSONResponse, BatchJSONResponse

# Ultra-fast JSON serialization
@app.get("/data")
async def get_data():
    return OptimizedJSONResponse(large_dataset)

# Batch processing
@app.get("/batch")
async def get_batch_data():
    return BatchJSONResponse([item1, item2, item3])
```

### 4. Middleware Ecosystem

Rich middleware ecosystem:

```python
from velithon.middleware import (
    AuthenticationMiddleware, CORSMiddleware, 
    CompressionMiddleware, SessionMiddleware,
    ProxyMiddleware, LoggingMiddleware
)

app = Velithon(
    middleware=[
        LoggingMiddleware(level="INFO"),
        CORSMiddleware(allow_origins=["*"]),
        CompressionMiddleware(minimum_size=1000),
        SessionMiddleware(secret_key="secret"),
        AuthenticationMiddleware(scheme=jwt_auth),
        ProxyMiddleware(upstream="https://api.example.com")
    ]
)
```

## 🗺️ Learning Path

### Beginner Track (Days 1-3)
1. **[Application Basics](core-concepts/application.md)** - Create your first app
2. **[Routing](core-concepts/routing.md)** - Define endpoints and parameters
3. **[Requests & Responses](core-concepts/requests-responses.md)** - Handle HTTP communication

### Intermediate Track (Days 4-7)
4. **[Dependency Injection](core-concepts/dependency-injection.md)** - Manage services and dependencies
5. **[Middleware](http/middleware.md)** - Add cross-cutting concerns
6. **[File Uploads](http/file-uploads.md)** - Handle multipart data
7. **[Authentication](security/authentication.md)** - Secure your API

### Advanced Track (Week 2)
8. **[WebSockets](advanced/websockets.md)** - Real-time communication
9. **[Background Tasks](advanced/background-tasks.md)** - Async processing
10. **[Performance Optimization](../performance/json-optimization.md)** - Maximum throughput
11. **[Service Mesh](advanced/vsp-service-protocol.md)** - Microservices architecture

### Expert Track (Week 3+)
12. **[Custom Middleware](http/middleware.md#custom-middleware)** - Build your own middleware
13. **[Gateway & Proxy](advanced/proxy-gateway.md)** - API gateway patterns
14. **[Deployment](../deployment/production-setup.md)** - Production deployment
15. **[Monitoring](../performance/monitoring.md)** - Observability and metrics

## 🎓 Prerequisites

Before diving into the user guide, you should have:

- **Python 3.10+** experience
- **Async/await** understanding
- **HTTP concepts** knowledge
- **REST API** familiarity
- **Basic security** awareness

## 🔄 Framework Comparison

| Feature | Velithon | FastAPI | Django | Flask |
|---------|----------|---------|--------|-------|
| **Protocol** | RSGI | ASGI | WSGI | WSGI |
| **Performance** | 115k req/s | 65k req/s | 15k req/s | 20k req/s |
| **WebSockets** | Advanced (Rooms/Channels) | Basic | Channels | Extensions |
| **DI System** | Native Advanced | Basic | Manual | Manual |
| **Service Mesh** | Built-in VSP | External | External | External |
| **Security** | Comprehensive | Good | Excellent | Basic |
| **Learning Curve** | Moderate | Easy | Steep | Easy |

## 🚀 What Makes Velithon Unique

1. **RSGI Performance** - 5-10x faster than traditional frameworks
2. **VSP Protocol** - Built-in service mesh and discovery
3. **Advanced WebSockets** - Channels, rooms, heartbeat monitoring
4. **Enterprise DI** - Production-ready dependency injection
5. **Security First** - Comprehensive auth/authz system
6. **Microservice Ready** - Native distributed systems support

Ready to master Velithon? Start with **[Application Concepts](core-concepts/application.md)** and work your way through the comprehensive guides.

**[Begin Your Journey →](core-concepts/application.md)**
