"""Rate limiting storage backends for Velithon framework.

This module provides storage backend implementations for rate limiting,
including in-memory and Redis-based storage options.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def increment(self, key: str, window: int) -> tuple[int, int]:
        """Increment the counter for a key and return current count and TTL.

        Args:
            key: The rate limit key (e.g., IP address, user ID)
            window: Time window in seconds

        Returns:
            Tuple of (current_count, ttl_seconds)

        """
        raise NotImplementedError()

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset the counter for a key.

        Args:
            key: The rate limit key to reset

        """
        raise NotImplementedError()

    @abstractmethod
    async def get(self, key: str) -> int:
        """Get the current count for a key.

        Args:
            key: The rate limit key

        Returns:
            Current count, or 0 if key doesn't exist

        """
        raise NotImplementedError()


class InMemoryRateLimitStorage(RateLimitStorage):
    """In-memory storage backend for rate limiting.

    This implementation uses a dictionary to store rate limit counters
    with automatic cleanup of expired entries. Suitable for single-worker
    deployments or development environments.
    """

    def __init__(self) -> None:
        """Initialize the in-memory storage."""
        self._storage: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def _cleanup_expired(self) -> None:
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                async with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key
                        for key, (_, expiry) in self._storage.items()
                        if expiry < current_time
                    ]
                    for key in expired_keys:
                        del self._storage[key]
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue cleanup even if there's an error
                continue

    async def increment(self, key: str, window: int) -> tuple[int, int]:
        """Increment the counter for a key.

        Args:
            key: The rate limit key
            window: Time window in seconds

        Returns:
            Tuple of (current_count, ttl_seconds)

        """
        async with self._lock:
            current_time = time.time()
            expiry_time = current_time + window

            if key in self._storage:
                count, expiry = self._storage[key]
                if expiry > current_time:
                    # Key is still valid, increment
                    count += 1
                    self._storage[key] = (count, expiry)
                    ttl = int(expiry - current_time)
                    return count, ttl
                else:
                    # Key expired, reset
                    self._storage[key] = (1, expiry_time)
                    return 1, window
            else:
                # New key
                self._storage[key] = (1, expiry_time)
                return 1, window

    async def reset(self, key: str) -> None:
        """Reset the counter for a key.

        Args:
            key: The rate limit key to reset

        """
        async with self._lock:
            if key in self._storage:
                del self._storage[key]

    async def get(self, key: str) -> int:
        """Get the current count for a key.

        Args:
            key: The rate limit key

        Returns:
            Current count, or 0 if key doesn't exist or expired

        """
        async with self._lock:
            current_time = time.time()
            if key in self._storage:
                count, expiry = self._storage[key]
                if expiry > current_time:
                    return count
                else:
                    # Expired, clean up
                    del self._storage[key]
                    return 0
            return 0

    async def close(self) -> None:
        """Close the storage and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class RedisRateLimitStorage(RateLimitStorage):
    """Redis-based storage backend for rate limiting.

    This implementation uses Redis for distributed rate limiting across
    multiple workers or processes. Requires the redis package.
    """

    def __init__(self, redis_url: str = 'redis://localhost:6379/0') -> None:
        """Initialize the Redis storage.

        Args:
            redis_url: Redis connection URL

        """
        try:
            import redis.asyncio as aioredis
        except ImportError as e:
            raise ImportError(
                'Redis support requires the redis package. '
                'Install it with: pip install "velithon[redis]"'
            ) from e

        self._redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = await aioredis.from_url(
                self._redis_url, encoding='utf-8', decode_responses=True
            )
        return self._redis

    async def increment(self, key: str, window: int) -> tuple[int, int]:
        """Increment the counter for a key using Redis.

        Args:
            key: The rate limit key
            window: Time window in seconds

        Returns:
            Tuple of (current_count, ttl_seconds)

        """
        redis = await self._get_redis()
        prefixed_key = f'ratelimit:{key}'

        # Use Redis pipeline for atomic operations
        pipe = redis.pipeline()
        pipe.incr(prefixed_key)
        pipe.ttl(prefixed_key)
        results = await pipe.execute()

        count = results[0]
        ttl = results[1]

        # If this is the first increment or key expired, set expiry
        if count == 1 or ttl == -1:
            await redis.expire(prefixed_key, window)
            ttl = window

        return count, ttl

    async def reset(self, key: str) -> None:
        """Reset the counter for a key.

        Args:
            key: The rate limit key to reset

        """
        redis = await self._get_redis()
        prefixed_key = f'ratelimit:{key}'
        await redis.delete(prefixed_key)

    async def get(self, key: str) -> int:
        """Get the current count for a key.

        Args:
            key: The rate limit key

        Returns:
            Current count, or 0 if key doesn't exist

        """
        redis = await self._get_redis()
        prefixed_key = f'ratelimit:{key}'
        value = await redis.get(prefixed_key)
        return int(value) if value else 0

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
