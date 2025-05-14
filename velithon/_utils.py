# -*- coding: utf-8 -*-
import typing
import functools
import asyncio
import concurrent.futures
import time
import random
import threading


T = typing.TypeVar("T")

# Allows configuring the maximum number of threads, suitable for application needs. 
# Reuse threadpool, reducing overhead when creating new ones.
_thread_pool = None

def set_thread_pool(max_workers: int = None):
    global _thread_pool
    _thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

def is_async_callable(obj: typing.Any) -> bool:
    if isinstance(obj, functools.partial):
        obj = obj.func
    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(getattr(obj, '__call__', None))
    )

async def run_in_threadpool(func: typing.Callable, *args, **kwargs):
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
    
    def generate(self):
        """Generate a unique request ID with format: prefix-timestamp-counter."""
        timestamp = int(time.time() * 1000)  # Timestamp in milliseconds
        
        with self._lock:
            self._counter = (self._counter + 1) % 100000
            request_id = f"{self._prefix}-{timestamp}-{self._counter:05d}"
        
        return request_id
