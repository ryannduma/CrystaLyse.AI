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

from .long_term.discovery_store import DiscoveryStore
from .long_term.user_store import UserProfileStore
from .long_term.knowledge_graph import MaterialKnowledgeGraph

from .tools.memory_tools import MEMORY_TOOLS
from .tools.scratchpad_tools import SCRATCHPAD_TOOLS

__version__ = "0.2.0"
__author__ = "CrystaLyse.AI Development Team"

# Main memory components
__all__ = [
    # Short-term memory classes
    "WorkingMemory",
    "AgentScratchpad", 
    "DualWorkingMemory",
    "ConversationManager",
    "ConversationMessage",
    "SessionContextManager",
    "SessionState",
    
    # Long-term memory classes
    "DiscoveryStore",
    "UserProfileStore",
    "MaterialKnowledgeGraph",
    
    # Tool collections
    "MEMORY_TOOLS",
    "SCRATCHPAD_TOOLS",
    
    # Utility functions
    "create_dual_memory",
    "create_complete_memory_system",
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


async def create_complete_memory_system(
    session_id: str,
    user_id: str,
    cache_dir=None,
    scratchpad_dir=None,
    discovery_persist_dir=None,
    user_db_path=None,
    neo4j_config=None,
    redis_config=None
):
    """
    Create complete memory system with all components.
    
    Args:
        session_id: Unique session identifier
        user_id: User identifier
        cache_dir: Directory for computational cache storage
        scratchpad_dir: Directory for scratchpad files
        discovery_persist_dir: Directory for discovery vector store
        user_db_path: Path to user profile database
        neo4j_config: Neo4j configuration dict
        redis_config: Redis configuration dict
        
    Returns:
        Dictionary with all memory components
    """
    # Short-term memory
    dual_memory = create_dual_memory(
        session_id=session_id,
        user_id=user_id,
        cache_dir=cache_dir,
        scratchpad_dir=scratchpad_dir
    )
    
    # Conversation manager
    conv_config = redis_config or {}
    conversation_manager = ConversationManager(
        redis_url=conv_config.get('url', 'redis://localhost:6379'),
        fallback_dir=conv_config.get('fallback_dir')
    )
    await conversation_manager.initialize()
    
    # Session context
    session_manager = SessionContextManager()
    
    # Long-term memory
    discovery_store = DiscoveryStore(persist_directory=discovery_persist_dir)
    user_store = UserProfileStore(db_path=user_db_path)
    
    # Knowledge graph
    neo4j_config = neo4j_config or {}
    knowledge_graph = MaterialKnowledgeGraph(
        uri=neo4j_config.get('uri', 'bolt://localhost:7687'),
        username=neo4j_config.get('username', 'neo4j'),
        password=neo4j_config.get('password', 'password')
    )
    await knowledge_graph.initialize()
    
    # Create user profile if needed
    await user_store.create_user_profile(user_id)
    
    return {
        'dual_working_memory': dual_memory,
        'conversation_manager': conversation_manager,
        'session_manager': session_manager,
        'discovery_store': discovery_store,
        'user_store': user_store,
        'knowledge_graph': knowledge_graph,
        'session_id': session_id,
        'user_id': user_id
    }


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