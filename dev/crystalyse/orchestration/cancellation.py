"""Hierarchical cancellation tokens for tool execution."""

import asyncio
from typing import Optional


class CancellationToken:
    """
    Hierarchical cancellation token.

    When a parent is cancelled, all children are cancelled.
    Each tool call gets a child token for independent cancellation.
    """

    def __init__(self, parent: Optional["CancellationToken"] = None) -> None:
        self._cancelled = asyncio.Event()
        self._parent = parent
        self._watcher: asyncio.Task[None] | None = None
        if parent:
            self._watcher = asyncio.create_task(self._watch_parent())

    async def _watch_parent(self) -> None:
        """Watch parent and propagate cancellation."""
        if self._parent:
            await self._parent._cancelled.wait()
            self._cancelled.set()

    def cancel(self) -> None:
        """Cancel this token and all children."""
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled.is_set()

    async def wait_cancelled(self) -> None:
        """Wait until cancellation is requested."""
        await self._cancelled.wait()

    def child(self) -> "CancellationToken":
        """Create a child token that inherits cancellation."""
        return CancellationToken(parent=self)

    def cleanup(self) -> None:
        """Clean up watcher task."""
        if self._watcher and not self._watcher.done():
            self._watcher.cancel()
