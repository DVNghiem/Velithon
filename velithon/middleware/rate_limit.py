"""Rate limiting middleware for Velithon framework.

This module provides the main rate limiting middleware with support for
multiple algorithms, storage backends, and flexible configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import ConditionalMiddleware
from velithon.middleware.rate_limit_algorithms import (
    FixedWindowAlgorithm,
    RateLimitAlgorithm,
    SimpleTokenBucketAlgorithm,
    SlidingWindowAlgorithm,
)
from velithon.middleware.rate_limit_storage import (
    InMemoryRateLimitStorage,
    RateLimitStorage,
)
from velithon.requests import Request
from velithon.responses import JSONResponse


def get_ip_key(request: Request) -> str:
    """Extract IP address from request for rate limiting.

    Args:
        request: The incoming request

    Returns:
        IP address as string

    """
    # Check for forwarded IP first (behind proxy)
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(',')[0].strip()

    # Check for real IP header
    real_ip = request.headers.get('x-real-ip')
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    client = getattr(request.scope, 'client', None)
    if client and len(client) >= 1:
        return client[0]

    return 'unknown'


def get_user_key(request: Request) -> str:
    """Extract user ID from request context for rate limiting.

    Args:
        request: The incoming request

    Returns:
        User ID as string, or IP if no user

    """
    # Try to get user from request state/context
    user = getattr(request.state, 'user', None)
    if user:
        user_id = getattr(user, 'id', None) or getattr(user, 'username', None)
        if user_id:
            return f'user:{user_id}'

    # Fall back to IP
    return f'ip:{get_ip_key(request)}'


def get_endpoint_key(request: Request) -> str:
    """Extract endpoint path from request for rate limiting.

    Args:
        request: The incoming request

    Returns:
        Endpoint path combined with IP

    """
    path = request.scope.path
    ip = get_ip_key(request)
    return f'{ip}:{path}'


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting middleware.

    Attributes:
        limit: Maximum number of requests allowed in the window
        window: Time window in seconds
        algorithm: Algorithm to use ('token_bucket', 'sliding_window', 'fixed_window')
        storage: Storage backend instance
        key_func: Function to extract rate limit key from request
        skip_failed_requests: Whether to skip counting failed requests (4xx, 5xx)
        error_message: Custom error message for rate limit exceeded

    """

    limit: int = 100
    window: int = 60
    algorithm: str = 'token_bucket'
    storage: Optional[RateLimitStorage] = None
    key_func: Callable[[Request], str] = field(default=get_ip_key)
    skip_failed_requests: bool = False
    error_message: str = 'Rate limit exceeded. Please try again later.'

    def __post_init__(self) -> None:
        """Validate and initialize configuration."""
        if self.limit <= 0:
            raise ValueError('limit must be positive')
        if self.window <= 0:
            raise ValueError('window must be positive')

        # Create default storage if not provided
        if self.storage is None:
            self.storage = InMemoryRateLimitStorage()

        # Validate algorithm
        valid_algorithms = {'token_bucket', 'sliding_window', 'fixed_window'}
        if self.algorithm not in valid_algorithms:
            raise ValueError(
                f"algorithm must be one of {valid_algorithms}, got '{self.algorithm}'"
            )


class RateLimitMiddleware(ConditionalMiddleware):
    """Rate limiting middleware for Velithon.

    This middleware enforces rate limits on incoming requests using
    configurable algorithms and storage backends. It adds standard
    rate limit headers and returns 429 status when limit is exceeded.
    """

    def __init__(
        self,
        app: Any,
        limit: int = 100,
        window: int = 60,
        algorithm: str = 'token_bucket',
        storage: Optional[RateLimitStorage] = None,
        key_func: Optional[Callable[[Request], str]] = None,
        skip_failed_requests: bool = False,
        error_message: str = 'Rate limit exceeded. Please try again later.',
    ) -> None:
        """Initialize the rate limiting middleware.

        Args:
            app: The next RSGI application in the middleware chain
            limit: Maximum requests allowed per window (default: 100)
            window: Time window in seconds (default: 60)
            algorithm: Algorithm to use - 'token_bucket', 'sliding_window', or 'fixed_window'
            storage: Storage backend (default: InMemoryRateLimitStorage)
            key_func: Function to extract rate limit key (default: get_ip_key)
            skip_failed_requests: Whether to skip counting failed requests
            error_message: Custom error message for rate limit exceeded

        """
        super().__init__(app)

        # Create configuration
        self.config = RateLimitConfig(
            limit=limit,
            window=window,
            algorithm=algorithm,
            storage=storage,
            key_func=key_func or get_ip_key,
            skip_failed_requests=skip_failed_requests,
            error_message=error_message,
        )

        # Initialize algorithm
        self.algorithm_impl = self._get_algorithm_impl(algorithm)

    def _get_algorithm_impl(self, algorithm: str) -> RateLimitAlgorithm:
        """Get the algorithm implementation instance.

        Args:
            algorithm: Algorithm name

        Returns:
            Algorithm implementation instance

        """
        algorithms = {
            'token_bucket': SimpleTokenBucketAlgorithm(),
            'sliding_window': SlidingWindowAlgorithm(),
            'fixed_window': FixedWindowAlgorithm(),
        }
        return algorithms[algorithm]

    async def should_process_request(self, scope: Scope, protocol: Protocol) -> bool:
        """Check rate limit and determine if request should continue.

        Args:
            scope: Request scope
            protocol: Protocol handler

        Returns:
            True if request should continue, False if rate limited

        """
        # Create request object to extract key
        request = Request(scope, protocol)

        # Extract rate limit key
        key = self.config.key_func(request)

        # Check rate limit
        is_allowed, rate_limit_info = await self.algorithm_impl.is_allowed(
            self.config.storage, key, self.config.limit, self.config.window
        )

        # Add rate limit headers
        headers = [
            ('X-RateLimit-Limit', str(rate_limit_info['limit'])),
            ('X-RateLimit-Remaining', str(rate_limit_info['remaining'])),
            ('X-RateLimit-Reset', str(rate_limit_info['reset'])),
        ]

        if not is_allowed:
            # Add Retry-After header
            retry_after = rate_limit_info.get('retry_after')
            if retry_after:
                headers.append(('Retry-After', str(retry_after)))

            # Return 429 response
            response = JSONResponse(
                {
                    'error': 'rate_limit_exceeded',
                    'message': self.config.error_message,
                    'limit': rate_limit_info['limit'],
                    'reset': rate_limit_info['reset'],
                    'retry_after': retry_after,
                },
                status_code=429,
                headers=dict(headers),
            )
            await response(scope, protocol)
            return False

        # Update headers for successful request
        protocol.update_headers(headers)
        return True


# Decorator for per-route rate limiting
class RateLimitDecorator:
    """Decorator for applying rate limits to specific routes.

    This is a placeholder for future per-route rate limiting support.
    Currently, rate limiting is applied at the middleware level.
    """

    def __init__(
        self,
        limit: int = 100,
        window: int = 60,
        algorithm: str = 'token_bucket',
        key_func: Optional[Callable[[Request], str]] = None,
    ) -> None:
        """Initialize the rate limit decorator.

        Args:
            limit: Maximum requests allowed per window
            window: Time window in seconds
            algorithm: Algorithm to use
            key_func: Function to extract rate limit key

        """
        self.limit = limit
        self.window = window
        self.algorithm = algorithm
        self.key_func = key_func or get_ip_key

    def __call__(self, func: Callable) -> Callable:
        """Apply rate limit to a function.

        Args:
            func: The function to decorate

        Returns:
            Decorated function

        """
        # Store rate limit config on function for middleware to read
        func._rate_limit_config = {  # type: ignore
            'limit': self.limit,
            'window': self.window,
            'algorithm': self.algorithm,
            'key_func': self.key_func,
        }
        return func


# Convenience function for creating rate limit decorator
def rate_limit(
    limit: int = 100,
    window: int = 60,
    algorithm: str = 'token_bucket',
    key_func: Optional[Callable[[Request], str]] = None,
) -> RateLimitDecorator:
    """Create a rate limit decorator for routes.

    Args:
        limit: Maximum requests allowed per window
        window: Time window in seconds
        algorithm: Algorithm to use
        key_func: Function to extract rate limit key

    Returns:
        Rate limit decorator

    Example:
        @app.get("/api/data")
        @rate_limit(limit=10, window=60)
        async def get_data(request: Request):
            return {"data": "value"}

    """
    return RateLimitDecorator(limit, window, algorithm, key_func)
