"""Async read-write lock for parallel tool execution."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class AsyncRwLock:
    """
    Async read-write lock.

    Multiple readers can hold the lock simultaneously.
    Writers get exclusive access. This enables parallel reads
    (database queries) while serialising writes (file operations).
    """

    def __init__(self) -> None:
        self._readers = 0
        self._writer = False
        self._lock = asyncio.Lock()
        self._readers_ok = asyncio.Condition(self._lock)
        self._writer_ok = asyncio.Condition(self._lock)

    @asynccontextmanager
    async def read(self) -> AsyncIterator[None]:
        """Acquire read lock (multiple readers allowed)."""
        async with self._lock:
            while self._writer:
                await self._readers_ok.wait()
            self._readers += 1
        try:
            yield
        finally:
            async with self._lock:
                self._readers -= 1
                if self._readers == 0:
                    self._writer_ok.notify()

    @asynccontextmanager
    async def write(self) -> AsyncIterator[None]:
        """Acquire write lock (exclusive access)."""
        async with self._lock:
            while self._writer or self._readers > 0:
                await self._writer_ok.wait()
            self._writer = True
        try:
            yield
        finally:
            async with self._lock:
                self._writer = False
                self._readers_ok.notify_all()
                self._writer_ok.notify()
