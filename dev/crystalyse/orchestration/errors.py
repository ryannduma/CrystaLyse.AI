"""Error classes for tool execution."""


class ToolExecutionError(Exception):
    """Base class for tool execution errors."""

    pass


class ToolTimeoutError(ToolExecutionError):
    """Tool exceeded timeout."""

    def __init__(self, tool_name: str, timeout_seconds: int) -> None:
        super().__init__(f"{tool_name} timed out after {timeout_seconds}s")
        self.tool_name = tool_name
        self.timeout = timeout_seconds


class ToolCancelledError(ToolExecutionError):
    """Tool was cancelled by user or system."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"{tool_name} was cancelled")
        self.tool_name = tool_name
