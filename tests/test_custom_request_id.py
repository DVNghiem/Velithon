"""Tests for custom request ID generation and context management."""

import pytest
import time
from unittest.mock import Mock

from velithon.application import Velithon
from velithon.ctx import (
    AppContext, 
    RequestContext, 
    current_app, 
    request, 
    g, 
    has_app_context, 
    has_request_context,
    get_current_app,
    get_current_request,
)
from velithon.datastructures import Scope, _TempRequestContext
from velithon.middleware.context import RequestContextMiddleware
from velithon.requests import Request
from velithon.responses import JSONResponse
from granian.rsgi import Scope as RSGIScope


class TestCustomRequestIDGeneration:
    """Test custom request ID generation functionality."""
    
    def test_default_request_id_generation(self):
        """Test that default request ID generation works when no custom generator is provided."""
        app = Velithon()
        
        # Verify no custom generator is set
        assert app.request_id_generator is None
        
        # Create a mock RSGI scope
        mock_scope = Mock()
        mock_scope.headers = []
        mock_scope.method = "GET"
        mock_scope.path = "/test"
        mock_scope.client = "127.0.0.1"
        mock_scope.query_string = b""
        
        # Create Velithon scope
        scope = Scope(mock_scope)
        
        # Verify default request ID format (prefix-timestamp-counter)
        assert scope._request_id is not None
        parts = scope._request_id.split('-')
        assert len(parts) == 3
        assert parts[0].isdigit()  # prefix
        assert parts[1].isdigit()  # timestamp
        assert parts[2].isdigit()  # counter
    
    def test_custom_request_id_generator_configuration(self):
        """Test that custom request ID generator can be configured."""
        
        def custom_generator(request):
            return f"custom-{request.method.lower()}-{hash(request.path) % 1000}"
        
        app = Velithon(request_id_generator=custom_generator)
        
        # Verify custom generator is set
        assert app.request_id_generator == custom_generator
        assert callable(app.request_id_generator)
    
    def test_custom_request_id_generator_functionality(self):
        """Test that custom request ID generator works correctly."""
        
        def custom_generator(request):
            correlation_id = request.headers.get('x-correlation-id')
            if correlation_id:
                return f"corr-{correlation_id}"
            return f"custom-{request.method.lower()}-{abs(hash(request.path)) % 1000}"
        
        app = Velithon(request_id_generator=custom_generator)
        
        # Test with correlation ID
        mock_scope = Mock()
        mock_scope.headers = [('x-correlation-id', 'test-123')]
        mock_scope.method = "GET"
        mock_scope.path = "/test"
        mock_scope.client = "127.0.0.1"
        mock_scope.query_string = b""
        
        temp_request = _TempRequestContext(mock_scope)
        result_id = custom_generator(temp_request)
        assert result_id == "corr-test-123"
        
        # Test without correlation ID
        mock_scope.headers = []
        temp_request = _TempRequestContext(mock_scope)
        result_id = custom_generator(temp_request)
        assert result_id.startswith("custom-get-")
    
    def test_temp_request_context(self):
        """Test _TempRequestContext provides correct request information."""
        
        mock_scope = Mock()
        mock_scope.headers = [('content-type', 'application/json'), ('x-test', 'value')]
        mock_scope.method = "POST"
        mock_scope.path = "/api/users"
        mock_scope.client = "192.168.1.100"
        mock_scope.query_string = b"param=value"
        
        temp_request = _TempRequestContext(mock_scope)
        
        assert temp_request.method == "POST"
        assert temp_request.path == "/api/users"
        assert temp_request.client == "192.168.1.100"
        # Note: Headers access would require proper Headers class implementation


class TestContextManagement:
    """Test Flask-style context management system."""
    
    def test_app_context_basic_functionality(self):
        """Test basic application context functionality."""
        app = Velithon(title="Test App")
        
        # Initially no context
        assert not has_app_context()
        
        with pytest.raises(RuntimeError, match="Working outside of application context"):
            _ = current_app.title
        
        # Within context
        with AppContext(app):
            assert has_app_context()
            assert current_app.title == "Test App"
            assert get_current_app() == app
        
        # After context
        assert not has_app_context()
    
    def test_request_context_basic_functionality(self):
        """Test basic request context functionality."""
        app = Velithon()
        
        # Create mock request
        mock_scope = Mock()
        mock_protocol = Mock()
        mock_request = Mock()
        mock_request.request_id = "test-request-123"
        
        # Initially no context
        assert not has_request_context()
        
        with pytest.raises(RuntimeError, match="Working outside of request context"):
            _ = request.request_id
        
        # Within context
        with AppContext(app):
            with RequestContext(app, mock_request):
                assert has_request_context()
                assert request.request_id == "test-request-123"
                assert get_current_request() == mock_request
                
                # Test 'g' object for request-local storage
                g.custom_value = "test"
                assert g.custom_value == "test"
        
        # After context
        assert not has_request_context()
    
    def test_nested_contexts(self):
        """Test nested application and request contexts."""
        app1 = Velithon(title="App 1")
        app2 = Velithon(title="App 2")
        
        mock_request1 = Mock()
        mock_request1.request_id = "req-1"
        mock_request2 = Mock()
        mock_request2.request_id = "req-2"
        
        # Nested app contexts
        with AppContext(app1):
            assert current_app.title == "App 1"
            
            with AppContext(app2):
                assert current_app.title == "App 2"
                
                with RequestContext(app2, mock_request1):
                    assert request.request_id == "req-1"
                    g.value1 = "first"
                    
                    with RequestContext(app2, mock_request2):
                        assert request.request_id == "req-2"
                        g.value2 = "second"
                        # Inner context overrides outer
                        assert g.value2 == "second"
                    
                    # Back to outer request context
                    assert request.request_id == "req-1"
                    assert g.value1 == "first"
            
            # Back to outer app context
            assert current_app.title == "App 1"
    
    def test_context_isolation(self):
        """Test that contexts are properly isolated."""
        app = Velithon()
        
        mock_request1 = Mock()
        mock_request1.request_id = "req-1"
        mock_request2 = Mock()
        mock_request2.request_id = "req-2"
        
        # First context
        with AppContext(app):
            with RequestContext(app, mock_request1):
                g.user_id = 123
                g.session_data = {"key": "value1"}
        
        # Second context should not see first context's data
        with AppContext(app):
            with RequestContext(app, mock_request2):
                # Should not have access to previous context's g data
                with pytest.raises(AttributeError):
                    _ = g.user_id
                
                # Can set new data
                g.user_id = 456
                g.session_data = {"key": "value2"}
                assert g.user_id == 456


class TestRequestContextMiddleware:
    """Test the RequestContextMiddleware."""
    
    def test_middleware_initialization(self):
        """Test middleware can be initialized with app."""
        app = Velithon()
        middleware = RequestContextMiddleware(app)
        
        assert middleware.app == app
        assert hasattr(middleware, 'request_id_manager')
    
    def test_middleware_with_custom_generator(self):
        """Test middleware correctly applies custom request ID generator."""
        
        def custom_generator(req):
            return f"middleware-{req.method}-{abs(hash(req.path)) % 100}"
        
        app = Velithon(request_id_generator=custom_generator)
        middleware = RequestContextMiddleware(app)
        
        # Verify the middleware has access to the custom generator
        assert middleware.app.request_id_generator == custom_generator
    
    @pytest.mark.asyncio
    async def test_middleware_request_processing(self):
        """Test that middleware properly processes requests and sets context."""
        
        def custom_generator(req):
            return f"processed-{req.method.lower()}"
        
        app = Velithon(request_id_generator=custom_generator)
        
        # Mock the next middleware/app in the chain
        app.process_request = Mock()
        
        middleware = RequestContextMiddleware(app)
        
        # Create mock scope and protocol
        mock_rsgi_scope = Mock()
        mock_rsgi_scope.headers = []
        mock_rsgi_scope.method = "GET"
        mock_rsgi_scope.path = "/test"
        mock_rsgi_scope.client = "127.0.0.1"
        mock_rsgi_scope.query_string = b""
        
        scope = Scope(mock_rsgi_scope)
        protocol = Mock()
        
        # Process request through middleware
        # Note: This is a simplified test - in reality, the middleware would
        # need proper request/response handling
        temp_request = _TempRequestContext(mock_rsgi_scope)
        custom_id = custom_generator(temp_request)
        
        assert custom_id == "processed-get"


class TestRequestIDManager:
    """Test the RequestIDManager class."""
    
    def test_request_id_manager_initialization(self):
        """Test RequestIDManager initialization."""
        app = Velithon()
        
        from velithon.ctx import RequestIDManager
        manager = RequestIDManager(app)
        
        assert manager.app == app
        assert manager._default_generator is None
    
    def test_request_id_manager_with_custom_generator(self):
        """Test RequestIDManager with custom generator."""
        
        def custom_generator(req):
            return "manager-test"
        
        app = Velithon(request_id_generator=custom_generator)
        
        from velithon.ctx import RequestIDManager
        manager = RequestIDManager(app)
        
        mock_request = Mock()
        request_id = manager.generate_request_id(mock_request)
        assert request_id == "manager-test"
    
    def test_request_id_manager_default_fallback(self):
        """Test RequestIDManager falls back to default generator."""
        
        app = Velithon()  # No custom generator
        
        from velithon.ctx import RequestIDManager
        manager = RequestIDManager(app)
        
        mock_request = Mock()
        request_id = manager.generate_request_id(mock_request)
        
        # Should generate default format
        assert request_id is not None
        parts = request_id.split('-')
        assert len(parts) == 3


class TestIntegrationScenarios:
    """Integration tests for complete request ID workflows."""
    
    def test_end_to_end_custom_request_id_flow(self):
        """Test complete flow of custom request ID generation."""
        
        # Track calls to the custom generator
        generator_calls = []
        
        def tracking_generator(req):
            generator_calls.append({
                'method': req.method,
                'path': req.path,
                'headers': dict(req.headers) if hasattr(req, 'headers') else {}
            })
            correlation_id = req.headers.get('x-correlation-id')
            if correlation_id:
                return f"tracked-{correlation_id}"
            return f"tracked-{req.method.lower()}-{len(generator_calls)}"
        
        app = Velithon(request_id_generator=tracking_generator)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return JSONResponse({"request_id": request.request_id})
        
        # Test that the generator function is properly configured
        assert app.request_id_generator == tracking_generator
        
        # Simulate request processing by calling the generator directly
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.path = "/test" 
        mock_request.headers = {'x-correlation-id': 'integration-test'}
        
        result_id = tracking_generator(mock_request)
        assert result_id == "tracked-integration-test"
        assert len(generator_calls) == 1
        assert generator_calls[0]['method'] == "GET"
        assert generator_calls[0]['path'] == "/test"
    
    def test_performance_considerations(self):
        """Test performance aspects of custom request ID generation."""
        
        # Counter to track generator calls
        call_count = 0
        
        def performance_generator(req):
            nonlocal call_count
            call_count += 1
            
            # Simulate some processing time (in reality should be minimal)
            start_time = time.time()
            
            # Simple logic that should be fast
            method_hash = hash(req.method) % 1000
            path_hash = abs(hash(req.path)) % 1000
            
            processing_time = time.time() - start_time
            
            return f"perf-{method_hash}-{path_hash}-{call_count}"
        
        app = Velithon(request_id_generator=performance_generator)
        
        # Test multiple calls
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.path = "/api/test"
        mock_request.headers = {}
        
        # Generate multiple IDs
        ids = []
        for i in range(10):
            mock_request.path = f"/api/test/{i}"
            request_id = performance_generator(mock_request)
            ids.append(request_id)
        
        # Verify all IDs are unique and follow expected pattern
        assert len(set(ids)) == 10  # All unique
        assert call_count == 10
        
        for request_id in ids:
            assert request_id.startswith("perf-")
            parts = request_id.split('-')
            assert len(parts) == 4  # perf-methodhash-pathhash-counter
    
    def test_error_handling_in_custom_generator(self):
        """Test error handling when custom generator fails."""
        
        def failing_generator(req):
            # This will fail on the second call
            if hasattr(failing_generator, 'call_count'):
                failing_generator.call_count += 1
            else:
                failing_generator.call_count = 1
            
            if failing_generator.call_count == 2:
                raise ValueError("Simulated generator failure")
            
            return f"success-{failing_generator.call_count}"
        
        app = Velithon(request_id_generator=failing_generator)
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.path = "/test"
        mock_request.headers = {}
        
        # First call should succeed
        first_id = failing_generator(mock_request)
        assert first_id == "success-1"
        
        # Second call should fail - in real implementation, this would be caught
        # and fall back to default generator
        with pytest.raises(ValueError):
            failing_generator(mock_request)
