"""
Session Memory - Layer 1 of CrystaLyse Simple Memory System

Keeps recent commands and outputs in memory during the session.
Passes this context to the LLM on each turn.
No databases, no complexity - just like gemini-cli.
"""

from typing import List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionMemory:
    """
    Simple in-memory session context for the current conversation.
    
    Keeps track of recent interactions and provides context for the agent.
    Based on gemini-cli approach: simple, fast, no persistence required.
    """
    
    def __init__(self, max_interactions: int = 10):
        """
        Initialize session memory.
        
        Args:
            max_interactions: Maximum number of interactions to keep in memory
        """
        self.history: List[Tuple[str, str, datetime]] = []  # (query, response, timestamp)
        self.max_interactions = max_interactions
        self.session_start = datetime.now()
        
        logger.info(f"SessionMemory initialized with max_interactions: {max_interactions}")
    
    def add_interaction(self, query: str, response: str) -> None:
        """
        Add an interaction to session memory.
        
        Args:
            query: User query
            response: Agent response
        """
        timestamp = datetime.now()
        self.history.append((query, response, timestamp))
        
        # Keep only the last max_interactions
        if len(self.history) > self.max_interactions:
            self.history.pop(0)
        
        logger.debug(f"Added interaction to session memory (total: {len(self.history)})")
    
    def get_context(self, last_n: int = 3) -> str:
        """
        Get recent conversation context as a formatted string.
        
        Args:
            last_n: Number of recent interactions to include
            
        Returns:
            Formatted context string for the agent
        """
        if not self.history:
            return "No previous conversation in this session."
        
        # Get the last n interactions
        recent_history = self.history[-last_n:]
        
        context_lines = []
        for query, response, timestamp in recent_history:
            # Format timestamp
            time_str = timestamp.strftime("%H:%M")
            
            # Truncate long responses for context
            truncated_response = response[:200] + "..." if len(response) > 200 else response
            
            context_lines.append(f"[{time_str}] User: {query}")
            context_lines.append(f"[{time_str}] CrystaLyse: {truncated_response}")
        
        return "\n".join(context_lines)
    
    def get_session_summary(self) -> dict:
        """
        Get a summary of the current session.
        
        Returns:
            Dictionary with session statistics
        """
        return {
            "total_interactions": len(self.history),
            "session_duration": str(datetime.now() - self.session_start),
            "last_interaction": self.history[-1][2] if self.history else None,
            "session_start": self.session_start
        }
    
    def clear(self) -> None:
        """Clear all session memory."""
        self.history.clear()
        self.session_start = datetime.now()
        logger.info("Session memory cleared")
    
    def search_history(self, query: str) -> List[Tuple[str, str, datetime]]:
        """
        Search through session history for relevant interactions.
        
        Args:
            query: Search query
            
        Returns:
            List of matching interactions
        """
        query_lower = query.lower()
        matches = []
        
        for user_query, response, timestamp in self.history:
            if (query_lower in user_query.lower() or 
                query_lower in response.lower()):
                matches.append((user_query, response, timestamp))
        
        return matches 