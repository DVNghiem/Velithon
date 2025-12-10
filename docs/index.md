# Welcome to Velithon

<div align="center">
  <h1>⚡ Velithon</h1>
  <p><strong>A lightweight, high-performance, asynchronous web framework for Python</strong></p>
  
  <p>
    <a href="https://pypi.org/project/velithon/"><img src="https://img.shields.io/pypi/v/velithon.svg" alt="PyPI version"></a>
    <a href="https://python.org/downloads/"><img src="https://img.shields.io/pypi/pyversions/velithon.svg" alt="Python versions"></a>
    <a href="https://github.com/DVNghiem/velithon/blob/main/LICENSE"><img src="https://img.shields.io/github/license/DVNghiem/velithon.svg" alt="License"></a>
    <a href="https://github.com/DVNghiem/velithon/actions"><img src="https://img.shields.io/github/workflow/status/DVNghiem/velithon/CI.svg" alt="Build status"></a>
  </p>
</div>

## What is Velithon?

Velithon is a modern, lightning-fast web framework for Python that combines simplicity with exceptional performance. Built on top of the RSGI protocol and powered by [Granian](https://github.com/emmett-framework/granian), Velithon delivers blazing-fast response times while maintaining clean, readable code.

## ✨ Key Features

<div class="grid cards" markdown>

-   :material-rocket-launch: **Ultra-High Performance**

    ---

    Optimized for maximum speed with orjson-only JSON processing. Built on RSGI protocol achieving ~70,000 requests per second.

-   :material-puzzle: **Dependency Injection**

    ---

    Seamless dependency injection with `Provide` and `inject` decorators for clean, testable code architecture.

-   :material-web: **WebSocket Support**

    ---

    Full WebSocket support with connection management, routing integration, and lifecycle hooks for real-time applications.

-   :material-broadcast: **Server-Sent Events**

    ---

    Built-in SSE support with structured events, keep-alive pings, and automatic reconnection for real-time streaming.

-   :material-cog: **Powerful Middleware**

    ---

    Built-in middleware for logging, CORS, compression, sessions, authentication, and custom middleware support.

-   :material-upload: **File Handling**

    ---

    Comprehensive file upload and form parsing with configurable limits and validation.

-   :material-security: **Authentication Ready**

    ---

    Built-in authentication and session management with JWT, OAuth2, API Keys, and secure HMAC signing.

-   :material-database: **Database Integration**

    ---

    Full SQLAlchemy async support with PostgreSQL, MySQL, SQLite. Repository pattern, transactions, migrations, and health checks.

-   :material-api: **OpenAPI Integration**

    ---

    Automatic API documentation generation with OpenAPI/Swagger support out of the box.

</div>

## 🚀 Quick Start

Get started with Velithon in just a few minutes:

### Installation

```bash
pip install velithon
```

### Your First App

```python title="main.py"
from velithon import Velithon

app = Velithon()

@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}

if __name__ == "__main__":
    app._serve(
        app="main:app",
        host="0.0.0.0", 
        port=8000,
        workers=1,
        log_level="INFO"
    )
```

### Run Your App

```bash
# Using the built-in CLI (recommended)
velithon run --app main:app --host 0.0.0.0 --port 8000

# Or using Python directly
python main.py
```

Visit `http://localhost:8000` to see your app in action!

## 📚 Learning Path

New to Velithon? Follow our structured learning path:

<div class="grid cards" markdown>

-   **[Installation](getting-started/installation.md)**
    
    Set up your development environment and install Velithon

-   **[Quick Start](getting-started/quick-start.md)**
    
    Build your first Velithon application in minutes

-   **[Core Concepts](user-guide/core-concepts.md)**
    
    Understand the fundamental concepts and architecture

-   **[User Guide](user-guide/index.md)**
    
    Deep dive into all features with practical examples

</div>

## 🎯 Use Cases

Velithon is perfect for:

- **High-Performance APIs**: REST API that need to handle thousands of requests per second
- **Real-Time Applications**: Chat applications, live dashboards, and collaborative tools using WebSockets
- **Microservices**: Lightweight services in a microservices architecture
- **IoT Backends**: High-throughput backends for IoT device data collection
- **Streaming Services**: Real-time data streaming with Server-Sent Events
- **Enterprise Applications**: Scalable business applications with complex authentication needs

## 🔥 Performance Highlights

- **~70,000 req/s** - Exceptional throughput for REST API endpoints
- **Advanced JSON Processing** - Optimized serialization with orjson
- **Memory Efficient** - Minimal memory footprint and smart resource management
- **Async-First** - Built from the ground up for asynchronous operations
- **Low Latency** - Sub-millisecond response times for simple endpoints

## 🌟 Why Choose Velithon?

Velithon stands out as a next-generation Python web framework built on the **RSGI (Rust Server Gateway Interface)** protocol and powered by **[Granian](https://github.com/emmett-framework/granian)**, delivering exceptional performance without compromising on developer experience.

### 🚀 **RSGI-Powered Performance**
Unlike traditional ASGI frameworks, Velithon leverages RSGI for:
- **~70,000 req/s** throughput (exceptional performance for Python)
- **Native Rust optimizations** in the core runtime
- **Zero-copy operations** for maximum efficiency
- **Memory-efficient** request handling

### 🔧 **Built for Modern Development**
- **Pure Python API** - No Rust knowledge required
- **Advanced Dependency Injection** - Enterprise-grade DI system
- **Optimized JSON Processing** - Rust-based parallel serialization
- **Native WebSocket Support** - Real-time applications made easy

### 📊 **Framework Comparison**

| Feature | Velithon | FastAPI | Flask | Django |
|---------|----------|---------|-------|--------|
| **Foundation** | ⚡ RSGI + Granian | ASGI + Uvicorn | WSGI | WSGI |
| **Learning Curve** | 📈 Easy | 📈 Easy | 📈 Easy | 📊 Steep |
| **Type Safety** | ✅ Full | ✅ Full | ❌ Optional | ❌ Optional |
| **Async Support** | ✅ Native RSGI | ✅ Native ASGI | ⚠️ Limited | ⚠️ Limited |
| **WebSockets** | ✅ Built-in | ✅ Via Starlette | ❌ Extensions | ❌ Channels |
| **Dependency Injection** | ✅ Advanced | ✅ Basic | ❌ Manual | ❌ Manual |
| **JSON Optimization** | ✅ orjson-only | ❌ Standard | ❌ Standard | ❌ Standard |
| **Gateway/Proxy** | ✅ Built-in | ❌ External | ❌ External | ❌ External |

### 🎯 **When to Choose Velithon**
- ✅ **High-throughput APIs** requiring maximum performance
- ✅ **Real-time applications** with WebSocket requirements  
- ✅ **Microservices architectures** needing efficient inter-service communication
- ✅ **Data-heavy applications** benefiting from optimized JSON processing
- ✅ **Enterprise applications** requiring advanced dependency injection

## 🤝 Community & Support

- **[GitHub](https://github.com/DVNghiem/velithon)** - Source code, issues, and discussions
- **[PyPI](https://pypi.org/project/velithon/)** - Official Python package
- **[Documentation](https://velithon.readthedocs.io)** - Comprehensive guides and API reference
- **[Examples](examples/index.md)** - Real-world application examples

## 📄 License

Velithon is released under the [BSD-3-Clause License](https://github.com/DVNghiem/velithon/blob/main/LICENSE).

---

Ready to build lightning-fast Python web applications? **[Get started now!](getting-started/installation.md)**
