"""
Crystalyse Agent Module V2

This module provides the skills-based materials discovery agent.
Two modes are supported:
- Creative (default): Fast exploration with gpt-5-mini
- Rigorous: Thorough analysis with gpt-5.2

Also provides custom tool execution infrastructure for future use
when moving away from SDK-managed tool handling.
"""

from .agent import MaterialsAgent
from .tool_classification import (
    PARALLEL_TOOLS,
    SERIAL_TOOLS,
    ToolSpec,
    classify_tool,
    create_tool_spec,
    create_tool_specs,
)
from .tool_executor import AgentToolExecutor, ExecutionContext, execute_with_orchestration

# Backward compatibility alias
EnhancedCrystaLyseAgent = MaterialsAgent

__all__ = [
    # Agent
    "MaterialsAgent",
    "EnhancedCrystaLyseAgent",
    # Tool classification
    "ToolSpec",
    "PARALLEL_TOOLS",
    "SERIAL_TOOLS",
    "classify_tool",
    "create_tool_spec",
    "create_tool_specs",
    # Tool execution
    "AgentToolExecutor",
    "ExecutionContext",
    "execute_with_orchestration",
]
