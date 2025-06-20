# crystalyse_memory/short_term/session_context.py
"""
Session Context Manager for CrystaLyse.AI Memory System

Manages session-specific context including user preferences, active research state,
and session metadata for memory-enhanced agents.
"""

from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import json
import logging
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Current session state and context."""
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    
    # Research context
    current_query: Optional[str] = None
    active_materials: List[str] = field(default_factory=list)
    research_focus: Optional[str] = None  # e.g., "perovskites", "superconductors"
    
    # Agent state
    agent_mode: str = "rigorous"  # "rigorous", "creative"
    reasoning_depth: str = "standard"  # "quick", "standard", "deep"
    
    # User preferences (session-specific overrides)
    preferred_tools: List[str] = field(default_factory=list)
    output_format: str = "detailed"  # "brief", "detailed", "technical"
    include_visualisations: bool = True
    
    # Session metadata
    query_count: int = 0
    tools_used: Set[str] = field(default_factory=set)
    materials_discovered: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert set to list for JSON serialisation
        data['tools_used'] = list(self.tools_used)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create from dictionary."""
        # Convert list back to set
        if 'tools_used' in data:
            data['tools_used'] = set(data['tools_used'])
        return cls(**data)


class SessionContextManager:
    """
    Manages session context and state for memory-enhanced agents.
    
    Tracks user preferences, research state, and session metadata
    to provide relevant context for agent decision-making.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialise session context manager.
        
        Args:
            storage_dir: Directory for persistent session storage
        """
        self.storage_dir = storage_dir or Path("./memory/sessions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Active session states
        self.active_sessions: Dict[str, SessionState] = {}
        
        # Session timeout (inactive sessions)
        self.session_timeout = timedelta(hours=24)
        
        logger.info(f"SessionContextManager initialised with storage: {self.storage_dir}")
    
    def create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> SessionState:
        """
        Create new session context.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID (generated if not provided)
            initial_context: Initial context data
            
        Returns:
            Created session state
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        timestamp = datetime.now().isoformat()
        
        session_state = SessionState(
            session_id=session_id,
            user_id=user_id,
            created_at=timestamp,
            last_active=timestamp
        )
        
        # Apply initial context if provided
        if initial_context:
            self._apply_context_updates(session_state, initial_context)
        
        self.active_sessions[session_id] = session_state
        self._save_session(session_state)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_state
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get session state by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session state if found, None otherwise
        """
        # Check active sessions first
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Check if session has expired
            last_active = datetime.fromisoformat(session.last_active)
            if datetime.now() - last_active > self.session_timeout:
                self._expire_session(session_id)
                return None
            
            return session
        
        # Try to load from storage
        return self._load_session(session_id)
    
    def update_session_activity(self, session_id: str) -> None:
        """Update last activity timestamp for session."""
        session = self.get_session(session_id)
        if session:
            session.last_active = datetime.now().isoformat()
            self._save_session(session)
    
    def update_session_context(
        self,
        session_id: str,
        context_updates: Dict[str, Any]
    ) -> Optional[SessionState]:
        """
        Update session context with new data.
        
        Args:
            session_id: Session identifier
            context_updates: Dictionary of context updates
            
        Returns:
            Updated session state if successful
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        self._apply_context_updates(session, context_updates)
        session.last_active = datetime.now().isoformat()
        
        self._save_session(session)
        return session
    
    def _apply_context_updates(self, session: SessionState, updates: Dict[str, Any]) -> None:
        """Apply context updates to session state."""
        for key, value in updates.items():
            if hasattr(session, key):
                if key == 'tools_used' and isinstance(value, list):
                    # Add to existing set
                    session.tools_used.update(value)
                elif key in ['active_materials', 'materials_discovered'] and isinstance(value, list):
                    # Extend existing list
                    current_list = getattr(session, key)
                    current_list.extend(v for v in value if v not in current_list)
                else:
                    setattr(session, key, value)
    
    def start_query(
        self,
        session_id: str,
        query: str,
        research_focus: Optional[str] = None
    ) -> Optional[SessionState]:
        """
        Start a new query in the session.
        
        Args:
            session_id: Session identifier
            query: The research query
            research_focus: Optional research focus area
            
        Returns:
            Updated session state
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        session.current_query = query
        session.query_count += 1
        
        if research_focus:
            session.research_focus = research_focus
        
        session.last_active = datetime.now().isoformat()
        self._save_session(session)
        
        logger.debug(f"Started query {session.query_count} in session {session_id}")
        return session
    
    def log_tool_usage(self, session_id: str, tool_name: str) -> None:
        """Log tool usage in session."""
        session = self.get_session(session_id)
        if session:
            session.tools_used.add(tool_name)
            self._save_session(session)
    
    def add_discovered_material(self, session_id: str, material: str) -> None:
        """Add discovered material to session."""
        session = self.get_session(session_id)
        if session and material not in session.materials_discovered:
            session.materials_discovered.append(material)
            self._save_session(session)
    
    def set_agent_mode(self, session_id: str, mode: str) -> None:
        """Set agent mode for session."""
        session = self.get_session(session_id)
        if session:
            session.agent_mode = mode
            self._save_session(session)
            logger.debug(f"Set agent mode to {mode} for session {session_id}")
    
    def set_reasoning_depth(self, session_id: str, depth: str) -> None:
        """Set reasoning depth for session."""
        session = self.get_session(session_id)
        if session:
            session.reasoning_depth = depth
            self._save_session(session)
            logger.debug(f"Set reasoning depth to {depth} for session {session_id}")
    
    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[SessionState]:
        """
        Get recent sessions for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent session states
        """
        user_sessions = []
        
        # Check active sessions
        for session in self.active_sessions.values():
            if session.user_id == user_id:
                user_sessions.append(session)
        
        # Load recent sessions from storage
        for session_file in self.storage_dir.glob(f"session_*.json"):
            if len(user_sessions) >= limit:
                break
                
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('user_id') == user_id:
                    session = SessionState.from_dict(data)
                    if session.session_id not in [s.session_id for s in user_sessions]:
                        user_sessions.append(session)
                        
            except Exception as e:
                logger.warning(f"Failed to load session file {session_file}: {e}")
        
        # Sort by last activity (most recent first)
        user_sessions.sort(key=lambda s: s.last_active, reverse=True)
        
        return user_sessions[:limit]
    
    def get_session_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        created = datetime.fromisoformat(session.created_at)
        last_active = datetime.fromisoformat(session.last_active)
        duration = last_active - created
        
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "duration_minutes": int(duration.total_seconds() / 60),
            "query_count": session.query_count,
            "tools_used_count": len(session.tools_used),
            "tools_used": list(session.tools_used),
            "materials_discovered_count": len(session.materials_discovered),
            "materials_discovered": session.materials_discovered,
            "current_mode": session.agent_mode,
            "research_focus": session.research_focus
        }
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_count = 0
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            last_active = datetime.fromisoformat(session.last_active)
            if datetime.now() - last_active > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._expire_session(session_id)
            expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired sessions")
        return expired_count
    
    def _expire_session(self, session_id: str) -> None:
        """Expire a session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            self._save_session(session)  # Final save
            del self.active_sessions[session_id]
            logger.debug(f"Expired session {session_id}")
    
    def _save_session(self, session: SessionState) -> None:
        """Save session to persistent storage."""
        try:
            session_file = self.storage_dir / f"session_{session.session_id}.json"
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
    
    def _load_session(self, session_id: str) -> Optional[SessionState]:
        """Load session from persistent storage."""
        try:
            session_file = self.storage_dir / f"session_{session_id}.json"
            
            if not session_file.exists():
                return None
            
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = SessionState.from_dict(data)
            
            # Check if session has expired
            last_active = datetime.fromisoformat(session.last_active)
            if datetime.now() - last_active > self.session_timeout:
                return None
            
            # Add to active sessions
            self.active_sessions[session_id] = session
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def close(self) -> None:
        """Close and save all active sessions."""
        for session in self.active_sessions.values():
            self._save_session(session)
        
        self.active_sessions.clear()
        logger.info("SessionContextManager closed")
    
    def get_context_for_agent(self, session_id: str) -> Dict[str, Any]:
        """
        Get session context formatted for agent use.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Context dictionary for agent
        """
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "agent_mode": session.agent_mode,
            "reasoning_depth": session.reasoning_depth,
            "research_focus": session.research_focus,
            "current_query": session.current_query,
            "output_format": session.output_format,
            "include_visualisations": session.include_visualisations,
            "tools_used_in_session": list(session.tools_used),
            "materials_discovered_in_session": session.materials_discovered,
            "query_count": session.query_count
        }