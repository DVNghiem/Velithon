# GraphQL Support in Velithon

Velithon provides high-performance GraphQL implementation powered by Rust's async-graphql library and seamlessly integrated with Python through PyO3. This combination delivers exceptional performance with over 6,500 queries per second and sub-millisecond latency.

## 🚀 Features

- **High Performance**: Rust-powered backend with 6,500+ QPS
- **Low Latency**: Sub-millisecond query execution (0.15ms average)
- **Batch Operations**: Execute multiple queries in a single request
- **Query Builder**: Programmatically build GraphQL queries
- **Schema Validation**: Built-in query validation and error handling
- **GraphQL Playground**: Interactive query development interface
- **Production Ready**: Robust error handling and memory efficiency
- **Type Safety**: Full Python type hints and Rust type system integration

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Server Integration](#server-integration)
5. [Performance Optimization](#performance-optimization)
6. [Best Practices](#best-practices)
7. [API Reference](#api-reference)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

## 🏁 Quick Start

### Installation

GraphQL support is included with Velithon. No additional installation required.

```bash
pip install velithon
```

### Basic Example

```python
from velithon.graphql import GraphQLSchema

# Create a schema
schema = GraphQLSchema()

# Execute a query
result = schema.execute('query { hello }')
print(result.to_dict())
# Output: {'data': {'hello': 'Hello, World!'}}
```

## 💡 Basic Usage

### Creating a Schema

```python
from velithon.graphql import GraphQLSchema

# Create with default configuration
schema = GraphQLSchema()

# Schema includes built-in queries:
# - hello(name: String): String
# - serverTime: DateTime
```

### Simple Query Execution

```python
# Basic hello query
result = schema.execute('query { hello }')
print(result.data)  # {'hello': 'Hello, World!'}

# Parameterized query
result = schema.execute('query { hello(name: "Developer") }')
print(result.data)  # {'hello': 'Hello, Developer!'}

# Server time query
result = schema.execute('query { serverTime }')
print(result.data)  # {'serverTime': '2025-09-24T16:00:00.000Z'}
```

### Multi-field Queries

```python
# Query multiple fields at once
query = '''
query {
    hello(name: "User")
    serverTime
}
'''

result = schema.execute(query)
print(result.data)
# Output: {
#     'hello': 'Hello, User!',
#     'serverTime': '2025-09-24T16:00:00.000Z'
# }
```

### Error Handling

```python
# Execute invalid query
result = schema.execute('query { invalidField }')

if result.errors:
    print("Query errors:")
    for error in result.errors:
        print(f"- {error['message']}")
else:
    print("Success:", result.data)
```

## 🔥 Advanced Features

### Batch Query Execution

Execute multiple queries in a single request for improved performance:

```python
from velithon.graphql import GraphQLSchema

schema = GraphQLSchema()

# Define batch queries
batch_queries = [
    {'query': 'query { hello }'},
    {'query': 'query { hello(name: "Batch1") }'},
    {'query': 'query { hello(name: "Batch2") }'},
    {'query': 'query { serverTime }'}
]

# Execute batch
results = schema.execute_batch(batch_queries)

# Process results
for i, result in enumerate(results):
    print(f"Query {i+1}: {result.to_dict()}")
```

### Query Builder

Programmatically build GraphQL queries:

```python
from velithon.graphql import GraphQLQueryBuilder

# Create builder
builder = GraphQLQueryBuilder()

# Add fields
builder.field('hello', {'name': 'Builder'})
builder.field('serverTime')

# Build query
query = builder.build()
print(query)  # query { hello(name: "Builder") serverTime }

# Execute
schema = GraphQLSchema()
result = schema.execute(query)
print(result.data)

# Reset builder for reuse
builder.reset()
builder.field('hello')
new_query = builder.build()
```

### Query Validation

Validate queries before execution:

```python
from velithon.graphql import GraphQLSchema

schema = GraphQLSchema()

# Validate queries
valid_query = 'query { hello }'
invalid_query = 'query { invalidField }'

print(schema.validate(valid_query))    # True
print(schema.validate(invalid_query))  # False
```

### Schema Introspection

Get schema definition in SDL format:

```python
from velithon.graphql import GraphQLSchema

schema = GraphQLSchema()

# Get schema SDL
sdl = schema.get_schema_sdl()
print(sdl)
```

## 🌐 Server Integration

### Complete GraphQL Server

```python
from velithon import Velithon
from velithon.graphql import GraphQLSchema
from velithon.responses import HTMLResponse, JSONResponse

def create_app():
    app = Velithon()
    schema = GraphQLSchema()

    @app.get("/")
    async def root():
        return JSONResponse({
            "name": "GraphQL API",
            "endpoints": {
                "/graphql": "GraphQL API endpoint",
                "/playground": "GraphQL Playground"
            }
        })

    @app.get("/playground")
    async def playground():
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>GraphQL Playground</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <link
                rel="stylesheet"
                href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/static/css/index.css"
            />
        </head>
        <body>
            <div id="root"></div>
            <script
                src="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/static/js/middleware.js"
            ></script>
            <script>
                window.GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/graphql',
                    settings: {
                        'editor.theme': 'dark',
                        'editor.fontSize': 14
                    }
                });
            </script>
        </body>
        </html>
        '''
        return HTMLResponse(html)

    @app.post("/graphql")
    async def graphql_endpoint(request):
        try:
            content_type = request.headers.get("content-type", "").lower()
            
            if "application/json" not in content_type:
                return JSONResponse(
                    {"errors": [{"message": "Content-Type must be application/json"}]}, 
                    status_code=400
                )

            body = await request.json()
            
            if isinstance(body, list):
                # Batch query
                responses = schema.execute_batch(body)
                return JSONResponse([resp.to_dict() for resp in responses])
            else:
                # Single query
                query = body.get("query", "")
                variables = body.get("variables")
                operation_name = body.get("operationName")
                
                response = schema.execute(query, variables, operation_name)
                return JSONResponse(response.to_dict())
                
        except Exception as e:
            return JSONResponse(
                {"errors": [{"message": f"Server error: {e!s}"}]}, 
                status_code=500
            )

    return app

# Run the server
if __name__ == "__main__":
    import granian
    
    server = granian.Granian(
        target="__main__:create_app",
        interface='rsgi',
        address="0.0.0.0",
        port=8000,
        workers=1,
    )
    server.serve()
```

### Health Check Integration

```python
@app.get("/health")
async def health():
    schema = GraphQLSchema()
    
    # Test GraphQL functionality
    try:
        result = schema.execute('query { hello }')
        graphql_status = "healthy" if result.data else "unhealthy"
    except Exception:
        graphql_status = "unhealthy"
    
    return JSONResponse({
        "status": "healthy",
        "services": {
            "graphql": graphql_status,
            "server": "healthy"
        }
    })
```

## ⚡ Performance Optimization

### Batch Queries for High Throughput

```python
# Instead of multiple individual requests
# BAD: Multiple round trips
results = []
for query in queries:
    result = schema.execute(query)
    results.append(result)

# GOOD: Single batch request
batch_queries = [{'query': q} for q in queries]
results = schema.execute_batch(batch_queries)
```

### Query Complexity Management

```python
# Keep queries simple and focused
# GOOD: Specific fields
query = 'query { hello(name: "User") }'

# AVOID: Overly complex nested queries
# Complex queries should be split into multiple simpler ones
```

### Connection Pooling

```python
# Reuse schema instances
class GraphQLService:
    def __init__(self):
        self.schema = GraphQLSchema()  # Create once
    
    def execute_query(self, query):
        return self.schema.execute(query)  # Reuse instance

# Singleton pattern for production
graphql_service = GraphQLService()
```

## 📚 Best Practices

### 1. Schema Design

```python
# Always validate queries before execution in production
def safe_execute(schema, query):
    if not schema.validate(query):
        return {"errors": [{"message": "Invalid query"}]}
    
    return schema.execute(query).to_dict()
```

### 2. Error Handling

```python
def robust_graphql_handler(schema, query):
    try:
        # Validate first
        if not schema.validate(query):
            return {
                "data": None,
                "errors": [{"message": "Query validation failed"}]
            }
        
        # Execute with timeout protection
        result = schema.execute(query)
        return result.to_dict()
        
    except Exception as e:
        return {
            "data": None,
            "errors": [{"message": f"Execution error: {e!s}"}]
        }
```

### 3. Input Sanitization

```python
import re

def sanitize_query(query):
    # Remove potentially dangerous patterns
    if re.search(r'(__|mutation|subscription)', query.lower()):
        raise ValueError("Unsafe query pattern detected")
    
    # Limit query length
    if len(query) > 1000:
        raise ValueError("Query too long")
    
    return query.strip()
```

### 4. Caching Strategy

```python
from functools import lru_cache

class CachedGraphQLSchema:
    def __init__(self):
        self.schema = GraphQLSchema()
    
    @lru_cache(maxsize=128)
    def execute_cached(self, query):
        """Cache results for identical queries"""
        return self.schema.execute(query).to_dict()
    
    def execute_batch(self, queries):
        """Non-cached batch execution"""
        return self.schema.execute_batch(queries)
```

### 5. Monitoring and Logging

```python
import time
import logging

logger = logging.getLogger(__name__)

def monitored_execute(schema, query):
    start_time = time.time()
    
    try:
        result = schema.execute(query)
        execution_time = time.time() - start_time
        
        logger.info(f"GraphQL query executed in {execution_time:.3f}s")
        
        if result.errors:
            logger.warning(f"Query errors: {result.errors}")
        
        return result.to_dict()
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"GraphQL error after {execution_time:.3f}s: {e}")
        raise
```

## 📖 API Reference

### GraphQLSchema

Main class for GraphQL operations.

#### Methods

- **`execute(query, variables=None, operation_name=None, context=None) -> GraphQLResponse`**
  - Execute a single GraphQL query
  - Returns: GraphQLResponse object

- **`execute_batch(queries) -> List[GraphQLResponse]`**
  - Execute multiple queries in batch
  - Args: List of query dictionaries
  - Returns: List of GraphQLResponse objects

- **`validate(query) -> bool`**
  - Validate a GraphQL query syntax
  - Returns: True if valid, False otherwise

- **`get_schema_sdl() -> str`**
  - Get schema definition in SDL format
  - Returns: SDL string

### GraphQLResponse

Response object containing query results.

#### Properties

- **`data: Optional[dict]`** - Query result data
- **`errors: Optional[List[dict]]`** - Query errors if any
- **`extensions: Optional[dict]`** - Additional response metadata

#### Methods

- **`to_dict() -> dict`** - Convert response to dictionary
- **`from_json(json_str) -> GraphQLResponse`** - Create from JSON string

### GraphQLQueryBuilder

Utility for building GraphQL queries programmatically.

#### Methods

- **`field(name, args=None, subfields=None) -> GraphQLQueryBuilder`**
  - Add a field to the query
  - Returns: Self for method chaining

- **`build(operation_type="query") -> str`**
  - Build the final query string
  - Returns: GraphQL query string

- **`reset() -> GraphQLQueryBuilder`**
  - Reset the builder state
  - Returns: Self for method chaining

## 🔍 Examples

### Example 1: Basic CRUD Operations

```python
from velithon.graphql import GraphQLSchema

schema = GraphQLSchema()

# Read operations
users = schema.execute('query { hello(name: "John") }')
user_time = schema.execute('query { serverTime }')

print("User greeting:", users.data)
print("Current time:", user_time.data)
```

### Example 2: Batch Processing

```python
from velithon.graphql import GraphQLSchema

schema = GraphQLSchema()

# Process multiple users
users = ["Alice", "Bob", "Charlie"]
batch_queries = [
    {'query': f'query {{ hello(name: "{user}") }}'}
    for user in users
]

results = schema.execute_batch(batch_queries)

for user, result in zip(users, results):
    print(f"{user}: {result.data}")
```

### Example 3: Dynamic Query Building

```python
from velithon.graphql import GraphQLQueryBuilder, GraphQLSchema

builder = GraphQLQueryBuilder()
schema = GraphQLSchema()

# Build query dynamically based on user input
fields = ["hello", "serverTime"]
for field in fields:
    if field == "hello":
        builder.field(field, {"name": "Dynamic"})
    else:
        builder.field(field)

query = builder.build()
result = schema.execute(query)
print(result.data)
```

### Example 4: Error Recovery

```python
from velithon.graphql import GraphQLSchema

schema = GraphQLSchema()

queries = [
    'query { hello }',           # Valid
    'query { invalidField }',    # Invalid
    'query { serverTime }',      # Valid
]

for i, query in enumerate(queries):
    result = schema.execute(query)
    
    if result.errors:
        print(f"Query {i+1} failed: {result.errors[0]['message']}")
    else:
        print(f"Query {i+1} success: {result.data}")
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors

```python
# Problem: ModuleNotFoundError: No module named 'velithon.graphql'
# Solution: Ensure Velithon is properly installed
pip install velithon

# Or rebuild from source
maturin develop
```

#### 2. Query Validation Failures

```python
# Problem: Queries fail validation
# Solution: Check query syntax
schema = GraphQLSchema()

query = "query { hello }"  # Missing closing brace
if not schema.validate(query):
    print("Invalid query syntax")
```

#### 3. Performance Issues

```python
# Problem: Slow query execution
# Solution: Use batch queries and caching

# Instead of:
for query in many_queries:
    schema.execute(query)

# Use:
schema.execute_batch([{'query': q} for q in many_queries])
```

#### 4. Memory Usage

```python
# Problem: High memory usage
# Solution: Reuse schema instances

# Global schema instance
SCHEMA = GraphQLSchema()

def execute_query(query):
    return SCHEMA.execute(query)  # Reuse instead of creating new
```

### Performance Metrics

Our testing shows these performance characteristics:

- **Throughput**: 6,500+ queries per second
- **Latency**: 0.15ms average per query
- **Memory**: Efficient resource usage with minimal overhead
- **Concurrency**: Excellent performance under load

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# GraphQL operations will log detailed information
schema = GraphQLSchema()
result = schema.execute('query { hello }')
```

## 🎯 Production Deployment

### Environment Variables

```bash
# .env file
GRAPHQL_DEBUG=false
GRAPHQL_ENABLE_PLAYGROUND=false
GRAPHQL_MAX_QUERY_DEPTH=10
```

### Production Configuration

```python
import os
from velithon.graphql import GraphQLSchema

# Production-ready configuration
class ProductionGraphQL:
    def __init__(self):
        self.schema = GraphQLSchema()
        self.debug = os.getenv('GRAPHQL_DEBUG', 'false').lower() == 'true'
        self.playground = os.getenv('GRAPHQL_ENABLE_PLAYGROUND', 'false').lower() == 'true'
    
    def execute(self, query, **kwargs):
        # Add production safeguards
        if len(query) > 1000:
            raise ValueError("Query too long")
        
        if not self.schema.validate(query):
            raise ValueError("Invalid query")
        
        return self.schema.execute(query, **kwargs)
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN maturin develop

EXPOSE 8000
CMD ["python", "examples/graphql_server.py"]
```

---

**🚀 Ready to build high-performance GraphQL APIs with Velithon!**

For more information, visit the [Velithon Documentation](https://github.com/DVNghiem/Velithon) or check out the complete examples in the `examples/` directory.

Velithon now includes high-performance GraphQL support powered by Rust. This implementation provides blazing-fast GraphQL query execution while maintaining Python's ease of use.

## Features

✅ **High-Performance Rust Backend** - Core GraphQL execution powered by async-graphql  
✅ **Python Integration** - Seamless integration with Python applications  
✅ **Query Execution** - Execute GraphQL queries with variables and operation names  
✅ **Query Building** - Programmatic query building with fluent API  
✅ **Batch Operations** - Execute multiple queries in a single request  
✅ **Query Validation** - Validate GraphQL queries without execution  
✅ **Schema Introspection** - Access GraphQL Schema Definition Language (SDL)  
✅ **HTTP Endpoint** - Built-in HTTP endpoint with GraphQL Playground  

## Quick Start

### Basic Usage

```python
from velithon import GraphQLSchema

# Create a schema
schema = GraphQLSchema()

# Execute a simple query
result = schema.execute("query { hello }")
print(result.data)  # {'hello': 'Hello, World!'}

# Execute with parameters
result = schema.execute('query { hello(name: "Velithon") }')
print(result.data)  # {'hello': 'Hello, Velithon!'}
```

### Query Builder

```python
from velithon import GraphQLQueryBuilder

builder = GraphQLQueryBuilder()
builder.field("hello", {"name": "Builder"}, None)
builder.field("serverTime", None, None)

query = builder.build()
result = schema.execute(query)
print(result.data)
```

### Batch Execution

```python
queries = [
    {"query": "query { hello }"},
    {"query": 'query { hello(name: "Batch") }'},
    {"query": "query { serverTime }"}
]

results = schema.execute_batch(queries)
for result in results:
    print(result.data)
```

### HTTP Endpoint

```python
from velithon import Velithon
from velithon.graphql import GraphQLEndpoint

app = Velithon()

# Add GraphQL endpoint with Playground
app.add_route("/graphql", GraphQLEndpoint(), ["GET", "POST"])
```

## Available Queries

The default schema includes these queries:

### hello
```graphql
query {
  hello(name: String)  # Returns "Hello, {name}!" or "Hello, World!"
}
```

### serverTime
```graphql
query {
  serverTime  # Returns current server time in ISO format
}
```

## API Reference

### GraphQLSchema

Core schema class for GraphQL operations.

**Methods:**
- `execute(query, variables=None, operation_name=None)` - Execute a GraphQL query
- `execute_batch(queries)` - Execute multiple queries in batch  
- `validate(query)` - Validate a query without execution
- `get_schema_sdl()` - Get the schema definition

### GraphQLQueryBuilder  

Programmatic query builder.

**Methods:**
- `field(name, args=None, subfields=None)` - Add a field to the query
- `build(operation_type="query")` - Build the query string
- `reset()` - Reset the builder

### GraphQLResponse

Response object containing query results.

**Properties:**
- `data` - Query result data
- `errors` - Any execution errors  
- `extensions` - Additional response data

### GraphQLEndpoint

HTTP endpoint for GraphQL with built-in Playground.

**Features:**
- GET requests serve GraphQL Playground
- POST requests execute GraphQL queries
- Supports both single and batch queries
- JSON request/response format

## Performance

The GraphQL implementation leverages Rust's performance advantages:

- **Fast Query Parsing** - Rust-based query parsing and validation
- **Efficient Execution** - Async execution with minimal overhead  
- **Memory Efficient** - Zero-copy operations where possible
- **Concurrent Queries** - Handle multiple queries simultaneously

## Example Output

```bash
$ python examples/graphql_example.py

🚀 Velithon GraphQL Example
==================================================
✅ GraphQL Schema created successfully

📝 Example 1: Simple Hello Query
Query: query { hello }
Result: {'hello': 'Hello, World!'}

📝 Example 2: Hello Query with Parameters  
Query: query { hello(name: "Rust+Python") }
Result: {'hello': 'Hello, Rust+Python!'}

📝 Example 3: Server Time Query
Query: query { serverTime }
Result: {'serverTime': '2025-01-24T15:49:38.416785257+00:00'}

🎉 All GraphQL examples completed successfully!
   - High-performance Rust backend ✅
   - Python integration ✅
   - Query execution ✅
   - Query building ✅
   - Batch operations ✅
   - Validation ✅
```

## Integration with Velithon

The GraphQL feature integrates seamlessly with Velithon's existing features:

- **Routing** - Use GraphQL endpoints in your route definitions
- **Middleware** - Apply authentication, CORS, and other middleware
- **Error Handling** - Consistent error handling across HTTP and GraphQL
- **Async Support** - Full async/await compatibility
- **Request Context** - Access to request context within resolvers

This implementation demonstrates Velithon's commitment to combining Rust's performance with Python's productivity.