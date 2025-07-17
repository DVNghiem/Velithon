"""Tests for Prometheus metrics middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from velithon.datastructures import Protocol, Scope
from velithon.middleware.prometheus import (
    PrometheusMiddleware,
    PrometheusMetrics,
    FastPrometheusMiddleware,
)
from velithon.responses import JSONResponse


class TestPrometheusMetrics:
    """Test the PrometheusMetrics collector."""

    def test_metrics_initialization(self):
        """Test that metrics are properly initialized."""
        metrics = PrometheusMetrics()

        assert metrics._active_requests == 0
        assert len(metrics._request_count) == 0
        assert len(metrics._request_duration) == 0
        assert metrics._app_start_time > 0

    def test_request_count_tracking(self):
        """Test request count tracking."""
        metrics = PrometheusMetrics()

        metrics.inc_request_count('GET', '/users', 200)
        metrics.inc_request_count('GET', '/users', 200)
        metrics.inc_request_count('GET', '/users', 404)

        assert metrics._request_count['GET:/users:200'] == 2
        assert metrics._request_count['GET:/users:404'] == 1

    def test_active_requests_tracking(self):
        """Test active requests counter."""
        metrics = PrometheusMetrics()

        metrics.inc_active_requests()
        assert metrics._active_requests == 1

        metrics.inc_active_requests()
        assert metrics._active_requests == 2

        metrics.dec_active_requests()
        assert metrics._active_requests == 1

        # Test that it doesn't go below 0
        metrics.dec_active_requests()
        metrics.dec_active_requests()
        assert metrics._active_requests == 0

    def test_duration_recording(self):
        """Test request duration recording."""
        metrics = PrometheusMetrics()

        metrics.record_request_duration('GET', '/users', 0.5)
        metrics.record_request_duration('GET', '/users', 0.3)

        durations = metrics._request_duration['GET:/users']
        assert len(durations) == 2
        assert 0.5 in durations
        assert 0.3 in durations

    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics text format generation."""
        metrics = PrometheusMetrics()

        # Add some test data
        metrics.inc_request_count('GET', '/users', 200)
        metrics.inc_request_count('POST', '/users', 201)
        metrics.record_request_duration('GET', '/users', 0.1)
        metrics.record_request_size('POST', '/users', 100)
        metrics.record_response_size('GET', '/users', 200)
        metrics.inc_active_requests()

        output = metrics.get_prometheus_metrics()

        # Check that all expected metric types are present
        assert 'http_requests_total' in output
        assert 'http_request_duration_seconds' in output
        assert 'http_request_size_bytes' in output
        assert 'http_response_size_bytes' in output
        assert 'http_requests_active' in output
        assert 'app_uptime_seconds' in output

        # Check specific metric values
        assert 'method="GET",path="/users",status_code="200"' in output
        assert 'method="POST",path="/users",status_code="201"' in output
        assert 'http_requests_active 1' in output


class TestPrometheusMiddleware:
    """Test the PrometheusMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock RSGI application."""
        return AsyncMock()

    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope."""
        scope = MagicMock()
        scope.path = '/users/123'
        scope.method = 'GET'
        scope.headers = {'content-length': '100'}
        return scope

    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol."""
        protocol = MagicMock()
        protocol.send = AsyncMock()
        return protocol

    def test_middleware_initialization(self, mock_app):
        """Test middleware initialization with default parameters."""
        middleware = PrometheusMiddleware(mock_app)

        assert middleware.metrics_path == '/metrics'
        assert middleware.collect_request_size is True
        assert middleware.collect_response_size is True
        assert middleware.exclude_paths == []

    def test_middleware_with_custom_config(self, mock_app):
        """Test middleware initialization with custom configuration."""
        middleware = PrometheusMiddleware(
            mock_app,
            metrics_path='/custom-metrics',
            collect_request_size=False,
            exclude_paths=['/health', '/ping'],
        )

        assert middleware.metrics_path == '/custom-metrics'
        assert middleware.collect_request_size is False
        assert middleware.exclude_paths == ['/health', '/ping']

    def test_path_normalization(self, mock_app):
        """Test default path normalization."""
        middleware = PrometheusMiddleware(mock_app)

        # Test numeric ID replacement
        assert middleware._default_path_normalizer('/users/123') == '/users/{id}'
        assert (
            middleware._default_path_normalizer('/posts/456/comments/789')
            == '/posts/{id}/comments/{id}'
        )

        # Test UUID replacement
        uuid_path = '/users/550e8400-e29b-41d4-a716-446655440000'
        expected = '/users/{uuid}'
        assert middleware._default_path_normalizer(uuid_path) == expected

    def test_should_collect_metrics(self, mock_app):
        """Test metrics collection filtering."""
        middleware = PrometheusMiddleware(
            mock_app, exclude_paths=['/health', '/metrics']
        )

        assert middleware._should_collect_metrics('/users') is True
        assert middleware._should_collect_metrics('/health') is False
        assert middleware._should_collect_metrics('/metrics') is False

    def test_request_size_extraction(self, mock_app, mock_scope):
        """Test request size extraction from headers."""
        middleware = PrometheusMiddleware(mock_app)

        # Test with valid content-length
        mock_scope.headers = {'content-length': '150'}
        assert middleware._get_request_size(mock_scope) == 150

        # Test with invalid content-length
        mock_scope.headers = {'content-length': 'invalid'}
        assert middleware._get_request_size(mock_scope) == 0

        # Test with missing content-length
        mock_scope.headers = {}
        assert middleware._get_request_size(mock_scope) == 0

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, mock_app, mock_protocol):
        """Test that metrics endpoint returns Prometheus data."""
        middleware = PrometheusMiddleware(mock_app)

        # Create scope for metrics endpoint
        scope = MagicMock()
        scope.path = '/metrics'
        scope.method = 'GET'

        # Add some test metrics
        middleware.metrics.inc_request_count('GET', '/users', 200)

        # Process request
        await middleware.process_http_request(scope, mock_protocol)

        # Verify that the app was not called (metrics handled directly)
        mock_app.assert_not_called()

    @pytest.mark.asyncio
    async def test_excluded_path_handling(self, mock_app, mock_protocol):
        """Test that excluded paths don't collect metrics."""
        middleware = PrometheusMiddleware(mock_app, exclude_paths=['/health'])

        scope = MagicMock()
        scope.path = '/health'
        scope.method = 'GET'

        initial_count = len(middleware.metrics._request_count)

        await middleware.process_http_request(scope, mock_protocol)

        # Verify app was called but no metrics collected
        mock_app.assert_called_once()
        assert len(middleware.metrics._request_count) == initial_count

    @pytest.mark.asyncio
    async def test_successful_request_metrics(
        self, mock_app, mock_scope, mock_protocol
    ):
        """Test metrics collection for successful requests."""
        middleware = PrometheusMiddleware(mock_app)

        # Mock successful response
        mock_protocol.send.side_effect = [
            None,  # First call for response start
            None,  # Second call for response body
        ]

        await middleware.process_http_request(mock_scope, mock_protocol)

        # Verify metrics were recorded
        assert len(middleware.metrics._request_count) > 0
        assert len(middleware.metrics._request_duration) > 0


class TestFastPrometheusMiddleware:
    """Test the FastPrometheusMiddleware optimizations."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock RSGI application."""
        return AsyncMock()

    def test_fast_middleware_initialization(self, mock_app):
        """Test fast middleware initialization."""
        middleware = FastPrometheusMiddleware(mock_app)

        assert hasattr(middleware, '_metric_cache')
        assert hasattr(middleware, '_last_cleanup')
        assert hasattr(middleware, '_cleanup_interval')
        assert middleware._cleanup_interval == 300

    def test_cleanup_old_metrics(self, mock_app):
        """Test metric cleanup functionality."""
        middleware = FastPrometheusMiddleware(mock_app)

        # Add many durations to trigger cleanup
        key = 'GET:/test'
        middleware.metrics._request_duration[key] = list(range(1500))

        # Force cleanup by setting old timestamp
        middleware._last_cleanup = 0

        middleware._cleanup_old_metrics()

        # Verify cleanup occurred
        assert len(middleware.metrics._request_duration[key]) == 1000
        assert middleware._last_cleanup > 0


if __name__ == '__main__':
    pytest.main([__file__])
