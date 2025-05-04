# -*- coding: utf-8 -*-
import typing
import functools
import inspect
import asyncio
import anyio

T = typing.TypeVar("T")

def is_async_callable(obj: typing.Any) -> typing.Any:
    while isinstance(obj, functools.partial):
        obj = obj.func

    return inspect.iscoroutinefunction(obj) or (callable(obj) and inspect.iscoroutinefunction(obj.__call__))

async def run_in_threadpool(func: typing.Callable, *args, **kwargs):
    if kwargs:  # pragma: no cover
        # run_sync doesn't accept 'kwargs', so bind them in here
        func = functools.partial(func, **kwargs)
    return await asyncio.to_thread(func, *args)


class _StopIteration(Exception):
    pass


def _next(iterator: typing.Iterator[T]) -> T:
    # We can't raise `StopIteration` from within the threadpool iterator
    # and catch it outside that context, so we coerce them into a different
    # exception type.
    try:
        return next(iterator)
    except StopIteration:
        raise _StopIteration


async def iterate_in_threadpool(
    iterator: typing.Iterable[T],
) -> typing.AsyncIterator[T]:
    as_iterator = iter(iterator)
    while True:
        try:
            yield await anyio.to_thread.run_sync(_next, as_iterator)
        except _StopIteration:
            break
