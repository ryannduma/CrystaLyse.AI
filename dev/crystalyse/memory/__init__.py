"""Memory system for Crystalyse.

Provides four components:

1. Session persistence (SQLite-backed via OpenAI SDK)
   - get_session(): Get/create a session for conversation history
   - list_sessions(): List all saved sessions
   - delete_session(): Delete a session

2. Discovery cache (SQLite-backed)
   - DiscoveryCacheV2: Cache expensive computation results
   - Keyed by (formula, computation_type, parameters_hash)

3. Project memory (CRYSTALYSE.md files)
   - load_project_memory(): Load project-specific instructions
   - find_project_memory(): Find memory files in directory tree

4. Context compaction
   - ContextManager: Summarise old messages when approaching token limits
   - CompactionConfig: Configure compaction thresholds
"""

from .compaction import (
    CompactionConfig,
    CompactionResult,
    ContextManager,
    Message,
    estimate_tokens,
)
from .discovery_cache import CachedDiscovery, DiscoveryCache
from .project_memory import (
    find_project_memory,
    get_project_memory_paths,
    load_project_memory,
)
from .session import SessionInfo, delete_session, get_session, list_sessions

__all__ = [
    # Session
    "get_session",
    "list_sessions",
    "delete_session",
    "SessionInfo",
    # Discovery Cache
    "DiscoveryCache",
    "CachedDiscovery",
    # Project Memory
    "load_project_memory",
    "find_project_memory",
    "get_project_memory_paths",
    # Context Compaction
    "ContextManager",
    "CompactionConfig",
    "CompactionResult",
    "Message",
    "estimate_tokens",
]
