# -*- coding: utf-8 -*-
import asyncio
import concurrent.futures
import functools
import os
import random
import threading
import time
import typing

T = typing.TypeVar("T")

# OPTIMIZED: Better configured thread pool with optimal sizing
_thread_pool = None
_pool_lock = threading.Lock()

def set_thread_pool() -> None:
    global _thread_pool
    with _pool_lock:
        if _thread_pool is None:
            # Optimal thread count: CPU cores + 4 (for I/O bound tasks)
            max_workers = min(32, (os.cpu_count() or 1) + 4)
            _thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="velithon_optimized"
            )

def is_async_callable(obj: typing.Any) -> bool:
    if isinstance(obj, functools.partial):
        obj = obj.func
    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(getattr(obj, '__call__', None))
    )

async def run_in_threadpool(func: typing.Callable, *args, **kwargs) -> typing.Any:
    global _thread_pool
    if _thread_pool is None:
        set_thread_pool()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_thread_pool, lambda: func(*args, **kwargs))

async def iterate_in_threadpool(iterator: typing.Iterable[T]) -> typing.AsyncIterator[T]:
    as_iterator = iter(iterator)
    
    def next_item() -> typing.Tuple[bool, typing.Optional[T]]:
        try:
            return True, next(as_iterator)
        except StopIteration:
            return False, None
    
    while True:
        has_next, item = await asyncio.to_thread(next_item)
        if not has_next:
            break
        yield item


class RequestIDGenerator:
    """Efficient request ID generator with much less overhead than UUID."""
    
    def __init__(self):
        self._prefix = f"{random.randint(100, 999)}"
        self._counter = 0
        self._lock = threading.Lock()
    
    def generate(self) -> str:
        """Generate a unique request ID with format: prefix-timestamp-counter."""
        timestamp = int(time.time() * 1000)  # Timestamp in milliseconds
        
        with self._lock:
            self._counter = (self._counter + 1) % 100000
            request_id = f"{self._prefix}-{timestamp}-{self._counter:05d}"
        
        return request_id
