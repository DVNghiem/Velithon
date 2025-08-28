# Velithon Documentation

Welcome to the comprehensive documentation for Velithon, a high-performance RSGI web framework for Python.

## 📚 Documentation Overview

This documentation covers all aspects of building applications with Velithon, from basic concepts to advanced production deployments.

## 🚀 Quick Navigation

### Getting Started
- **[Installation](getting-started/installation.md)** - Set up your development environment
- **[Quick Start](getting-started/quick-start.md)** - Build your first application in minutes
- **[Core Concepts](user-guide/core-concepts.md)** - Understand the framework architecture

### User Guide
- **[HTTP Endpoints](user-guide/http-endpoints.md)** - Request/response handling
- **[Routing](user-guide/routing.md)** - URL routing and path parameters
- **[Middleware](user-guide/middleware.md)** - Built-in and custom middleware
- **[Dependency Injection](user-guide/dependency-injection.md)** - DI system
- **[WebSocket Support](user-guide/websocket.md)** - Real-time communication
- **[Background Tasks](user-guide/background-tasks.md)** - Async task processing
- **[Templates](user-guide/templates.md)** - HTML templating with Jinja2
- **[File Uploads](user-guide/file-uploads.md)** - File handling and validation
- **[Error Handling](user-guide/error-handling.md)** - Exception management
- **[Best Practices](user-guide/best-practices.md)** - Production-ready patterns

### Security
- **[Authentication](security/authentication.md)** - JWT, OAuth2, API Keys
- **[Authorization](security/authorization.md)** - Role-based access control
- **[JWT Tokens](security/jwt.md)** - Token management
- **[API Keys](security/api-keys.md)** - API key authentication
- **[OAuth2](security/oauth2.md)** - Third-party authentication
- **[Permissions](security/permissions.md)** - Permission system
- **[Security Middleware](security/middleware.md)** - Security headers and protection
- **[Best Practices](security/best-practices.md)** - Security guidelines

### Advanced Features
- **[Gateway](advanced/gateway.md)** - API gateway capabilities
- **[Performance](advanced/performance.md)** - Optimization techniques
- **[Circuit Breaker](advanced/circuit-breaker.md)** - Fault tolerance
- **[Connection Pooling](advanced/connection-pooling.md)** - Database optimization
- **[Health Checks](advanced/health-checks.md)** - Service monitoring
- **[Load Balancing](advanced/load-balancing.md)** - Traffic distribution
- **[JSON Optimization](advanced/json-optimization.md)** - Performance tuning

### API Reference
- **[Application](api/application.md)** - Main application class
- **[Requests](api/requests.md)** - Request handling
- **[Responses](api/responses.md)** - Response types
- **[Routing](api/routing.md)** - Route definitions
- **[Middleware](api/middleware.md)** - Middleware system
- **[WebSocket](api/websocket.md)** - WebSocket support
- **[Security](api/security.md)** - Security components

### Deployment
- **[Development](deployment/development.md)** - Local development setup
- **[Production](deployment/production.md)** - Production deployment
- **[Docker](deployment/docker.md)** - Container deployment
- **[Kubernetes](deployment/kubernetes.md)** - K8s deployment
- **[Cloud Platforms](deployment/cloud.md)** - Cloud deployment

### Examples
- **[Basic Application](examples/basic.md)** - Simple "Hello World"
- **[Authentication](examples/authentication.md)** - User authentication
- **[CRUD API](examples/crud-api.md)** - Database operations
- **[File Upload](examples/file-upload.md)** - File handling
- **[Real-time Chat](examples/websocket-chat.md)** - WebSocket chat
- **[Microservices](examples/microservices.md)** - Service architecture

### OpenAPI & Documentation
- **[Automatic Documentation](openapi/automatic.md)** - Auto-generated docs
- **[Custom Documentation](openapi/custom.md)** - Custom OpenAPI specs
- **[Export Documentation](openapi/export.md)** - Export API docs
- **[Swagger UI](openapi/swagger-ui.md)** - Interactive documentation

### CLI Reference
- **[CLI Commands](cli/index.md)** - Command-line interface
- **[Configuration](cli/configuration.md)** - CLI configuration
- **[Development Server](cli/development.md)** - Development tools

## 🔄 Recent Updates

### Version 0.6.1 Updates

The documentation has been updated to reflect the current framework status:

#### ✅ Updated Features
- **RSGI Protocol**: Updated all references to use RSGI instead of ASGI
- **Granian Server**: Updated server references to use Granian
- **CLI Commands**: Updated CLI documentation with current options
- **Middleware**: Updated middleware documentation with current components
- **Security**: Updated security features and authentication methods
- **Performance**: Updated performance metrics and optimization techniques

#### 🆕 New Features Documented
- **Advanced Middleware**: LoggingMiddleware, PrometheusMiddleware, ProxyMiddleware
- **Security Components**: JWT, OAuth2, API Keys, RBAC
- **Performance Features**: JSON optimization
- **Deployment**: Docker, Kubernetes, Cloud platforms
- **Monitoring**: Prometheus metrics, health checks

#### 🔧 Framework Changes
- **Version**: Updated to 0.6.1
- **Dependencies**: Updated dependency list
- **Python Support**: Python 3.10, 3.11, 3.12, 3.13
- **Architecture**: RSGI-based architecture with Granian server
- **Performance**: ~70,000 requests/second capability

## 📖 Documentation Structure

```
docs/
├── getting-started/          # Quick start guides
├── user-guide/              # Core concepts and features
├── security/                # Authentication and security
├── advanced/                # Advanced features
├── api/                     # API reference
├── deployment/              # Deployment guides
├── examples/                # Code examples
├── openapi/                 # OpenAPI documentation
├── cli/                     # CLI reference
└── contributing/            # Contributing guidelines
```

## 🎯 Framework Highlights

### Performance
- **~70,000 req/s** for simple endpoints
- **RSGI protocol** for maximum performance
- **Granian server** with HTTP/2 support
- **Optimized JSON** processing with orjson

### Features
- **Dependency Injection** - Enterprise-grade DI system
- **WebSocket Support** - Real-time communication
- **Server-Sent Events** - Live data streaming
- **Middleware Stack** - Comprehensive middleware system
- **Security** - JWT, OAuth2, RBAC, API Keys
- **Monitoring** - Prometheus metrics, health checks
- **Templates** - Jinja2 integration
- **File Uploads** - Secure file handling

### Architecture
- **RSGI Protocol** - Rust Server Gateway Interface
- **Async/Await** - Native async support
- **Type Safety** - Full type hints and validation
- **OpenAPI** - Automatic API documentation
- **CLI Tools** - Comprehensive command-line interface

## 🚀 Getting Help

- **[GitHub Issues](https://github.com/DVNghiem/velithon/issues)** - Report bugs
- **[Discussions](https://github.com/DVNghiem/velithon/discussions)** - Community help
- **[Examples](examples/index.md)** - Code examples
- **[API Reference](api/application.md)** - Complete API docs

## 📄 License

Velithon is released under the [BSD-3-Clause License](https://github.com/DVNghiem/velithon/blob/main/LICENSE).

---

**Ready to build high-performance Python web applications?** Start with the [Quick Start Guide](getting-started/quick-start.md)!
