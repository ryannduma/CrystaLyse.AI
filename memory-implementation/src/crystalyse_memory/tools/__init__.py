# crystalyse_memory/tools/__init__.py
"""
Memory Tools for CrystaLyse.AI

Function tools for OpenAI Agents SDK to interact with memory systems.
Provides both computational caching tools and reasoning scratchpad tools.
"""

from .memory_tools import MEMORY_TOOLS
from .scratchpad_tools import SCRATCHPAD_TOOLS

__all__ = [
    "MEMORY_TOOLS",
    "SCRATCHPAD_TOOLS"
]

# Combined tool registry
ALL_TOOLS = {}
ALL_TOOLS.update(MEMORY_TOOLS)
ALL_TOOLS.update(SCRATCHPAD_TOOLS)

__all__.append("ALL_TOOLS")