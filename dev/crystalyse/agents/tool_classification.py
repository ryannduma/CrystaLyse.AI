"""Tool classification for orchestration.

Classifies tools as parallel (read-only) or serial (mutations)
to enable smart locking when using custom tool execution.

This module is designed to work independently of the OpenAI SDK,
enabling future migration to custom tool handling with proper
concurrency control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Tools that can run in parallel (read-only operations)
PARALLEL_TOOLS: frozenset[str] = frozenset(
    [
        # Database queries
        "query_optimade",
        # Web operations
        "web_search",
        # File reading
        "read_file",
        "read_artifact",
        "list_files",
        "list_artifacts",
        # Discovery cache (reads)
        "get_cached_computation",
        "search_previous_discoveries",
        "get_all_computations_for_formula",
    ]
)

# Tools that must run serially (mutations)
SERIAL_TOOLS: frozenset[str] = frozenset(
    [
        # Shell/code execution
        "run_shell_command",
        "execute_python",
        "execute_skill_script",
        # File writing
        "write_file",
        "write_artifact",
    ]
)


@dataclass
class ToolSpec:
    """Specification for a tool's execution characteristics.

    Attributes:
        name: Tool function name.
        handler: The actual tool function.
        supports_parallel: Whether this tool can run in parallel.
        description: Human-readable description.
    """

    name: str
    handler: Callable
    supports_parallel: bool = True
    description: str = ""


def classify_tool(tool_name: str) -> bool:
    """Determine if a tool supports parallel execution.

    Args:
        tool_name: Name of the tool function.

    Returns:
        True if the tool can run in parallel, False if it must be serial.
    """
    # Check explicit lists first
    if tool_name in PARALLEL_TOOLS:
        return True
    if tool_name in SERIAL_TOOLS:
        return False

    # Default to serial for unknown tools (safer)
    return False


def create_tool_spec(tool_func: Callable) -> ToolSpec:
    """Create a ToolSpec from a tool function.

    Args:
        tool_func: A function decorated with @function_tool.

    Returns:
        ToolSpec with classification.
    """
    name = getattr(tool_func, "__name__", str(tool_func))
    doc = getattr(tool_func, "__doc__", "") or ""

    return ToolSpec(
        name=name,
        handler=tool_func,
        supports_parallel=classify_tool(name),
        description=doc.split("\n")[0] if doc else "",
    )


def create_tool_specs(tools: list[Callable]) -> list[ToolSpec]:
    """Create ToolSpecs for a list of tool functions.

    Args:
        tools: List of tool functions.

    Returns:
        List of ToolSpec objects.
    """
    return [create_tool_spec(tool) for tool in tools]


def get_parallel_tools(specs: list[ToolSpec]) -> list[ToolSpec]:
    """Filter to only parallel-safe tools."""
    return [spec for spec in specs if spec.supports_parallel]


def get_serial_tools(specs: list[ToolSpec]) -> list[ToolSpec]:
    """Filter to only serial tools."""
    return [spec for spec in specs if not spec.supports_parallel]
