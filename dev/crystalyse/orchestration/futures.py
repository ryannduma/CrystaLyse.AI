"""Ordered futures collection for parallel tool execution."""

import asyncio
from collections import deque
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class OrderedFutures:
    """
    Collect async futures and yield results in submission order.

    Unlike asyncio.as_completed(), this maintains the order results
    are returned to match the order they were submitted. This is
    critical for conversation consistency.
    """

    def __init__(self) -> None:
        self._queue: deque[asyncio.Task[Any]] = deque()

    def push(self, coro: Coroutine[Any, Any, T]) -> None:
        """Add a coroutine to the queue. Starts execution immediately."""
        task = asyncio.create_task(coro)
        self._queue.append(task)

    def __len__(self) -> int:
        return len(self._queue)

    async def drain(self) -> list[Any]:
        """Wait for all futures and return results in submission order."""
        results = []
        while self._queue:
            task = self._queue.popleft()
            result = await task
            results.append(result)
        return results

    async def __aiter__(self):
        """Iterate over results in submission order."""
        while self._queue:
            task = self._queue.popleft()
            yield await task
