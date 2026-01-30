"""Hierarchical cancellation tokens for tool execution."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class CancellationToken:
    """
    Hierarchical cancellation token.

    When a parent is cancelled, all children are cancelled.
    Each tool call gets a child token for independent cancellation.

    Unlike tokio_util's CancellationToken which uses Rust's Drop trait for
    automatic cleanup, Python requires explicit cleanup of watcher tasks.
    Use the `child_scope()` context manager for automatic cleanup, or call
    `cleanup()` manually when done with a child token.
    """

    def __init__(self, parent: "CancellationToken | None" = None) -> None:
        self._cancelled = asyncio.Event()
        self._parent = parent
        self._watcher: asyncio.Task[None] | None = None
        if parent:
            self._watcher = asyncio.create_task(self._watch_parent())

    async def _watch_parent(self) -> None:
        """Watch parent and propagate cancellation."""
        if self._parent:
            try:
                await self._parent._cancelled.wait()
                self._cancelled.set()
            except asyncio.CancelledError:
                # Watcher was cleaned up, this is expected
                pass

    def cancel(self) -> None:
        """Cancel this token and all children."""
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested (includes parent state)."""
        if self._cancelled.is_set():
            return True
        # Also check parent directly for immediate propagation
        if self._parent and self._parent.is_cancelled():
            self._cancelled.set()  # Cache the result
            return True
        return False

    async def wait_cancelled(self) -> None:
        """Wait until cancellation is requested."""
        if self._parent:
            # Wait for either self or parent to be cancelled
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(self._cancelled.wait()),
                    asyncio.create_task(self._parent.wait_cancelled()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self._cancelled.set()  # Propagate to self
        else:
            await self._cancelled.wait()

    def child(self) -> "CancellationToken":
        """
        Create a child token that inherits cancellation.

        IMPORTANT: Call cleanup() on the child when done, or use child_scope()
        context manager to avoid task leaks.
        """
        return CancellationToken(parent=self)

    @asynccontextmanager
    async def child_scope(self) -> AsyncIterator["CancellationToken"]:
        """
        Create a child token with automatic cleanup.

        Usage:
            async with parent.child_scope() as child:
                # child is automatically cleaned up when exiting
                await do_work(child)
        """
        child = self.child()
        try:
            yield child
        finally:
            child.cleanup()

    def cleanup(self) -> None:
        """Clean up watcher task. Call this when done with a child token."""
        if self._watcher and not self._watcher.done():
            self._watcher.cancel()

    def __del__(self) -> None:
        """Best-effort cleanup on garbage collection."""
        if self._watcher and not self._watcher.done():
            self._watcher.cancel()
