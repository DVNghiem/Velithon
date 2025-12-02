"""Rate limiting algorithms for Velithon framework.

This module provides different rate limiting algorithm implementations
including fixed window, sliding window, and token bucket algorithms.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from velithon.middleware.rate_limit_storage import RateLimitStorage


class RateLimitAlgorithm(ABC):
    """Abstract base class for rate limiting algorithms."""

    @abstractmethod
    async def is_allowed(
        self, storage: RateLimitStorage, key: str, limit: int, window: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if a request is allowed under the rate limit.

        Args:
            storage: Storage backend to use
            key: Rate limit key (e.g., IP address)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info) where rate_limit_info contains:
                - limit: Maximum requests allowed
                - remaining: Requests remaining in window
                - reset: Unix timestamp when limit resets

        """
        raise NotImplementedError()


class FixedWindowAlgorithm(RateLimitAlgorithm):
    """Fixed window counter algorithm.

    Simple algorithm that resets the counter at fixed intervals.
    Fast but can allow bursts at window boundaries (up to 2x limit).
    """

    async def is_allowed(
        self, storage: RateLimitStorage, key: str, limit: int, window: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using fixed window algorithm.

        Args:
            storage: Storage backend
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)

        """
        count, ttl = await storage.increment(key, window)
        current_time = int(time.time())
        reset_time = current_time + ttl

        is_allowed = count <= limit
        remaining = max(0, limit - count)

        rate_limit_info = {
            'limit': limit,
            'remaining': remaining,
            'reset': reset_time,
            'retry_after': ttl if not is_allowed else None,
        }

        return is_allowed, rate_limit_info


class SlidingWindowAlgorithm(RateLimitAlgorithm):
    """Sliding window log algorithm.

    More accurate than fixed window, prevents boundary burst issues.
    Uses weighted count based on time overlap between windows.
    """

    async def is_allowed(
        self, storage: RateLimitStorage, key: str, limit: int, window: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using sliding window algorithm.

        Args:
            storage: Storage backend
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)

        """
        current_time = time.time()
        current_window = int(current_time / window)
        previous_window = current_window - 1

        # Get counts for current and previous windows
        current_key = f'{key}:{current_window}'
        previous_key = f'{key}:{previous_window}'

        current_count, ttl = await storage.increment(current_key, window)
        previous_count = await storage.get(previous_key)

        # Calculate weighted count based on time overlap
        elapsed_in_current = current_time % window
        weight = (window - elapsed_in_current) / window
        weighted_count = previous_count * weight + current_count

        is_allowed = weighted_count <= limit
        remaining = max(0, int(limit - weighted_count))
        reset_time = int(current_time + (window - elapsed_in_current))

        rate_limit_info = {
            'limit': limit,
            'remaining': remaining,
            'reset': reset_time,
            'retry_after': int(window - elapsed_in_current) if not is_allowed else None,
        }

        return is_allowed, rate_limit_info


class TokenBucketAlgorithm(RateLimitAlgorithm):
    """Token bucket algorithm.

    Industry-standard algorithm that allows controlled bursts while
    maintaining average rate. Used by AWS, GitHub, Stripe, etc.

    Tokens are added at a constant rate. Each request consumes one token.
    If bucket is empty, request is denied.
    """

    async def is_allowed(
        self, storage: RateLimitStorage, key: str, limit: int, window: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using token bucket algorithm.

        Args:
            storage: Storage backend
            key: Rate limit key
            limit: Maximum tokens (bucket capacity)
            window: Time window in seconds (refill period)

        Returns:
            Tuple of (is_allowed, rate_limit_info)

        """
        current_time = time.time()
        bucket_key = f'{key}:bucket'
        timestamp_key = f'{key}:timestamp'

        # Get current bucket state
        current_tokens = await storage.get(bucket_key)
        last_refill_str = await storage.get(timestamp_key)

        # Initialize if first request
        if current_tokens == 0 and last_refill_str == 0:
            current_tokens = limit
            last_refill = current_time
        else:
            last_refill = float(last_refill_str) if last_refill_str else current_time

        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_refill
        refill_rate = limit / window  # tokens per second
        tokens_to_add = int(time_elapsed * refill_rate)

        # Refill bucket (capped at limit)
        current_tokens = min(limit, current_tokens + tokens_to_add)

        # Try to consume one token
        if current_tokens >= 1:
            is_allowed = True
            current_tokens -= 1
            remaining = current_tokens
        else:
            is_allowed = False
            remaining = 0

        # Update storage
        if tokens_to_add > 0 or is_allowed:
            # Store updated values
            await storage.reset(bucket_key)
            await storage.reset(timestamp_key)

            # Set new values with expiry
            count, _ = await storage.increment(bucket_key, window * 2)
            # Adjust count to actual token value
            for _ in range(count - 1):
                await storage.increment(bucket_key, window * 2)

            # Store timestamp (using increment as a way to set value)
            # This is a workaround since we only have increment/get/reset
            # In production, you'd want a set() method
            timestamp_int = int(current_time)
            for _ in range(timestamp_int):
                await storage.increment(timestamp_key, window * 2)

        # Calculate when next token will be available
        time_until_refill = (1.0 / refill_rate) if not is_allowed else 0
        reset_time = int(current_time + time_until_refill)

        rate_limit_info = {
            'limit': limit,
            'remaining': remaining,
            'reset': reset_time,
            'retry_after': int(time_until_refill) if not is_allowed else None,
        }

        return is_allowed, rate_limit_info


# Simplified token bucket that works better with our storage interface
class SimpleTokenBucketAlgorithm(RateLimitAlgorithm):
    """Simplified token bucket using fixed window with burst allowance.

    This is a practical implementation that works well with simple
    increment/get/reset storage interface while still allowing bursts.
    """

    async def is_allowed(
        self, storage: RateLimitStorage, key: str, limit: int, window: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using simplified token bucket.

        Args:
            storage: Storage backend
            key: Rate limit key
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)

        """
        # Use fixed window but allow small burst (20% over limit)
        burst_allowance = int(limit * 0.2)
        effective_limit = limit + burst_allowance

        count, ttl = await storage.increment(key, window)
        current_time = int(time.time())
        reset_time = current_time + ttl

        # Allow up to effective_limit, but warn when over base limit
        is_allowed = count <= effective_limit
        remaining = max(0, limit - count)

        rate_limit_info = {
            'limit': limit,
            'remaining': remaining,
            'reset': reset_time,
            'retry_after': ttl if not is_allowed else None,
        }

        return is_allowed, rate_limit_info
