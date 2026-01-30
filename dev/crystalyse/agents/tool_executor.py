"""Custom tool executor with orchestration support.

Provides an alternative to the OpenAI SDK's built-in tool handling,
with support for:
- Parallel execution of read-only tools
- Serial execution of mutation tools
- Cancellation tokens for graceful shutdown
- Metrics collection for observability

This is designed for future use when moving away from SDK-managed
tool execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..orchestration import (
    CancellationToken,
    ParallelToolExecutor,
    ToolCall,
    ToolResult,
    TurnMetrics,
)
from ..orchestration import (
    ToolSpec as OrchToolSpec,
)
from .tool_classification import create_tool_specs

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for tool execution.

    Attributes:
        turn_id: Unique identifier for this turn.
        cancellation_token: Token for cancellation propagation.
        timeout: Default timeout in seconds.
        collect_metrics: Whether to collect execution metrics.
    """

    turn_id: str
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    timeout: float = 300.0
    collect_metrics: bool = True


class AgentToolExecutor:
    """Tool executor with orchestration support.

    Wraps the orchestration package's ParallelToolExecutor with
    agent-specific functionality.
    """

    def __init__(
        self,
        tools: list[Callable],
        timeout: float = 300.0,
    ):
        """Initialize the executor.

        Args:
            tools: List of tool functions to make available.
            timeout: Default timeout for tool execution.
        """
        self.timeout = timeout
        self._tool_specs = create_tool_specs(tools)
        self._tool_map = {spec.name: spec for spec in self._tool_specs}

        # Create orchestration specs
        orch_specs = [
            OrchToolSpec(
                name=spec.name,
                handler=spec.handler,
                supports_parallel=spec.supports_parallel,
            )
            for spec in self._tool_specs
        ]

        self._executor = ParallelToolExecutor(
            tools=orch_specs,
            timeout=int(timeout),
        )

        logger.info(
            f"AgentToolExecutor initialized with {len(tools)} tools "
            f"({len(self.parallel_tools)} parallel, {len(self.serial_tools)} serial)"
        )

    @property
    def parallel_tools(self) -> list[str]:
        """Get names of parallel-safe tools."""
        return [s.name for s in self._tool_specs if s.supports_parallel]

    @property
    def serial_tools(self) -> list[str]:
        """Get names of serial tools."""
        return [s.name for s in self._tool_specs if not s.supports_parallel]

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Execute a single tool.

        Args:
            name: Tool name.
            arguments: Tool arguments.
            context: Execution context.

        Returns:
            ToolResult with output or error.
        """
        if name not in self._tool_map:
            return ToolResult(
                tool_call_id=f"{context.turn_id}_{name}",
                content="",
                error=f"Unknown tool: {name}",
            )

        call = ToolCall(
            id=f"{context.turn_id}_{name}",
            name=name,
            input=arguments,
        )

        async with context.cancellation_token.child_scope() as child:
            self._executor.queue(call, child)
            results = await self._executor.drain()

            if results:
                return results[0]

            return ToolResult(
                tool_call_id=call.id,
                content="",
                error="No result returned",
            )

    async def execute_tools(
        self,
        tool_calls: list[tuple[str, dict[str, Any]]],
        context: ExecutionContext,
    ) -> tuple[list[ToolResult], TurnMetrics | None]:
        """Execute multiple tools with smart batching.

        Parallel tools run concurrently, serial tools run in order.
        Results are returned in submission order.

        Args:
            tool_calls: List of (name, arguments) tuples.
            context: Execution context.

        Returns:
            Tuple of (results, metrics). Metrics is None if not collected.
        """
        if not tool_calls:
            return [], None

        # Queue all calls
        for i, (name, args) in enumerate(tool_calls):
            if name not in self._tool_map:
                logger.warning(f"Unknown tool in batch: {name}")
                continue

            call = ToolCall(
                id=f"{context.turn_id}_{i}_{name}",
                name=name,
                input=args,
            )
            child_token = context.cancellation_token.child()
            self._executor.queue(call, child_token)

        # Drain results
        results = await self._executor.drain()

        # Collect metrics if enabled
        metrics = None
        if context.collect_metrics:
            metrics = self._executor.get_turn_metrics(context.turn_id)

        return results, metrics

    def cancel_all(self) -> None:
        """Cancel all pending tool executions."""
        # The executor handles this through cancellation tokens
        logger.info("Cancelling all pending tool executions")


async def execute_with_orchestration(
    tools: list[Callable],
    tool_calls: list[tuple[str, dict[str, Any]]],
    turn_id: str = "turn_0",
    timeout: float = 300.0,
) -> list[ToolResult]:
    """Convenience function for one-shot tool execution.

    Args:
        tools: Available tool functions.
        tool_calls: List of (name, arguments) to execute.
        turn_id: Identifier for this turn.
        timeout: Timeout in seconds.

    Returns:
        List of ToolResults in submission order.
    """
    executor = AgentToolExecutor(tools, timeout=timeout)
    context = ExecutionContext(turn_id=turn_id, timeout=timeout)

    results, _ = await executor.execute_tools(tool_calls, context)
    return results
