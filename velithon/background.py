from __future__ import annotations
import typing
import asyncio
import sys
from collections import deque

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

from velithon._utils import is_async_callable, run_in_threadpool

P = ParamSpec("P")

class BackgroundTask:
    def __init__(self, func: typing.Callable[P, typing.Any], *args: P.args, **kwargs: P.kwargs) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_async = is_async_callable(func)

    async def __call__(self) -> None:
        if self.is_async:
            await self.func(*self.args, **self.kwargs)
        else:
            await run_in_threadpool(self.func, *self.args, **self.kwargs)

class BackgroundTasks:
    def __init__(self, tasks: typing.Sequence[BackgroundTask] | None = None, max_concurrent: int = 10):
        # deque has better performance when adding/removing elements than list.
        self.tasks = deque(tasks) if tasks else deque()
        self.max_concurrent = max_concurrent

    def add_task(self, func: typing.Callable[P, typing.Any], *args: P.args, **kwargs: P.kwargs) -> None:
        task = BackgroundTask(func, *args, **kwargs)
        self.tasks.append(task)

    async def __call__(self, continue_on_error: bool = True) -> None:
        # To avoid overloading the threadpool or event loop, you can add a limit on the number of tasks running concurrently.
        semaphore = asyncio.Semaphore(self.max_concurrent)
        errors = []

        async def run_task(task: BackgroundTask) -> None:
            async with semaphore:
                try:
                    await task()
                except Exception as e:
                    errors.append(e)
                    if not continue_on_error:
                        raise
        # Tasks run concurrently instead of sequentially.
        # Take full advantage of asyncio's threadpool and event loop.
        # Reduce overall wait times.
        await asyncio.gather(*(run_task(task) for task in self.tasks))
        
        if errors:
            for error in errors:
                print(f"Task failed with error: {error}")
            if not continue_on_error:
                raise RuntimeError("One or more background tasks failed")