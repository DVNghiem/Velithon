"""
Tests for error handling and exception management in Velithon.
"""
import asyncio
from unittest.mock import MagicMock

import pytest

from velithon.exceptions import HTTPException
from velithon.middleware.logging import LoggingMiddleware
from velithon.responses import JSONResponse, PlainTextResponse


class CustomHTTPException(HTTPException):
    """Custom HTTP exception for testing."""
    
    def __init__(self, status_code: int = 400, detail: str = "Custom error"):
        from velithon.exceptions.errors import ErrorDefinitions
        super().__init__(status_code=status_code, error=ErrorDefinitions.VALIDATION_ERROR)
        self.details = {"message": detail}
        self.custom_field = "test_value"
    
    def to_dict(self):
        return {
            "message": self.details.get("message"),
            "error_code": "CUSTOM_ERROR",
            "custom_field": self.custom_field,
            "status": self.status_code
        }


class TestHTTPException:
    """Test HTTPException class."""
    
    def test_http_exception_creation(self):
        """Test basic HTTPException creation."""
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=404, error=ErrorDefinitions.NOT_FOUND)
        
        assert exc.status_code == 404
        assert exc.error is not None
    
    def test_http_exception_default_values(self):
        """Test HTTPException with default values."""
        exc = HTTPException()
        
        assert exc.status_code == 400  # Default is 400, not 500
        assert hasattr(exc, 'error')
    
    def test_http_exception_to_dict(self):
        """Test HTTPException to_dict method."""
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=400, error=ErrorDefinitions.BAD_REQUEST)
        result = exc.to_dict()
        
        assert isinstance(result, dict)
        assert 'error' in result
    
    def test_http_exception_str_representation(self):
        """Test HTTPException string representation."""
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=403, error=ErrorDefinitions.FORBIDDEN)
        
        str_repr = str(exc)
        assert isinstance(str_repr, str)
    
    def test_custom_http_exception(self):
        """Test custom HTTPException subclass."""
        from velithon.exceptions.errors import ErrorDefinitions
        
        class CustomHTTPException(HTTPException):
            def __init__(self, status_code: int, detail: str):
                super().__init__(status_code=status_code, error=ErrorDefinitions.VALIDATION_ERROR)
                self.details = {"message": detail}
                self.custom_field = "test_value"
                
            def to_dict(self):
                return {
                    "message": self.details.get("message"),
                    "error_code": "CUSTOM_ERROR",
                    "custom_field": self.custom_field,
                    "status": self.status_code
                }
        
        exc = CustomHTTPException(status_code=422, detail="Validation error")
        
        assert exc.status_code == 422
        assert exc.details["message"] == "Validation error"
        assert exc.custom_field == "test_value"
        
        result = exc.to_dict()
        assert result["error_code"] == "CUSTOM_ERROR"
        assert result["custom_field"] == "test_value"


class TestErrorHandlingMiddleware:
    """Test error handling in middleware."""
    
    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol."""
        protocol = MagicMock()
        protocol.response_bytes = MagicMock()
        return protocol
    
    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.path = "/test"
        scope.client = "127.0.0.1"
        scope.headers = MagicMock()
        scope.headers.get.return_value = "test-agent"
        scope._request_id = "test-request-123"
        return scope
    
    @pytest.mark.asyncio
    async def test_logging_middleware_http_exception(self, mock_scope, mock_protocol):
        """Test logging middleware handling HTTPException."""
        async def failing_app(scope, protocol):
            from velithon.exceptions.errors import ErrorDefinitions
            raise HTTPException(status_code=404, error=ErrorDefinitions.NOT_FOUND)
        
        middleware = LoggingMiddleware(failing_app)
        
        await middleware(mock_scope, mock_protocol)
        
        # Should have called response_bytes with error response
        mock_protocol.response_bytes.assert_called_once()
        args = mock_protocol.response_bytes.call_args[0]
        assert args[0] == 404  # status code
    
    @pytest.mark.asyncio
    async def test_logging_middleware_generic_exception(self, mock_scope, mock_protocol):
        """Test logging middleware handling generic exceptions."""
        async def failing_app(scope, protocol):
            raise ValueError("Something went wrong")
        
        middleware = LoggingMiddleware(failing_app)
        
        await middleware(mock_scope, mock_protocol)
        
        # Should have called response_bytes with 500 error
        mock_protocol.response_bytes.assert_called_once()
        args = mock_protocol.response_bytes.call_args[0]
        assert args[0] == 500  # status code
    
    @pytest.mark.asyncio
    async def test_logging_middleware_custom_http_exception(self, mock_scope, mock_protocol):
        """Test logging middleware handling custom HTTPException."""
        async def failing_app(scope, protocol):
            raise CustomHTTPException(status_code=422, detail="Validation failed")
        
        middleware = LoggingMiddleware(failing_app)
        
        await middleware(mock_scope, mock_protocol)
        
        # Should have called response_bytes with custom error
        mock_protocol.response_bytes.assert_called_once()
        args = mock_protocol.response_bytes.call_args[0]
        assert args[0] == 422  # status code


class TestErrorResponseGeneration:
    """Test error response generation."""
    
    def test_json_error_response_creation(self):
        """Test creating JSON error responses."""
        error_data = {
            "message": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "details": ["Field 'email' is required"]
        }
        
        response = JSONResponse(content=error_data, status_code=400)
        
        assert response.status_code == 400
        assert response.media_type == "application/json"
    
    def test_plain_text_error_response_creation(self):
        """Test creating plain text error responses."""
        response = PlainTextResponse("Internal Server Error", status_code=500)
        
        assert response.status_code == 500
        assert response.media_type == "text/plain"  # No charset in the actual implementation
        assert response.body == b"Internal Server Error"


class MockEndpoint:
    """Mock endpoint for testing error scenarios."""
    
    def __init__(self, exception_to_raise=None):
        self.exception_to_raise = exception_to_raise
        self.call_count = 0
    
    async def __call__(self, scope, protocol):
        self.call_count += 1
        if self.exception_to_raise:
            raise self.exception_to_raise
        
        response = JSONResponse({"message": "success"})
        await response(scope, protocol)


class TestEndpointErrorHandling:
    """Test error handling in endpoints."""
    
    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.path = "/test"
        return scope
    
    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol."""
        protocol = MagicMock()
        protocol.response_bytes = MagicMock()
        return protocol
    
    @pytest.mark.asyncio
    async def test_endpoint_http_exception_propagation(self, mock_scope, mock_protocol):
        """Test that HTTPExceptions are properly propagated from endpoints."""
        from velithon.exceptions.errors import ErrorDefinitions
        endpoint = MockEndpoint(HTTPException(status_code=401, error=ErrorDefinitions.UNAUTHORIZED))
        
        with pytest.raises(HTTPException) as exc_info:
            await endpoint(mock_scope, mock_protocol)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_endpoint_generic_exception_propagation(self, mock_scope, mock_protocol):
        """Test that generic exceptions are properly propagated from endpoints."""
        endpoint = MockEndpoint(ValueError("Invalid input"))
        
        with pytest.raises(ValueError) as exc_info:
            await endpoint(mock_scope, mock_protocol)
        
        assert str(exc_info.value) == "Invalid input"
    
    @pytest.mark.asyncio
    async def test_endpoint_success_case(self, mock_scope, mock_protocol):
        """Test successful endpoint execution."""
        endpoint = MockEndpoint()
        
        await endpoint(mock_scope, mock_protocol)
        
        assert endpoint.call_count == 1


class TestAsyncErrorHandling:
    """Test error handling in async contexts."""
    
    @pytest.mark.asyncio
    async def test_asyncio_cancellation_handling(self):
        """Test handling of asyncio.CancelledError."""
        async def cancellable_operation():
            await asyncio.sleep(1)
            return "completed"
        
        task = asyncio.create_task(cancellable_operation())
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task
    
    @pytest.mark.asyncio
    async def test_asyncio_timeout_error(self):
        """Test handling of asyncio.TimeoutError."""
        async def slow_operation():
            await asyncio.sleep(2)
            return "completed"
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.5)
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_errors(self):
        """Test handling multiple concurrent errors."""
        async def failing_task(delay, error_msg):
            await asyncio.sleep(delay)
            raise ValueError(error_msg)
        
        tasks = [
            asyncio.create_task(failing_task(0.1, "Error 1")),
            asyncio.create_task(failing_task(0.2, "Error 2")),
            asyncio.create_task(failing_task(0.3, "Error 3"))
        ]
        
        # Wait for all tasks and collect exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == 3
        assert all(isinstance(result, ValueError) for result in results)
        assert str(results[0]) == "Error 1"
        assert str(results[1]) == "Error 2"
        assert str(results[2]) == "Error 3"


class TestErrorHandlingEdgeCases:
    """Test edge cases in error handling."""
    
    def test_empty_error_message(self):
        """Test handling of empty error messages."""
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=400, error=ErrorDefinitions.BAD_REQUEST, details={"message": ""})
        
        assert exc.status_code == 400
        assert exc.details.get("message") == ""
    
    def test_none_error_detail(self):
        """Test handling of None error detail."""
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=500, error=ErrorDefinitions.INTERNAL_ERROR, details=None)
        
        assert exc.status_code == 500
        assert exc.details is None or exc.details == {}
    
    def test_unicode_error_messages(self):
        """Test handling of Unicode error messages."""
        unicode_msg = "Errör with spëcial charactërs: 测试"
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=400, error=ErrorDefinitions.BAD_REQUEST, details={"message": unicode_msg})
        
        assert exc.status_code == 400
        assert exc.details.get("message") == unicode_msg
    
    def test_very_long_error_message(self):
        """Test handling of very long error messages."""
        long_msg = "A" * 10000  # 10KB message
        from velithon.exceptions.errors import ErrorDefinitions
        exc = HTTPException(status_code=400, error=ErrorDefinitions.BAD_REQUEST, details={"message": long_msg})
        
        assert exc.status_code == 400
        assert exc.details.get("message") == long_msg
        assert len(exc.details.get("message")) == 10000
    
    def test_nested_exception_chaining(self):
        """Test exception chaining and cause tracking."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                from velithon.exceptions.errors import ErrorDefinitions
                raise HTTPException(status_code=500, error=ErrorDefinitions.INTERNAL_ERROR, details={"message": "Wrapped error"}) from e
        except HTTPException as exc:
            assert exc.status_code == 500
            assert exc.details.get("message") == "Wrapped error"
            assert isinstance(exc.__cause__, ValueError)
            assert str(exc.__cause__) == "Original error"


class TestStatusCodeValidation:
    """Test HTTP status code validation and handling."""
    
    def test_valid_status_codes(self):
        """Test various valid HTTP status codes."""
        valid_codes = [200, 201, 301, 400, 401, 403, 404, 422, 500, 502, 503]
        from velithon.exceptions.errors import ErrorDefinitions
        
        for code in valid_codes:
            exc = HTTPException(status_code=code, error=ErrorDefinitions.BAD_REQUEST)
            assert exc.status_code == code
    
    def test_custom_status_codes(self):
        """Test custom/non-standard status codes."""
        custom_codes = [299, 399, 499, 599]
        from velithon.exceptions.errors import ErrorDefinitions
        
        for code in custom_codes:
            exc = HTTPException(status_code=code, error=ErrorDefinitions.BAD_REQUEST)
            assert exc.status_code == code
    
    def test_invalid_status_codes_handled_gracefully(self):
        """Test that invalid status codes are handled gracefully."""
        # These should still work, even if not standard
        invalid_codes = [0, 99, 1000, -1]
        from velithon.exceptions.errors import ErrorDefinitions
        
        for code in invalid_codes:
            exc = HTTPException(status_code=code, error=ErrorDefinitions.BAD_REQUEST)
            assert exc.status_code == code


if __name__ == "__main__":
    pytest.main([__file__])
