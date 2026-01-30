"""Metrics for tool execution observability."""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ToolMetrics:
    """Metrics for a single tool execution."""

    tool_name: str
    tool_call_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    success: bool = False
    parallel: bool = False
    error: str | None = None

    @property
    def duration_ms(self) -> float | None:
        """Duration in milliseconds."""
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return None

    def complete(self, success: bool, error: str | None = None) -> None:
        """Mark tool execution as complete."""
        self.end_time = datetime.now()
        self.success = success
        self.error = error


@dataclass
class TurnMetrics:
    """Aggregated metrics for a single agent turn."""

    turn_id: str
    start_time: datetime = field(default_factory=datetime.now)
    tool_calls: list[ToolMetrics] = field(default_factory=list)

    @property
    def parallel_count(self) -> int:
        """Number of parallel tool executions."""
        return sum(1 for t in self.tool_calls if t.parallel)

    @property
    def serial_count(self) -> int:
        """Number of serial tool executions."""
        return sum(1 for t in self.tool_calls if not t.parallel)

    @property
    def total_duration_ms(self) -> float:
        """Total tool execution time in milliseconds."""
        return sum(t.duration_ms or 0 for t in self.tool_calls)

    @property
    def success_count(self) -> int:
        """Number of successful tool calls."""
        return sum(1 for t in self.tool_calls if t.success)

    def add_tool(self, metrics: ToolMetrics) -> None:
        """Add tool metrics to this turn."""
        self.tool_calls.append(metrics)

    def log_summary(self) -> None:
        """Log a summary of this turn's metrics."""
        logger.info(
            f"Turn {self.turn_id}: "
            f"{len(self.tool_calls)} tools "
            f"({self.parallel_count} parallel, {self.serial_count} serial), "
            f"{self.success_count}/{len(self.tool_calls)} succeeded, "
            f"{self.total_duration_ms:.0f}ms total"
        )
