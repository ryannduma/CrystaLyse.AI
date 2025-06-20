# crystalyse_memory/__init__.py
"""
CrystaLyse.AI Memory System

A comprehensive memory architecture for materials discovery AI agents,
providing both computational caching and reasoning scratchpad capabilities.
"""

from .short_term.working_memory import WorkingMemory
from .short_term.agent_scratchpad import AgentScratchpad
from .short_term.dual_working_memory import DualWorkingMemory
from .short_term.conversation_manager import ConversationManager, ConversationMessage
from .short_term.session_context import SessionContextManager, SessionState

from .tools.memory_tools import MEMORY_TOOLS
from .tools.scratchpad_tools import SCRATCHPAD_TOOLS

__version__ = "0.1.0"
__author__ = "CrystaLyse.AI Development Team"

# Main memory components
__all__ = [
    # Core memory classes
    "WorkingMemory",
    "AgentScratchpad", 
    "DualWorkingMemory",
    "ConversationManager",
    "ConversationMessage",
    "SessionContextManager",
    "SessionState",
    
    # Tool collections
    "MEMORY_TOOLS",
    "SCRATCHPAD_TOOLS",
    
    # Utility functions
    "create_dual_memory",
    "get_all_tools"
]


def create_dual_memory(
    session_id: str,
    user_id: str,
    cache_dir=None,
    scratchpad_dir=None,
    max_cache_age_hours: int = 24
) -> DualWorkingMemory:
    """
    Convenience function to create a dual working memory instance.
    
    Args:
        session_id: Unique session identifier
        user_id: User identifier
        cache_dir: Directory for computational cache storage
        scratchpad_dir: Directory for scratchpad files
        max_cache_age_hours: Maximum age for cached items in hours
        
    Returns:
        Configured DualWorkingMemory instance
    """
    return DualWorkingMemory(
        session_id=session_id,
        user_id=user_id,
        cache_dir=cache_dir,
        scratchpad_dir=scratchpad_dir,
        max_cache_age_hours=max_cache_age_hours
    )


def get_all_tools():
    """
    Get all memory and scratchpad tools for agent integration.
    
    Returns:
        Dictionary of all available tools
    """
    all_tools = {}
    all_tools.update(MEMORY_TOOLS)
    all_tools.update(SCRATCHPAD_TOOLS)
    return all_tools