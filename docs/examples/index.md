# Examples

This section provides comprehensive examples of Velithon applications, from simple "Hello World" to complex production-ready systems.

## 🚀 Quick Examples

### Basic Examples

<div class="grid cards" markdown>

-   **[Basic Application](basic.md)**
    
    Simple "Hello World" application with basic routing

-   **[Authentication Example](authentication.md)**
    
    JWT authentication with user management

-   **[CRUD API](crud-api.md)**
    
    Complete CRUD operations with database integration

-   **[File Upload](file-upload.md)**
    
    File upload handling with validation

-   **[Real-time Chat](websocket-chat.md)**
    
    WebSocket-based real-time chat application

-   **[Microservices](microservices.md)**
    
    Microservices architecture with service communication

</div>

## 🎯 Example Categories

### Authentication & Security

- **JWT Authentication**: Complete JWT implementation with refresh tokens
- **OAuth2 Integration**: Third-party authentication (Google, GitHub, etc.)
- **API Key Management**: Secure API key handling
- **Role-Based Access Control**: User roles and permissions
- **Session Management**: Secure session handling

### Data Handling

- **Database Integration**: SQLAlchemy, asyncpg, and other ORMs
- **File Upload**: Secure file handling with validation
- **Form Processing**: Complex form handling with validation
- **JSON Processing**: Optimized JSON serialization
- **Caching**: Redis and in-memory caching strategies

### Real-time Features

- **WebSocket Chat**: Real-time messaging
- **Server-Sent Events**: Live data streaming
- **Live Notifications**: Push notifications
- **Collaborative Editing**: Real-time document editing
- **Gaming**: Real-time game state management

### Performance & Scalability

- **Load Balancing**: Multiple backend distribution
- **Caching Strategies**: Redis, memory, and CDN caching
- **Background Tasks**: Async task processing
- **Rate Limiting**: Request throttling
- **Circuit Breakers**: Fault tolerance patterns

### Monitoring & Observability

- **Prometheus Metrics**: Application metrics collection
- **Health Checks**: Service health monitoring
- **Logging**: Structured logging with correlation IDs
- **Tracing**: Distributed tracing with OpenTelemetry
- **Error Handling**: Comprehensive error management

## 🛠️ Example Structure

Each example follows a consistent structure:

```python
# 1. Application Setup
from velithon import Velithon
from velithon.middleware import LoggingMiddleware, CORSMiddleware

app = Velithon(
    title="Example API",
    description="A comprehensive example",
    version="1.0.0",
    middleware=[
        LoggingMiddleware(),
        CORSMiddleware(origins=["*"])
    ]
)

# 2. Models and Validation
from pydantic import BaseModel

class User(BaseModel):
    username: str
    email: str

# 3. Route Handlers
@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/users")
async def create_user(user: User):
    return {"user": user.dict()}

# 5. Application Startup
if __name__ == "__main__":
    app._serve(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        workers=1
    )
```

## 🔧 Running Examples

### Prerequisites

```bash
# Install Velithon
pip install velithon

# Install additional dependencies for examples
pip install redis sqlalchemy asyncpg httpx
```

### Running an Example

```bash
# Clone the repository
git clone https://github.com/DVNghiem/velithon.git
cd velithon

# Navigate to examples
cd examples

# Run a specific example
python basic_example.py

# Or use the CLI
velithon run --app basic_example:app --host 0.0.0.0 --port 8000
```

### Testing Examples

```bash
# Install testing dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/test_examples.py

# Run specific example tests
pytest tests/test_basic_example.py
```

## 📊 Example Performance

All examples are optimized for performance:

- **Basic API**: ~70,000 requests/second
- **Database CRUD**: ~50,000 requests/second
- **File Upload**: ~10,000 requests/second
- **WebSocket**: ~5,000 concurrent connections
- **Real-time Chat**: ~1,000 messages/second

## 🎯 Contributing Examples

We welcome contributions! To add an example:

1. **Create the example file** in `examples/`
2. **Add tests** in `tests/test_examples.py`
3. **Update documentation** in `docs/examples/`
4. **Follow the structure** shown above
5. **Include performance metrics** if applicable

### Example Template

```python
"""
Example: [Name]

Description: Brief description of what this example demonstrates.

Features:
- Feature 1
- Feature 2
- Feature 3

Performance: ~X requests/second
"""

from velithon import Velithon
# ... rest of the example
```

## 📚 Related Documentation

- **[User Guide](../user-guide/index.md)** - Core concepts and features
- **[API Reference](../api/index.md)** - Complete API documentation
- **[Security](../security/index.md)** - Authentication and authorization
- **[Deployment](../deployment/index.md)** - Production deployment guides

Start with the basic examples and work your way up to complex applications. Each example builds upon the previous ones, helping you understand Velithon's capabilities progressively.
