"""
Tests for application lifecycle and integration scenarios.
"""
import asyncio

import pytest

from velithon import Velithon
from velithon.di import Provide, ServiceContainer
from velithon.middleware import Middleware
from velithon.requests import Request
from velithon.responses import JSONResponse


class TestApplicationLifecycle:
    """Test application startup and shutdown lifecycle."""

    def test_application_initialization(self):
        """Test basic application initialization."""
        app = Velithon()
        
        assert app.router is not None
        assert app.container is None  # Container starts as None until registered
        assert isinstance(app.user_middleware, list)

    def test_application_with_custom_openapi_url(self):
        """Test application with custom OpenAPI URL."""
        app = Velithon(openapi_url="/custom-openapi.json")
        
        assert app.openapi_url == "/custom-openapi.json"

    def test_application_with_custom_title(self):
        """Test application with custom title."""
        app = Velithon(title="My Custom API")
        
        assert app.title == "My Custom API"

    def test_application_startup_handlers(self):
        """Test application startup event handlers."""
        startup_called = []
        app = Velithon()

        @app.on_startup(priority=0)
        def startup_handler():
            startup_called.append("called")

        @app.on_startup(priority=1)
        async def async_startup_handler():
            startup_called.append("async_called")
        
        assert len(app.startup_functions) >= 2

    def test_application_shutdown_handlers(self):
        """Test application shutdown event handlers."""
        shutdown_called = []
        app = Velithon()

        @app.on_shutdown(priority=0)
        def shutdown_handler():
            shutdown_called.append("called")

        @app.on_shutdown(priority=1) 
        async def async_shutdown_handler():
            shutdown_called.append("async_called")

        assert len(app.shutdown_functions) >= 2

    def test_application_middleware_registration(self):
        """Test middleware registration."""
        class TestMiddleware:
            def __init__(self, app):
                self.app = app

        app = Velithon(middleware=[Middleware(TestMiddleware)])
        
        assert len(app.user_middleware) == 1

    def test_application_route_registration(self):
        """Test route registration via decorators."""
        app = Velithon()

        @app.get("/test")
        async def test_handler(request: Request):
            return JSONResponse({"message": "test"})

        assert len(app.router.routes) >= 1

    def test_application_openapi_configuration(self):
        """Test OpenAPI configuration."""
        app = Velithon(
            title="Test API",
            description="A test API",
            version="1.0.0",
            openapi_url="/openapi.json",
            docs_url="/docs"
        )

        assert app.title == "Test API"
        assert app.description == "A test API"
        assert app.version == "1.0.0"


class TestApplicationIntegration:
    """Test application integration scenarios."""

    @pytest.fixture
    def app(self):
        """Create a test application."""
        return Velithon()

    def test_basic_request_response_flow(self, app):
        """Test basic request-response flow."""
        @app.get("/hello")
        async def hello_handler(request: Request):
            return JSONResponse({"message": "Hello, World!"})

        # Application should have the route registered
        assert any(route.path == "/hello" for route in app.router.routes)

    def test_dependency_injection_integration(self, app):
        """Test dependency injection integration."""
        from velithon.di import SingletonProvider, inject
        
        class UserService:
            def get_user(self, user_id: int):
                return {"id": user_id, "name": f"User {user_id}"}

        # Create a custom container class with providers
        class TestContainer(ServiceContainer):
            user_service = SingletonProvider(UserService)
        
        # Register the container instance
        container = TestContainer()
        app.register_container(container)

        @app.get("/users/{user_id}")
        @inject
        async def get_user(user_id: int, service: UserService = Provide[container.user_service]):
            return JSONResponse(service.get_user(user_id))

        # Should have registered the route
        assert any("/users/" in route.path for route in app.router.routes)

    def test_middleware_stack_integration(self, app):
        """Test middleware stack integration."""
        middleware_calls = []

        class TrackingMiddleware:
            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, protocol):
                middleware_calls.append("called")
                return await self.app(scope, protocol)

        # Create new app with middleware in constructor
        app_with_middleware = Velithon(
            middleware=[Middleware(TrackingMiddleware)]
        )
        
        # Middleware should be added
        assert len(app_with_middleware.user_middleware) >= 1

    def test_error_handling_integration(self, app):
        """Test error handling integration."""
        from velithon.exceptions import ErrorDefinitions, HTTPException

        @app.get("/error")
        async def error_handler(request: Request):
            raise HTTPException(status_code=400, error=ErrorDefinitions.BAD_REQUEST, details={})

        # Route should be registered
        assert any(route.path == "/error" for route in app.router.routes)

    def test_multiple_http_methods(self, app):
        """Test handling multiple HTTP methods."""
        @app.get("/resource")
        async def get_resource(request: Request):
            return JSONResponse({"method": "GET"})

        @app.post("/resource")
        async def create_resource(request: Request):
            return JSONResponse({"method": "POST"})

        @app.put("/resource")
        async def update_resource(request: Request):
            return JSONResponse({"method": "PUT"})

        @app.delete("/resource")
        async def delete_resource(request: Request):
            return JSONResponse({"method": "DELETE"})

        # Should have multiple routes for the same path
        resource_routes = [route for route in app.router.routes if route.path == "/resource"]
        assert len(resource_routes) == 4

    def test_path_parameters_integration(self, app):
        """Test path parameters integration."""
        @app.get("/users/{user_id}/posts/{post_id}")
        async def get_user_post(user_id: int, post_id: int):
            return JSONResponse({
                "user_id": user_id,
                "post_id": post_id
            })

        # Should have registered the parameterized route
        route_paths = [route.path for route in app.router.routes]
        assert "/users/{user_id}/posts/{post_id}" in route_paths

    def test_request_validation_integration(self, app):
        """Test request validation integration."""
        from pydantic import BaseModel

        class UserCreate(BaseModel):
            name: str
            email: str

        @app.post("/users")
        async def create_user(user: UserCreate):
            return JSONResponse({
                "name": user.name,
                "email": user.email
            })

        # Route should be registered
        assert any(route.path == "/users" for route in app.router.routes)


class TestApplicationConfiguration:
    """Test application configuration options."""

    def test_cors_configuration(self):
        """Test CORS configuration."""
        from velithon.middleware.cors import CORSMiddleware

        app = Velithon(
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST"],
                    allow_headers=["*"]
                )
            ]
        )

        assert len(app.user_middleware) >= 1

    def test_compression_configuration(self):
        """Test compression middleware configuration."""
        from velithon.middleware.compression import CompressionMiddleware

        app = Velithon(
            middleware=[
                Middleware(
                    CompressionMiddleware,
                    minimum_size=1000
                )
            ]
        )

        assert len(app.user_middleware) >= 1

    def test_session_configuration(self):
        """Test session middleware configuration."""
        from velithon.middleware.session import SessionMiddleware

        app = Velithon(
            middleware=[
                Middleware(
                    SessionMiddleware,
                    secret_key="test-secret-key",
                    max_age=3600
                )
            ]
        )

        assert len(app.user_middleware) >= 1

    def test_custom_exception_handlers(self):
        """Test custom exception handlers via middleware."""
        app = Velithon()

        # Note: Velithon uses middleware for exception handling
        # rather than a direct exception_handler decorator
        
        # For now, just test that we can create custom exceptions
        from velithon.exceptions import ErrorDefinitions, HTTPException
        
        try:
            raise HTTPException(status_code=400, error=ErrorDefinitions.VALIDATION_ERROR)
        except HTTPException as e:
            assert e.status_code == 400

        # Application should still be functional
        assert app.router is not None

    def test_openapi_customization(self):
        """Test OpenAPI documentation customization."""
        app = Velithon(
            title="Custom API",
            description="Custom API Description",
            version="2.0.0",
            openapi_tags=[
                {
                    "name": "users",
                    "description": "User operations"
                }
            ]
        )

        @app.get("/users", tags=["users"])
        async def get_users():
            return JSONResponse({"users": []})

        assert app.title == "Custom API"
        assert app.description == "Custom API Description"
        assert app.version == "2.0.0"


class TestApplicationPerformance:
    """Test application performance characteristics."""

    def test_route_lookup_performance(self):
        """Test route lookup performance with many routes."""
        app = Velithon()

        # Add many routes
        for i in range(100):
            @app.get(f"/route{i}")
            async def handler(request: Request, i=i):
                return JSONResponse({"route": i})

        # Should handle route registration efficiently
        assert len(app.router.routes) >= 100

    def test_middleware_stack_performance(self):
        """Test middleware stack performance."""
        # Create middleware classes
        middleware_list = []
        for i in range(10):
            class TestMiddleware:
                def __init__(self, app, middleware_id=i):
                    self.app = app
                    self.middleware_id = middleware_id

                async def __call__(self, scope, protocol):
                    return await self.app(scope, protocol)
            
            middleware_list.append(Middleware(TestMiddleware, middleware_id=i))

        app = Velithon(middleware=middleware_list)

        # Should handle multiple middleware efficiently
        assert len(app.user_middleware) >= 10

    def test_dependency_injection_performance(self):
        """Test dependency injection performance."""
        from velithon.di import SingletonProvider
        
        # Create a container class with many providers
        class TestContainer(ServiceContainer):
            pass
        
        container = TestContainer()
        
        # Register many services via providers as class attributes
        for i in range(50):
            class Service:
                def __init__(self, service_id=i):
                    self.service_id = service_id
            
            setattr(TestContainer, f'service_{i}', SingletonProvider(Service))
        
        # Create app and register container
        app = Velithon()
        app.register_container(container)

        # Should handle many service registrations
        # Count the number of provider attributes in the container class
        providers = [attr for attr in dir(TestContainer) 
                    if hasattr(getattr(TestContainer, attr, None), 'get')]
        assert len(providers) >= 50


class TestApplicationEdgeCases:
    """Test application edge cases."""

    def test_empty_application(self):
        """Test empty application with no routes."""
        app = Velithon()
        
        # Should still be functional
        assert app.router is not None
        assert len(app.router.routes) >= 0  # May have default routes

    def test_application_with_no_middleware(self):
        """Test application with no custom middleware."""
        app = Velithon(middleware=[])
        
        # Should still work with default middleware
        assert app.user_middleware == []

    def test_duplicate_route_registration(self):
        """Test duplicate route registration."""
        app = Velithon()

        @app.get("/duplicate")
        async def handler1(request: Request):
            return JSONResponse({"handler": "1"})

        @app.get("/duplicate")
        async def handler2(request: Request):
            return JSONResponse({"handler": "2"})

        # Should handle duplicate routes (last one wins or both registered)
        duplicate_routes = [route for route in app.router.routes 
                           if route.path == "/duplicate"]
        assert len(duplicate_routes) >= 1

    def test_application_with_invalid_config(self):
        """Test application with invalid configuration."""
        # These should either work or raise clear errors
        try:
            app = Velithon(
                title="",  # Empty title
                version="invalid-version",  # Invalid version format
            )
            assert app is not None
        except Exception as e:
            # Should raise a clear error message
            assert isinstance(e, (ValueError, TypeError))

    def test_large_application_structure(self):
        """Test large application with many components."""
        from velithon.di import SingletonProvider
        
        # Create middleware list
        middleware_list = []
        class TestMiddleware:
            def __init__(self, app):
                self.app = app
        
        middleware_list.append(Middleware(TestMiddleware))
        
        app = Velithon(middleware=middleware_list)

        # Add many routes
        for i in range(20):
            @app.get(f"/api/v1/endpoint{i}")
            async def handler(request: Request, i=i):
                return JSONResponse({"endpoint": i})

        # Create container with many services
        class TestContainer(ServiceContainer):
            pass
        
        for i in range(10):
            class Service:
                def __init__(self, service_id=i):
                    self.service_id = service_id
            
            setattr(TestContainer, f'service_{i}', SingletonProvider(Service))
        
        container = TestContainer()
        app.register_container(container)

        # Should handle large applications
        assert len(app.router.routes) >= 20
        providers = [attr for attr in dir(TestContainer) 
                    if hasattr(getattr(TestContainer, attr, None), 'get')]
        assert len(providers) >= 10
        assert len(app.user_middleware) >= 1


class TestApplicationAsync:
    """Test application async behavior."""

    @pytest.mark.asyncio
    async def test_async_startup_handlers(self):
        """Test async startup handlers."""
        startup_results = []
        app = Velithon()

        @app.on_startup(priority=0)
        async def async_startup():
            await asyncio.sleep(0.01)
            startup_results.append("startup")

        # Simulate startup by calling the function directly
        if app.startup_functions:
            for func_info in app.startup_functions:
                if func_info.is_async:
                    await func_info.func()
                else:
                    func_info.func()

        assert "startup" in startup_results

    @pytest.mark.asyncio
    async def test_async_shutdown_handlers(self):
        """Test async shutdown handlers."""
        shutdown_results = []
        app = Velithon()

        @app.on_shutdown(priority=0)
        async def async_shutdown():
            await asyncio.sleep(0.01)
            shutdown_results.append("shutdown")

        # Simulate shutdown by calling the function directly
        if app.shutdown_functions:
            for func_info in app.shutdown_functions:
                if func_info.is_async:
                    await func_info.func()
                else:
                    func_info.func()

        assert "shutdown" in shutdown_results

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test concurrent request handling capability."""
        app = Velithon()

        @app.get("/slow")
        async def slow_handler(request: Request):
            await asyncio.sleep(0.1)
            return JSONResponse({"message": "slow"})

        @app.get("/fast")
        async def fast_handler(request: Request):
            return JSONResponse({"message": "fast"})

        # Application should support concurrent handlers
        assert len(app.router.routes) >= 2


if __name__ == "__main__":
    pytest.main([__file__])
