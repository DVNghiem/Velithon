import asyncio
import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from velithon._velithon import ProxyClient, ProxyLoadBalancer
from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.requests import Request
from velithon.responses import JSONResponse, ProxyResponse

logger = logging.getLogger(__name__)


class ProxyMiddleware(BaseHTTPMiddleware):
    """High-performance HTTP proxy middleware.

    Features:
    - Multiple upstream targets with load balancing
    - Circuit breaker for resilience
    - Health checking
    - Request/response transformation hooks
    - Comprehensive error handling
    """

    def __init__(
        self,
        app: Any,
        targets: str | list[str],
        *,
        load_balancing_strategy: str = 'round_robin',
        weights: list[int] | None = None,
        health_check_path: str = '/health',
        health_check_interval: int = 30,
        timeout_ms: int = 30000,
        max_retries: int = 3,
        max_failures: int = 5,
        recovery_timeout_ms: int = 60000,
        strip_request_headers: list[str] | None = None,
        strip_response_headers: list[str] | None = None,
        add_request_headers: dict[str, str] | None = None,
        add_response_headers: dict[str, str] | None = None,
        transform_request: Callable | None = None,
        transform_response: Callable | None = None,
        path_prefix: str = '',
        upstream_path_prefix: str = '',
        enable_health_checks: bool = True,
    ):
        """Initialize proxy middleware.

        Args:
            app: The ASGI application to wrap
            targets: Single target URL or list of target URLs for load balancing
            load_balancing_strategy: "round_robin", "random", or "weighted"
            weights: Weights for weighted load balancing (required if strategy is "weighted")
            health_check_path: Path for health checking upstream services
            health_check_interval: Interval in seconds between health checks
            timeout_ms: Request timeout in milliseconds
            max_retries: Maximum number of retry attempts
            max_failures: Maximum failures before circuit breaker opens
            recovery_timeout_ms: Time before circuit breaker allows retry
            strip_request_headers: Headers to remove from upstream requests
            strip_response_headers: Headers to remove from responses
            add_request_headers: Headers to add to upstream requests
            add_response_headers: Headers to add to responses
            transform_request: Callable to transform request before forwarding
            transform_response: Callable to transform response before returning
            path_prefix: URL path prefix that triggers proxy (e.g., "/api/v1")
            upstream_path_prefix: Path prefix to add to upstream requests
            enable_health_checks: Whether to enable background health checking

        """
        super().__init__(app)

        # Normalize targets
        if isinstance(targets, str):
            self.targets = [targets]
        else:
            self.targets = targets

        if not self.targets:
            raise ValueError('At least one target URL is required')

        # Validate target URLs
        for target in self.targets:
            parsed = urlparse(target)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f'Invalid target URL: {target}')

        # Initialize load balancer
        self.load_balancer = ProxyLoadBalancer(
            targets=self.targets,
            strategy=load_balancing_strategy,
            weights=weights,
            health_check_url=health_check_path,
        )

        # Create proxy clients for each target
        self.proxy_clients: dict[str, ProxyClient] = {}
        for target in self.targets:
            self.proxy_clients[target] = ProxyClient(
                target_url=target,
                timeout_ms=timeout_ms,
                max_retries=max_retries,
                max_failures=max_failures,
                recovery_timeout_ms=recovery_timeout_ms,
            )

        self.health_check_interval = health_check_interval
        self.path_prefix = path_prefix.rstrip('/')
        self.upstream_path_prefix = upstream_path_prefix.rstrip('/')
        self.enable_health_checks = enable_health_checks

        # Header processing
        self.strip_request_headers = set(
            h.lower() for h in (strip_request_headers or [])
        )
        self.strip_response_headers = set(
            h.lower() for h in (strip_response_headers or [])
        )
        self.add_request_headers = add_request_headers or {}
        self.add_response_headers = add_response_headers or {}

        # Transformation hooks
        self.transform_request = transform_request
        self.transform_response = transform_response

        # Default headers to strip for proxy
        self.strip_request_headers.update(
            {
                'host',
                'content-length',
                'transfer-encoding',
                'connection',
                'upgrade',
                'proxy-connection',
            }
        )

        self.strip_response_headers.update(
            {'transfer-encoding', 'connection', 'upgrade'}
        )

        # Start health checking task only if enabled
        self._health_check_task = None
        if self.enable_health_checks:
            self._start_health_checking()

    def _start_health_checking(self):
        """Start background health checking task."""

        async def health_check_loop():
            while True:
                try:
                    await self.load_balancer.health_check()
                    await asyncio.sleep(self.health_check_interval)
                except Exception as e:
                    logger.error(f'Health check failed: {e}')
                    await asyncio.sleep(self.health_check_interval)

        try:
            # Try to get the running event loop
            loop = asyncio.get_running_loop()
            self._health_check_task = loop.create_task(health_check_loop())
        except RuntimeError:
            # No event loop running yet, will start later
            pass

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request and forward to upstream if needed."""
        request_path = scope.path

        # Check if request should be proxied
        if self.path_prefix and not request_path.startswith(self.path_prefix):
            return await self.app(scope, protocol)

        try:
            # Start health checking if not already running
            if self._health_check_task is None:
                self._start_health_checking()

            # Get target URL from load balancer
            target_url = await self.load_balancer.get_next_target()
            proxy_client = self.proxy_clients[target_url]

            # Build upstream path
            upstream_path = request_path
            if self.path_prefix:
                upstream_path = request_path[len(self.path_prefix) :]
            if self.upstream_path_prefix:
                upstream_path = self.upstream_path_prefix + upstream_path

            # Create request object for transformation
            request = Request(scope, protocol)

            # Transform request if needed
            if self.transform_request:
                request = await self._call_transform_function(
                    self.transform_request, request
                )

            # Prepare headers
            headers_dict = {}
            for key, value in scope.headers.items():
                if key.lower() not in self.strip_request_headers:
                    headers_dict[key] = value

            # Add custom headers
            headers_dict.update(self.add_request_headers)

            # Get request body
            body = None
            if scope.method in ('POST', 'PUT', 'PATCH'):
                try:
                    body = await request.body()
                except Exception as e:
                    logger.warning(f'Failed to read request body: {e}')

            # Build query parameters
            query_params = {}
            if scope.query_string:
                query_string = scope.query_string.decode('utf-8')
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value

            # Forward request
            (
                status_code,
                response_headers,
                response_body,
            ) = await proxy_client.forward_request(
                method=scope.method,
                path=upstream_path,
                headers=headers_dict,
                body=body,
                query_params=query_params if query_params else None,
            )

            # Process response headers
            filtered_headers = {}
            for key, value in response_headers.items():
                if key.lower() not in self.strip_response_headers:
                    filtered_headers[key] = value

            # Add custom response headers
            filtered_headers.update(self.add_response_headers)

            # Create response
            response = ProxyResponse(
                content=response_body, status_code=status_code, headers=filtered_headers
            )

            # Transform response if needed
            if self.transform_response:
                response = await self._call_transform_function(
                    self.transform_response, response
                )

            # Send response
            await response(scope, protocol)

        except Exception as e:
            logger.error(f'Proxy request failed: {e}')
            error_response = JSONResponse(
                content={'error': 'Proxy request failed', 'detail': str(e)},
                status_code=502,
            )
            await error_response(scope, protocol)

    async def _call_transform_function(self, transform_func: Callable, obj: Any) -> Any:
        """Call transformation function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(transform_func):
            return await transform_func(obj)
        else:
            return transform_func(obj)

    async def get_proxy_status(self) -> dict[str, Any]:
        """Get status of all proxy targets and load balancer."""
        health_status = await self.load_balancer.get_health_status()

        circuit_status = {}
        for target, client in self.proxy_clients.items():
            (
                state,
                failure_count,
                last_failure,
            ) = await client.get_circuit_breaker_status()
            circuit_status[target] = {
                'state': state,
                'failure_count': failure_count,
                'last_failure_ms': last_failure,
            }

        return {
            'targets': self.targets,
            'health_status': health_status,
            'circuit_breaker_status': circuit_status,
            'load_balancing_strategy': 'round_robin',  # Could be made dynamic
        }

    async def reset_circuit_breakers(self):
        """Reset all circuit breakers."""
        for client in self.proxy_clients.values():
            await client.reset_circuit_breaker()

    async def cleanup(self):
        """Async cleanup method for proper task cancellation."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    def __del__(self):
        """Cleanup health checking task."""
        if self._health_check_task and not self._health_check_task.done():
            try:
                # Try to get the current event loop and cancel the task
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    self._health_check_task.cancel()
            except RuntimeError:
                # Event loop is already closed or not running, task will be cleaned up automatically
                pass
            except Exception:
                # Any other exception, just ignore
                pass
