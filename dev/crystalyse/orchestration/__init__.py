"""Orchestration package for parallel tool execution."""

from .cancellation import CancellationToken
from .errors import ToolCancelledError, ToolExecutionError, ToolTimeoutError
from .executor import ParallelToolExecutor, ToolCall, ToolResult, ToolSpec
from .futures import OrderedFutures
from .locking import AsyncRwLock
from .metrics import ToolMetrics, TurnMetrics

__all__ = [
    # Core executor
    "ParallelToolExecutor",
    "ToolSpec",
    "ToolCall",
    "ToolResult",
    # Primitives
    "OrderedFutures",
    "AsyncRwLock",
    "CancellationToken",
    # Observability
    "ToolMetrics",
    "TurnMetrics",
    # Errors
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolCancelledError",
]
