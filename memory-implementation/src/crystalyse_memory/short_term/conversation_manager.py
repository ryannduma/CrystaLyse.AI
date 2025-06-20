# crystalyse_memory/short_term/conversation_manager.py
"""
Conversation Manager for CrystaLyse.AI Memory System

Manages conversation history using Redis for persistence and performance.
Provides conversation context for memory-enhanced agents.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging
import asyncio
from dataclasses import dataclass, asdict
from pathlib import Path

# Redis will be optional dependency - fallback to local storage
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Single conversation message."""
    timestamp: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    session_id: str
    user_id: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary."""
        return cls(**data)


class ConversationManager:
    """
    Manages conversation history with Redis backend and local fallback.
    
    Provides persistent storage of conversation context for memory-enhanced
    agents, enabling continuity across sessions.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        fallback_dir: Optional[Path] = None,
        max_history_length: int = 1000,
        message_ttl_hours: int = 168  # 1 week
    ):
        """
        Initialise conversation manager.
        
        Args:
            redis_url: Redis connection URL
            fallback_dir: Directory for local storage fallback
            max_history_length: Maximum messages to keep per session
            message_ttl_hours: Time-to-live for messages in hours
        """
        self.redis_url = redis_url
        self.fallback_dir = fallback_dir or Path("./memory/conversations")
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_history_length = max_history_length
        self.message_ttl = timedelta(hours=message_ttl_hours)
        
        self.redis_client: Optional[redis.Redis] = None
        self.use_redis = REDIS_AVAILABLE
        
        # Local fallback storage
        self.local_conversations: Dict[str, List[ConversationMessage]] = {}
        
        logger.info(f"ConversationManager initialised (Redis: {self.use_redis})")
    
    async def initialize(self) -> None:
        """Initialize Redis connection if available."""
        if self.use_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using local fallback.")
                self.use_redis = False
                self.redis_client = None
        else:
            logger.info("Using local conversation storage")
    
    async def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add message to conversation history.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata dictionary
        """
        timestamp = datetime.now().isoformat()
        
        message = ConversationMessage(
            timestamp=timestamp,
            role=role,
            content=content,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        if self.use_redis and self.redis_client:
            await self._add_message_redis(message)
        else:
            await self._add_message_local(message)
        
        logger.debug(f"Added {role} message to session {session_id}")
    
    async def _add_message_redis(self, message: ConversationMessage) -> None:
        """Add message using Redis backend."""
        try:
            # Store message in session-specific list
            session_key = f"conversation:{message.session_id}"
            message_json = json.dumps(message.to_dict())
            
            pipe = self.redis_client.pipeline()
            
            # Add message to list
            pipe.lpush(session_key, message_json)
            
            # Trim list to max length
            pipe.ltrim(session_key, 0, self.max_history_length - 1)
            
            # Set TTL
            pipe.expire(session_key, int(self.message_ttl.total_seconds()))
            
            # Index by user for cross-session retrieval
            user_key = f"user_sessions:{message.user_id}"
            pipe.sadd(user_key, message.session_id)
            pipe.expire(user_key, int(self.message_ttl.total_seconds()))
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Redis add_message failed: {e}. Falling back to local storage.")
            await self._add_message_local(message)
    
    async def _add_message_local(self, message: ConversationMessage) -> None:
        """Add message using local storage."""
        session_id = message.session_id
        
        if session_id not in self.local_conversations:
            self.local_conversations[session_id] = []
        
        # Add to front of list (newest first)
        self.local_conversations[session_id].insert(0, message)
        
        # Trim to max length
        if len(self.local_conversations[session_id]) > self.max_history_length:
            self.local_conversations[session_id] = self.local_conversations[session_id][:self.max_history_length]
        
        # Persist to file
        await self._save_session_to_file(session_id)
    
    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        role_filter: Optional[str] = None
    ) -> List[ConversationMessage]:
        """
        Get conversation history for session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            role_filter: Filter by role ('user', 'assistant', 'system')
            
        Returns:
            List of conversation messages (newest first)
        """
        if self.use_redis and self.redis_client:
            messages = await self._get_history_redis(session_id, limit)
        else:
            messages = await self._get_history_local(session_id, limit)
        
        # Apply role filter if specified
        if role_filter:
            messages = [msg for msg in messages if msg.role == role_filter]
        
        logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")
        return messages
    
    async def _get_history_redis(self, session_id: str, limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get history using Redis backend."""
        try:
            session_key = f"conversation:{session_id}"
            
            # Get messages (newest first)
            end_index = (limit - 1) if limit else -1
            message_jsons = await self.redis_client.lrange(session_key, 0, end_index)
            
            messages = []
            for msg_json in message_jsons:
                try:
                    msg_data = json.loads(msg_json)
                    messages.append(ConversationMessage.from_dict(msg_data))
                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Redis get_history failed: {e}. Falling back to local storage.")
            return await self._get_history_local(session_id, limit)
    
    async def _get_history_local(self, session_id: str, limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get history using local storage."""
        # Load from file if not in memory
        if session_id not in self.local_conversations:
            await self._load_session_from_file(session_id)
        
        messages = self.local_conversations.get(session_id, [])
        
        if limit:
            messages = messages[:limit]
        
        return messages
    
    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[str]:
        """
        Get recent session IDs for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            
        Returns:
            List of session IDs (most recent first)
        """
        if self.use_redis and self.redis_client:
            return await self._get_user_sessions_redis(user_id, limit)
        else:
            return await self._get_user_sessions_local(user_id, limit)
    
    async def _get_user_sessions_redis(self, user_id: str, limit: int) -> List[str]:
        """Get user sessions using Redis."""
        try:
            user_key = f"user_sessions:{user_id}"
            session_ids = await self.redis_client.smembers(user_key)
            
            # Convert bytes to strings and sort by most recent activity
            session_list = [sid.decode() if isinstance(sid, bytes) else sid for sid in session_ids]
            
            # For simplicity, return first N sessions
            # In production, would sort by last activity timestamp
            return session_list[:limit]
            
        except Exception as e:
            logger.error(f"Redis get_user_sessions failed: {e}")
            return []
    
    async def _get_user_sessions_local(self, user_id: str, limit: int) -> List[str]:
        """Get user sessions using local storage."""
        # Find sessions for this user
        user_sessions = []
        
        for session_id, messages in self.local_conversations.items():
            if messages and messages[0].user_id == user_id:
                user_sessions.append((session_id, messages[0].timestamp))
        
        # Sort by timestamp (newest first)
        user_sessions.sort(key=lambda x: x[1], reverse=True)
        
        return [session_id for session_id, _ in user_sessions[:limit]]
    
    async def get_context_summary(self, session_id: str, max_tokens: int = 1000) -> str:
        """
        Get a summarised context from conversation history.
        
        Args:
            session_id: Session identifier
            max_tokens: Approximate maximum tokens for summary
            
        Returns:
            Formatted context summary
        """
        messages = await self.get_history(session_id, limit=20)
        
        if not messages:
            return ""
        
        # Build context summary
        context_parts = []
        current_length = 0
        
        for msg in reversed(messages):  # Chronological order
            msg_text = f"{msg.role}: {msg.content}"
            
            # Rough token estimation (4 chars per token)
            if current_length + len(msg_text) > max_tokens * 4:
                break
            
            context_parts.append(msg_text)
            current_length += len(msg_text)
        
        return "\n".join(context_parts)
    
    async def _save_session_to_file(self, session_id: str) -> None:
        """Save session to local file."""
        try:
            session_file = self.fallback_dir / f"{session_id}.json"
            messages = self.local_conversations.get(session_id, [])
            
            # Convert to serializable format
            data = {
                "session_id": session_id,
                "messages": [msg.to_dict() for msg in messages]
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
    
    async def _load_session_from_file(self, session_id: str) -> None:
        """Load session from local file."""
        try:
            session_file = self.fallback_dir / f"{session_id}.json"
            
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                messages = [ConversationMessage.from_dict(msg_data) for msg_data in data["messages"]]
                self.local_conversations[session_id] = messages
                
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            self.local_conversations[session_id] = []
    
    async def cleanup_expired(self) -> int:
        """Clean up expired conversations."""
        if self.use_redis and self.redis_client:
            # Redis handles TTL automatically
            return 0
        else:
            return await self._cleanup_expired_local()
    
    async def _cleanup_expired_local(self) -> int:
        """Clean up expired local conversations."""
        expired_count = 0
        cutoff_time = datetime.now() - self.message_ttl
        
        for session_id in list(self.local_conversations.keys()):
            messages = self.local_conversations[session_id]
            
            if messages:
                # Check if newest message is expired
                newest_time = datetime.fromisoformat(messages[0].timestamp)
                if newest_time < cutoff_time:
                    del self.local_conversations[session_id]
                    
                    # Remove file
                    session_file = self.fallback_dir / f"{session_id}.json"
                    if session_file.exists():
                        session_file.unlink()
                    
                    expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired conversations")
        return expired_count
    
    async def close(self) -> None:
        """Close connections and cleanup."""
        if self.redis_client:
            await self.redis_client.close()
        
        # Save all local conversations
        for session_id in self.local_conversations:
            await self._save_session_to_file(session_id)