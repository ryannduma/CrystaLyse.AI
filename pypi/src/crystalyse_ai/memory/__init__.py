"""
Simple File-Based Memory System for CrystaLyse.AI

A gemini-cli inspired memory system that uses simple files + smart context
instead of complex databases. Provides 4 layers:
1. Session Memory - Current conversation context
2. Discovery Cache - Cached material properties  
3. User Memory - User preferences and notes
4. Cross-Session Context - Auto-generated insights

Philosophy: Simple files + smart context beats complex architectures.
"""

from .session_memory import SessionMemory
from .discovery_cache import DiscoveryCache
from .user_memory import UserMemory
from .cross_session_context import CrossSessionContext
from .crystalyse_memory import CrystaLyseMemory
from .memory_tools import (
    save_to_memory,
    search_memory,
    save_discovery,
    search_discoveries,
    get_memory_tools
)

__all__ = [
    "SessionMemory",
    "DiscoveryCache", 
    "UserMemory",
    "CrossSessionContext",
    "CrystaLyseMemory",
    "save_to_memory",
    "search_memory",
    "save_discovery",
    "search_discoveries",
    "get_memory_tools"
] 
