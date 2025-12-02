"""Rate limiting example for Velithon.

This example demonstrates how to use the rate limiting middleware with different
configurations, algorithms, and storage backends.
"""

import time
from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.rate_limit import (
    RateLimitMiddleware,
    get_ip_key,
    get_user_key,
    rate_limit,
)
from velithon.middleware.rate_limit_storage import InMemoryRateLimitStorage
from velithon.responses import JSONResponse
from velithon.requests import Request


# Custom key extractor for API keys
def get_api_key(request: Request) -> str:
    """Extract API key from header."""
    api_key = request.headers.get('x-api-key')
    if api_key:
        return f'apikey:{api_key}'
    return f'ip:{get_ip_key(request)}'


async def homepage(request):
    """Public endpoint with standard rate limit."""
    return JSONResponse({'message': 'Welcome to the public API'})


@rate_limit(limit=5, window=60)
async def sensitive_data(request):
    """Sensitive endpoint with stricter rate limit."""
    return JSONResponse({'message': 'This is sensitive data'})


async def bursty_endpoint(request):
    """Endpoint that allows bursts."""
    return JSONResponse({'message': 'Burst allowed here'})


# Create application with rate limiting middleware
app = Velithon(
    middleware=[
        Middleware(
            RateLimitMiddleware,
            limit=10,  # Default limit: 10 requests
            window=60,  # Per 60 seconds
            algorithm='token_bucket',  # Use token bucket algorithm
            key_func=get_ip_key,  # Rate limit by IP
            error_message='Too many requests. Please slow down.',
        )
    ]
)

# Add routes
app.add_route('/', homepage)
app.add_route('/sensitive', sensitive_data)
app.add_route('/burst', bursty_endpoint)


# Example of how to use Redis storage (commented out as it requires Redis)
"""
from velithon.middleware.rate_limit_storage import RedisRateLimitStorage

app_redis = Velithon(
    middleware=[
        Middleware(
            RateLimitMiddleware,
            limit=100,
            window=60,
            storage=RedisRateLimitStorage(redis_url='redis://localhost:6379/0'),
            algorithm='sliding_window',
        )
    ]
)
"""

if __name__ == '__main__':
    # This block is for demonstration purposes
    print("Rate limiting example app created.")
    print("Run with: velithon run --app examples.rate_limit_example:app")
