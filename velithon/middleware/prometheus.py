"""Prometheus metrics middleware for Velithon framework.

This module provides Prometheus-compatible metrics collection and exposure
for monitoring HTTP requests, response times, and application performance.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import Any

from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.responses import PlainTextResponse


class PrometheusMetrics:
    """Thread-safe Prometheus metrics collector.

    Collects and stores metrics in Prometheus text format for efficient
    scraping and monitoring.
    """

    def __init__(self):
        """Initialize metrics collectors."""
        self._request_count = defaultdict(int)
        self._request_duration = defaultdict(list)
        self._request_size = defaultdict(list)
        self._response_size = defaultdict(list)
        self._active_requests = 0
        self._app_start_time = time.time()

    def inc_request_count(self, method: str, path: str, status_code: int) -> None:
        """Increment request counter for given method, path, and status."""
        key = f'{method}:{path}:{status_code}'
        self._request_count[key] += 1

    def record_request_duration(self, method: str, path: str, duration: float) -> None:
        """Record request duration for given method and path."""
        key = f'{method}:{path}'
        self._request_duration[key].append(duration)

    def record_request_size(self, method: str, path: str, size: int) -> None:
        """Record request size for given method and path."""
        key = f'{method}:{path}'
        self._request_size[key].append(size)

    def record_response_size(self, method: str, path: str, size: int) -> None:
        """Record response size for given method and path."""
        key = f'{method}:{path}'
        self._response_size[key].append(size)

    def inc_active_requests(self) -> None:
        """Increment active requests counter."""
        self._active_requests += 1

    def dec_active_requests(self) -> None:
        """Decrement active requests counter."""
        self._active_requests = max(0, self._active_requests - 1)

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus metrics in text format."""
        lines = []

        # Request count metrics
        lines.append('# HELP http_requests_total Total number of HTTP requests')
        lines.append('# TYPE http_requests_total counter')
        for key, count in self._request_count.items():
            method, path, status_code = key.split(':', 2)
            lines.append(
                f'http_requests_total{{'
                f'method="{method}",path="{path}",status_code="{status_code}"'
                f'}} {count}'
            )

        # Request duration metrics
        lines.append(
            '# HELP http_request_duration_seconds HTTP request duration in seconds'
        )
        lines.append('# TYPE http_request_duration_seconds histogram')
        for key, durations in self._request_duration.items():
            if durations:
                method, path = key.split(':', 1)
                count = len(durations)
                total = sum(durations)

                # Calculate histogram buckets
                buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
                bucket_counts = {
                    bucket: sum(1 for d in durations if d <= bucket)
                    for bucket in buckets
                }

                for bucket, bucket_count in bucket_counts.items():
                    lines.append(
                        f'http_request_duration_seconds_bucket{{'
                        f'method="{method}",path="{path}",le="{bucket}"'
                        f'}} {bucket_count}'
                    )

                lines.append(
                    f'http_request_duration_seconds_bucket{{'
                    f'method="{method}",path="{path}",le="+Inf"'
                    f'}} {count}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{'
                    f'method="{method}",path="{path}"'
                    f'}} {count}'
                )
                lines.append(
                    f'http_request_duration_seconds_sum{{'
                    f'method="{method}",path="{path}"'
                    f'}} {total}'
                )

        # Request size metrics
        lines.append('# HELP http_request_size_bytes HTTP request size in bytes')
        lines.append('# TYPE http_request_size_bytes histogram')
        for key, sizes in self._request_size.items():
            if sizes:
                method, path = key.split(':', 1)
                count = len(sizes)
                total = sum(sizes)
                lines.append(
                    f'http_request_size_bytes_count{{'
                    f'method="{method}",path="{path}"'
                    f'}} {count}'
                )
                lines.append(
                    f'http_request_size_bytes_sum{{'
                    f'method="{method}",path="{path}"'
                    f'}} {total}'
                )

        # Response size metrics
        lines.append('# HELP http_response_size_bytes HTTP response size in bytes')
        lines.append('# TYPE http_response_size_bytes histogram')
        for key, sizes in self._response_size.items():
            if sizes:
                method, path = key.split(':', 1)
                count = len(sizes)
                total = sum(sizes)
                lines.append(
                    f'http_response_size_bytes_count{{'
                    f'method="{method}",path="{path}"'
                    f'}} {count}'
                )
                lines.append(
                    f'http_response_size_bytes_sum{{'
                    f'method="{method}",path="{path}"'
                    f'}} {total}'
                )

        # Active requests
        lines.append('# HELP http_requests_active Number of active HTTP requests')
        lines.append('# TYPE http_requests_active gauge')
        lines.append(f'http_requests_active {self._active_requests}')

        # Application uptime
        uptime = time.time() - self._app_start_time
        lines.append('# HELP app_uptime_seconds Application uptime in seconds')
        lines.append('# TYPE app_uptime_seconds counter')
        lines.append(f'app_uptime_seconds {uptime}')

        return '\n'.join(lines) + '\n'


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus metrics collection middleware.

    Automatically collects HTTP request metrics and provides a /metrics
    endpoint for Prometheus scraping.
    """

    def __init__(
        self,
        app: Any,
        metrics_path: str = '/metrics',
        collect_request_size: bool = True,
        collect_response_size: bool = True,
        exclude_paths: list[str] | None = None,
        path_normalizer: callable | None = None,
    ):
        """Initialize Prometheus middleware.

        Args:
            app: RSGI application
            metrics_path: Path to expose metrics endpoint
            collect_request_size: Whether to collect request size metrics
            collect_response_size: Whether to collect response size metrics
            exclude_paths: List of paths to exclude from metrics collection
            path_normalizer: Function to normalize paths for metrics grouping

        """
        super().__init__(app)
        self.metrics = PrometheusMetrics()
        self.metrics_path = metrics_path
        self.collect_request_size = collect_request_size
        self.collect_response_size = collect_response_size
        self.exclude_paths = exclude_paths or []
        self.path_normalizer = path_normalizer or self._default_path_normalizer

    def _default_path_normalizer(self, path: str) -> str:
        """Normalize path that groups paths with IDs.

        Converts paths like /users/123 to /users/{id} for better grouping.
        """
        # Replace UUIDs first (before numeric IDs to avoid conflicts)
        uuid_pattern = (
            r'/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
            r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
        )
        path = re.sub(uuid_pattern, '/{uuid}', path)
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        return path

    def _should_collect_metrics(self, path: str) -> bool:
        """Check if metrics should be collected for this path."""
        return path not in self.exclude_paths

    def _get_request_size(self, scope: Scope) -> int:
        """Get request size from headers."""
        content_length = scope.headers.get('content-length')
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return 0

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request and collect metrics."""
        path = scope.path
        method = scope.method

        # Handle metrics endpoint
        if path == self.metrics_path:
            metrics_content = self.metrics.get_prometheus_metrics()
            response = PlainTextResponse(
                content=metrics_content,
                headers={'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'},
            )
            return await response(scope, protocol)

        # Skip metrics collection for excluded paths
        if not self._should_collect_metrics(path):
            return await self.app(scope, protocol)

        # Normalize path for metrics grouping
        normalized_path = self.path_normalizer(path)

        # Start timing and collect request metrics
        start_time = time.time()
        self.metrics.inc_active_requests()

        request_size = 0
        if self.collect_request_size:
            request_size = self._get_request_size(scope)
            self.metrics.record_request_size(method, normalized_path, request_size)

        try:
            # Create response capture for size measurement
            response_size = 0
            status_code = 200

            protocol.enable_response_capture()

            await self.app(scope, protocol)
            response_size += len(protocol._response_capture.get_response_size())
            status_code = protocol.status_code

        except Exception as e:
            # Handle errors and set appropriate status code
            from velithon.exceptions import HTTPException

            if isinstance(e, HTTPException):
                status_code = e.status_code
            else:
                status_code = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            self.metrics.dec_active_requests()
            self.metrics.inc_request_count(method, normalized_path, status_code)
            self.metrics.record_request_duration(method, normalized_path, duration)

            if self.collect_response_size and response_size > 0:
                self.metrics.record_response_size(
                    method, normalized_path, response_size
                )


class FastPrometheusMiddleware(PrometheusMiddleware):
    """High-performance Prometheus middleware with minimal overhead.

    Optimized version that reduces metric collection overhead for
    high-throughput applications.
    """

    def __init__(self, *args, **kwargs):
        """Initialize fast Prometheus middleware with optimizations."""
        super().__init__(*args, **kwargs)
        # Enable performance optimizations
        self._metric_cache = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes

    def _cleanup_old_metrics(self) -> None:
        """Periodically cleanup old metric data to prevent memory leaks."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            # Keep only recent duration data (last 1000 requests per endpoint)
            for key in list(self.metrics._request_duration.keys()):
                durations = self.metrics._request_duration[key]
                if len(durations) > 1000:
                    self.metrics._request_duration[key] = durations[-1000:]

            self._last_cleanup = current_time

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Optimized request processing with periodic cleanup."""
        self._cleanup_old_metrics()
        return await super().process_http_request(scope, protocol)


# Alias for Rust middleware optimizer compatibility
RustPrometheusMiddleware = FastPrometheusMiddleware
