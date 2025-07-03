# Testing Guidelines

This guide covers how to write and run tests for Velithon contributions.

## Overview

Velithon uses a comprehensive testing strategy that includes unit tests, integration tests, and performance benchmarks. All contributions should include appropriate tests.

## Testing Framework

We use **pytest** as our primary testing framework along with several plugins:

- `pytest` - Core testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Code coverage
- `pytest-benchmark` - Performance benchmarks

## Running Tests

### Basic Test Commands

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_application.py

# Run specific test class
poetry run pytest tests/test_application.py::TestVelithon

# Run specific test method
poetry run pytest tests/test_application.py::TestVelithon::test_basic_route

# Run tests matching a pattern
poetry run pytest -k "test_auth"
```

### Coverage Testing

```bash
# Run tests with coverage
poetry run pytest --cov=velithon

# Generate HTML coverage report
poetry run pytest --cov=velithon --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

### Parallel Testing

```bash
# Run tests in parallel (faster)
poetry run pytest -n auto

# Specify number of workers
poetry run pytest -n 4
```

## Test Structure

### Directory Layout

```
tests/
├── conftest.py              # Shared fixtures
├── test_application.py      # Application tests
├── test_routing.py          # Routing tests
├── test_middleware.py       # Middleware tests
├── test_security.py         # Security tests
├── test_websocket.py        # WebSocket tests
├── test_di.py              # Dependency injection tests
├── integration/            # Integration tests
│   ├── test_full_app.py
│   └── test_performance.py
└── benchmarks/             # Performance benchmarks
    ├── test_request_handling.py
    └── test_json_serialization.py
```

### Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*` (optional)
- Test functions: `test_*`
- Fixtures: descriptive names without `test_` prefix

## Writing Tests

### Basic Test Example

```python
import pytest
import httpx
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse

def test_basic_route():
    """Test a basic GET route"""
    app = Velithon()
    
    @app.get("/hello")
    async def hello():
        return {"message": "Hello, World!"}
    
    # Test using httpx
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/hello")
        
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
```

### Async Test Example

```python
@pytest.mark.asyncio
async def test_async_endpoint():
    """Test an async endpoint with database operations"""
    app = Velithon()
    
    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        # Simulate async database call
        await asyncio.sleep(0.1)
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/users/123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 123
        assert "User 123" in data["name"]
```

### WebSocket Testing

```python
@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection and messaging"""
    app = Velithon()
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket):
        await websocket.accept()
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        async with client.websocket_connect("/ws") as websocket:
            await websocket.send_text("Hello WebSocket")
            data = await websocket.receive_text()
            assert data == "Echo: Hello WebSocket"
```

### Error Testing

```python
def test_error_handling():
    """Test error responses"""
    app = Velithon()
    
    @app.get("/error")
    async def error_endpoint():
        raise HTTPException(status_code=400, detail="Bad request")
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/error")
        
        assert response.status_code == 400
        assert "Bad request" in response.text
```

## Fixtures

### Common Fixtures (conftest.py)

```python
import pytest
import httpx
from velithon import Velithon

@pytest.fixture
def app():
    """Create a test application"""
    return Velithon(title="Test App")

@pytest.fixture
async def client(app):
    """Create an HTTP client for testing"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User"
    }

@pytest.fixture
async def authenticated_client(client):
    """Create an authenticated client"""
    # Login and get token
    login_response = await client.post("/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    token = login_response.json()["access_token"]
    
    # Add auth header
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

### Database Fixtures

```python
@pytest.fixture
async def db_session():
    """Create a test database session"""
    # Setup test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session = AsyncSession(engine)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()

@pytest.fixture
async def sample_user(db_session):
    """Create a test user in the database"""
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

## Mocking and Patching

### Mock External Services

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_external_api_call():
    """Test endpoint that calls external API"""
    app = Velithon()
    
    @app.get("/weather/{city}")
    async def get_weather(city: str):
        # This would normally call an external API
        weather_data = await fetch_weather_data(city)
        return weather_data
    
    # Mock the external API call
    with patch('your_module.fetch_weather_data') as mock_fetch:
        mock_fetch.return_value = {"city": "London", "temp": 20}
        
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/weather/London")
            
            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "London"
            assert data["temp"] == 20
            mock_fetch.assert_called_once_with("London")
```

### Mock Database Operations

```python
@pytest.mark.asyncio
async def test_user_creation_with_mock():
    """Test user creation with mocked database"""
    app = Velithon()
    
    @app.post("/users")
    async def create_user(user_data: dict):
        user = await UserService.create_user(user_data)
        return user
    
    with patch('your_module.UserService.create_user') as mock_create:
        mock_create.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/users", json={
                "username": "testuser",
                "email": "test@example.com"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
```

## Integration Tests

### Full Application Testing

```python
@pytest.mark.asyncio
async def test_full_user_workflow():
    """Test complete user registration and login workflow"""
    app = create_test_app()  # Your app factory
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # 1. Register user
        register_response = await client.post("/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123"
        })
        assert register_response.status_code == 201
        
        # 2. Login
        login_response = await client.post("/login", json={
            "username": "newuser",
            "password": "securepass123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 3. Access protected endpoint
        protected_response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert protected_response.status_code == 200
```

## Performance Testing

### Benchmark Tests

```python
import pytest

def test_json_serialization_performance(benchmark):
    """Benchmark JSON serialization performance"""
    data = {"key": "value", "number": 42, "list": [1, 2, 3]}
    
    result = benchmark(json.dumps, data)
    assert result is not None

@pytest.mark.asyncio
async def test_endpoint_performance():
    """Test endpoint response time"""
    app = Velithon()
    
    @app.get("/fast")
    async def fast_endpoint():
        return {"status": "ok"}
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        import time
        start_time = time.time()
        
        response = await client.get("/fast")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 0.1  # Should respond in less than 100ms
```

### Load Testing

```python
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling multiple concurrent requests"""
    app = Velithon()
    
    @app.get("/concurrent")
    async def concurrent_endpoint():
        await asyncio.sleep(0.1)  # Simulate work
        return {"status": "ok"}
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Send 10 concurrent requests
        tasks = [
            client.get("/concurrent")
            for _ in range(10)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
```

## Test Configuration

### pytest.ini

```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=velithon
    --cov-report=term-missing
    --cov-report=html
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    benchmark: marks tests as performance benchmarks
```

### Coverage Configuration

```toml
[tool.coverage.run]
source = ["velithon"]
omit = [
    "*/tests/*",
    "*/benchmarks/*",
    "*/__pycache__/*",
    "*/target/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: |
        poetry install --with dev
    
    - name: Run tests
      run: |
        poetry run pytest --cov=velithon --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Best Practices

### 1. Test Organization
- Group related tests in classes
- Use descriptive test names
- One assertion per test (when possible)
- Test both success and failure cases

### 2. Test Data
- Use fixtures for reusable test data
- Avoid hardcoded values
- Create minimal test data
- Clean up after tests

### 3. Async Testing
- Always use `@pytest.mark.asyncio` for async tests
- Use `AsyncClient` for HTTP testing
- Test timeout scenarios
- Handle WebSocket connections properly

### 4. Performance
- Write performance tests for critical paths
- Set reasonable performance expectations
- Monitor test execution time
- Use parallel testing when safe

### 5. Coverage
- Aim for high test coverage (>90%)
- Test edge cases and error conditions
- Don't write tests just for coverage
- Focus on critical business logic

## Debugging Tests

### Debug Failed Tests

```bash
# Run with debug output
poetry run pytest -vvv --tb=long

# Drop into debugger on failure
poetry run pytest --pdb

# Run specific failing test
poetry run pytest tests/test_auth.py::test_login -vvv
```

### Using Print Debugging

```python
def test_debug_example():
    """Example with debug output"""
    app = Velithon()
    
    @app.get("/debug")
    async def debug_endpoint():
        result = {"debug": True}
        print(f"Debug: returning {result}")  # This will show in test output
        return result
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/debug")
        print(f"Response: {response.json()}")  # Debug output
        assert response.status_code == 200
```

By following these testing guidelines, you'll help maintain Velithon's high quality and reliability standards.
