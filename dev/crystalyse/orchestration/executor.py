"""Parallel tool executor with smart locking."""

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from .cancellation import CancellationToken
from .futures import OrderedFutures
from .locking import AsyncRwLock

logger = logging.getLogger(__name__)

# Default timeout for tool execution (5 minutes)
DEFAULT_TIMEOUT = 300


@dataclass
class ToolSpec:
    """Specification for a tool with parallelism flag."""

    name: str
    handler: Callable[..., Coroutine[Any, Any, Any]]
    supports_parallel: bool = True  # Default to parallel for reads


@dataclass
class ToolCall:
    """A single tool invocation."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_call_id: str
    content: str
    error: str | None = None


class ParallelToolExecutor:
    """
    Execute tools in parallel with smart locking.

    Parallel tools (reads) run concurrently.
    Non-parallel tools (mutations) are serialised.
    Results are returned in call order.
    """

    def __init__(
        self,
        tools: dict[str, ToolSpec],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._tools = tools
        self._timeout = timeout
        self._lock = AsyncRwLock()
        self._in_flight: OrderedFutures | None = None

    def _ensure_queue(self) -> OrderedFutures:
        """Ensure in-flight queue exists."""
        if self._in_flight is None:
            self._in_flight = OrderedFutures()
        return self._in_flight

    def supports_parallel(self, tool_name: str) -> bool:
        """Check if a tool supports parallel execution."""
        if tool_name not in self._tools:
            return False
        return self._tools[tool_name].supports_parallel

    async def _execute_with_lock(
        self,
        tool_call: ToolCall,
        cancellation_token: CancellationToken,
    ) -> ToolResult:
        """Execute a single tool with appropriate locking."""
        try:
            return await self._execute_with_lock_inner(tool_call, cancellation_token)
        finally:
            # Clean up the cancellation token's watcher task to avoid leaks
            cancellation_token.cleanup()

    async def _execute_with_lock_inner(
        self,
        tool_call: ToolCall,
        cancellation_token: CancellationToken,
    ) -> ToolResult:
        """Inner execution logic."""
        tool_spec = self._tools.get(tool_call.name)
        if not tool_spec:
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                error=f"Unknown tool: {tool_call.name}",
            )

        # Acquire appropriate lock
        lock_ctx = self._lock.read() if tool_spec.supports_parallel else self._lock.write()

        async with lock_ctx:
            if cancellation_token.is_cancelled():
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content="",
                    error="Cancelled",
                )

            try:
                result = await asyncio.wait_for(
                    tool_spec.handler(**tool_call.input),
                    timeout=self._timeout,
                )
                # Serialise result to string
                if isinstance(result, dict):
                    content = json.dumps(result)
                else:
                    content = str(result)
                return ToolResult(tool_call_id=tool_call.id, content=content)

            except TimeoutError:
                logger.warning(f"Tool {tool_call.name} timed out")
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content="",
                    error=f"Tool timed out after {self._timeout}s",
                )
            except Exception as e:
                logger.error(f"Tool {tool_call.name} failed: {e}")
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content="",
                    error=str(e),
                )

    def queue(
        self,
        tool_call: ToolCall,
        cancellation_token: CancellationToken,
    ) -> None:
        """Queue a tool call for parallel execution."""
        queue = self._ensure_queue()
        queue.push(self._execute_with_lock(tool_call, cancellation_token))

    async def drain(self) -> list[ToolResult]:
        """Wait for all queued tool calls and return results in order."""
        if self._in_flight is None:
            return []
        results = await self._in_flight.drain()
        self._in_flight = None  # Reset for next batch
        return results

    @property
    def pending_count(self) -> int:
        """Number of pending tool calls."""
        return len(self._in_flight) if self._in_flight else 0
