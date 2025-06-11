"""Tests for application HTTP method decorators."""
import pytest

from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse


@pytest.fixture
def app():
    """Create a test app with no default routes."""
    return Velithon(
        # Disable OpenAPI routes
        openapi_url=None,
        docs_url=None
    )

def test_get_decorator(app):
    """Test the GET decorator."""
    
    @app.get("/test")
    async def get_handler(request: Request):
        return JSONResponse({"method": "GET"})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/test"
    assert route.methods == {"GET", "HEAD"}

def test_post_decorator(app):
    """Test the POST decorator."""
    
    @app.post("/test")
    async def post_handler(request: Request):
        return JSONResponse({"method": "POST"})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/test"
    assert route.methods == {"POST"}

def test_put_decorator(app):
    """Test the PUT decorator."""
    
    @app.put("/test")
    async def put_handler(request: Request):
        return JSONResponse({"method": "PUT"})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/test"
    assert route.methods == {"PUT"}

def test_delete_decorator(app):
    """Test the DELETE decorator."""
    
    @app.delete("/test")
    async def delete_handler(request: Request):
        return JSONResponse({"method": "DELETE"})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/test"
    assert route.methods == {"DELETE"}

def test_patch_decorator(app):
    """Test the PATCH decorator."""
    
    @app.patch("/test")
    async def patch_handler(request: Request):
        return JSONResponse({"method": "PATCH"})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/test"
    assert route.methods == {"PATCH"}

def test_options_decorator(app):
    """Test the OPTIONS decorator."""
    
    @app.options("/test")
    async def options_handler(request: Request):
        return JSONResponse({"method": "OPTIONS"})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/test"
    assert route.methods == {"OPTIONS"}

def test_combine_multiple_decorators(app):
    """Test using multiple HTTP method decorators."""
    
    @app.get("/api/resource")
    @app.post("/api/resource")
    @app.put("/api/resource")
    async def handle_resource(request: Request):
        return JSONResponse({"method": request.method})
    
    assert len(app.router.routes) == 3
    
    # Check for each HTTP method
    methods = set()
    for route in app.router.routes:
        if route.path == "/api/resource":
            methods.update(route.methods)
            
    assert "GET" in methods or "HEAD" in methods  # HEAD is automatically added for GET routes
    assert "POST" in methods
    assert "PUT" in methods

def test_decorator_with_parameters(app):
    """Test HTTP method decorators with additional parameters."""
    
    @app.get(
        path="/users",
        name="get_users",
        summary="Get all users",
        description="Returns a list of all users",
        tags=["users"],
        include_in_schema=True,
    )
    async def get_users(request: Request):
        return JSONResponse({"users": []})
    
    assert len(app.router.routes) == 1
    route = app.router.routes[0]
    assert route.path == "/users"
    assert route.name == "get_users"
    assert route.summary == "Get all users"
    assert route.description == "Returns a list of all users"
    assert route.tags == ["users"]
    assert route.include_in_schema is True
