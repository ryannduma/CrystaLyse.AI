"""
CrystaLyse Memory System - Main Memory Class

Combines all 4 memory layers into a cohesive system:
1. Session Memory - Current conversation context
2. Discovery Cache - Cached material properties
3. User Memory - User preferences and notes
4. Cross-Session Context - Auto-generated insights

Simple files + smart context beats complex architectures.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from .session_memory import SessionMemory
from .discovery_cache import DiscoveryCache
from .user_memory import UserMemory
from .cross_session_context import CrossSessionContext

logger = logging.getLogger(__name__)


class CrystaLyseMemory:
    """
    Main memory system for CrystaLyse.AI agent.
    
    Provides a unified interface to all memory layers while maintaining
    the simplicity of file-based storage. Each layer serves a specific
    purpose in the agent's memory architecture.
    """
    
    def __init__(self, user_id: str = "default", memory_dir: Optional[Path] = None):
        """
        Initialize CrystaLyse memory system.
        
        Args:
            user_id: User identifier for personalized memory
            memory_dir: Directory for memory files (default: ~/.crystalyse)
        """
        self.user_id = user_id
        
        if memory_dir is None:
            memory_dir = Path.home() / ".crystalyse"
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all memory layers
        self.session_memory = SessionMemory()
        self.discovery_cache = DiscoveryCache(self.memory_dir)
        self.user_memory = UserMemory(self.memory_dir, user_id)
        self.cross_session_context = CrossSessionContext(self.memory_dir, user_id)
        
        logger.info(f"CrystaLyseMemory initialized for user {user_id}")
    
    def get_context_for_agent(self) -> str:
        """
        Get comprehensive context for the agent.
        
        Returns:
            Formatted context string combining all memory layers
        """
        context_parts = []
        
        # Session context (Layer 1)
        session_context = self.session_memory.get_context()
        if session_context and session_context != "No previous conversation in this session.":
            context_parts.append("## Previous Conversation")
            context_parts.append(session_context)
        
        # User preferences and memory (Layer 3)
        user_context = self.user_memory.get_context_summary()
        if user_context and user_context != "No user memory available.":
            context_parts.append("## User Profile")
            context_parts.append(user_context)
        
        # Cross-session insights (Layer 4)
        insights_context = self.cross_session_context.get_context_summary()
        if insights_context and insights_context != "No recent research context available.":
            context_parts.append("## Recent Research Context")
            context_parts.append(insights_context)
        
        # Discovery cache stats (Layer 2)
        cache_stats = self.discovery_cache.get_statistics()
        if cache_stats["total_entries"] > 0:
            recent_discoveries = self.discovery_cache.get_recent_discoveries(limit=3)
            if recent_discoveries:
                context_parts.append("## Recent Discoveries")
                for discovery in recent_discoveries:
                    formula = discovery.get("formula", "Unknown")
                    cached_at = discovery.get("cached_at", "Unknown time")
                    context_parts.append(f"- {formula} (cached at {cached_at})")
        
        if context_parts:
            return "\n\n".join(context_parts)
        else:
            return "No previous context available."
    
    def add_interaction(self, query: str, response: str) -> None:
        """
        Add an interaction to session memory.
        
        Args:
            query: User query
            response: Agent response
        """
        self.session_memory.add_interaction(query, response)
    
    def save_discovery(self, formula: str, properties: Dict[str, Any]) -> None:
        """
        Save a discovery to the cache.
        
        Args:
            formula: Chemical formula
            properties: Material properties
        """
        self.discovery_cache.save_result(formula, properties)
    
    def get_cached_discovery(self, formula: str) -> Optional[Dict[str, Any]]:
        """
        Get cached discovery result.
        
        Args:
            formula: Chemical formula
            
        Returns:
            Cached result if available, None otherwise
        """
        return self.discovery_cache.get_cached_result(formula)
    
    def save_to_memory(self, fact: str, section: str = "Important Notes") -> None:
        """
        Save a fact to user memory.
        
        Args:
            fact: Fact to save
            section: Section to save to
        """
        self.user_memory.add_fact(fact, section)
    
    def search_memory(self, query: str) -> List[str]:
        """
        Search user memory for relevant information.
        
        Args:
            query: Search query
            
        Returns:
            List of relevant memory entries
        """
        return self.user_memory.search_memory(query)
    
    def search_discoveries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search discoveries cache.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching discoveries
        """
        return self.discovery_cache.search_similar(query, limit)
    
    def generate_weekly_summary(self) -> str:
        """
        Generate weekly summary of discoveries and patterns.
        
        Returns:
            Weekly summary as markdown string
        """
        return self.cross_session_context.generate_weekly_summary()
    
    def auto_generate_insights(self) -> Optional[str]:
        """
        Auto-generate insights if needed.
        
        Returns:
            Generated insights if created, None otherwise
        """
        return self.cross_session_context.auto_generate_if_needed()
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.
        
        Returns:
            Dictionary with memory statistics
        """
        session_stats = self.session_memory.get_session_summary()
        cache_stats = self.discovery_cache.get_statistics()
        
        return {
            "user_id": self.user_id,
            "memory_directory": str(self.memory_dir),
            "session": session_stats,
            "cache": cache_stats,
            "user_preferences": len(self.user_memory.get_preferences()),
            "research_interests": len(self.user_memory.get_research_interests()),
            "recent_discoveries": len(self.user_memory.get_recent_discoveries()),
            "insights_available": self.cross_session_context.insights_file.exists()
        }
    
    def clear_session(self) -> None:
        """Clear current session memory."""
        self.session_memory.clear()
    
    def export_memory(self, export_dir: Path) -> None:
        """
        Export all memory to a directory.
        
        Args:
            export_dir: Directory to export to
        """
        export_dir = Path(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export discovery cache
        self.discovery_cache.export_cache(export_dir / "discoveries.json")
        
        # Copy user memory and insights files
        try:
            import shutil
            if self.user_memory.memory_file.exists():
                shutil.copy2(self.user_memory.memory_file, export_dir / f"memory_{self.user_id}.md")
            if self.cross_session_context.insights_file.exists():
                shutil.copy2(self.cross_session_context.insights_file, export_dir / f"insights_{self.user_id}.md")
            
            logger.info(f"Memory exported to {export_dir}")
        except Exception as e:
            logger.error(f"Failed to export memory: {e}")
    
    def import_memory(self, import_dir: Path, merge: bool = True) -> None:
        """
        Import memory from a directory.
        
        Args:
            import_dir: Directory to import from
            merge: Whether to merge with existing memory
        """
        import_dir = Path(import_dir)
        
        # Import discovery cache
        discoveries_file = import_dir / "discoveries.json"
        if discoveries_file.exists():
            self.discovery_cache.import_cache(discoveries_file, merge)
        
        # Import user memory file
        user_memory_file = import_dir / f"memory_{self.user_id}.md"
        if user_memory_file.exists():
            try:
                import shutil
                if not merge:
                    # Replace existing file
                    shutil.copy2(user_memory_file, self.user_memory.memory_file)
                else:
                    # Merge content (simplified)
                    with open(user_memory_file, "r", encoding="utf-8") as f:
                        imported_content = f.read()
                    
                    # Add imported content to Important Notes section
                    self.user_memory.add_fact(f"Imported memory content: {imported_content[:100]}...")
                    
                logger.info(f"User memory imported from {user_memory_file}")
            except Exception as e:
                logger.error(f"Failed to import user memory: {e}")
    
    def cleanup(self) -> None:
        """Cleanup memory system resources."""
        # Clear session memory
        self.session_memory.clear()
        
        # Auto-generate insights if needed
        self.auto_generate_insights()
        
        logger.info("Memory system cleanup completed") 