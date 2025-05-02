# -*- coding: utf-8 -*-
import typing
import functools
import inspect
import asyncio

def is_async_callable(obj: typing.Any) -> typing.Any:
    while isinstance(obj, functools.partial):
        obj = obj.func

    return inspect.iscoroutinefunction(obj) or (callable(obj) and inspect.iscoroutinefunction(obj.__call__))


async def run_in_threadpool(func: typing.Callable, *args, **kwargs):
    if kwargs:  # pragma: no cover
        # run_sync doesn't accept 'kwargs', so bind them in here
        func = functools.partial(func, **kwargs)
    return await asyncio.to_thread(func, *args)
