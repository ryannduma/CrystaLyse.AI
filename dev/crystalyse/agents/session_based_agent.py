"""
Session-Based CrystaLyse Agent Implementation

This demonstrates how to implement proper conversation persistence and memory
using the OpenAI Agents SDK patterns. While the SDK doesn't have SQLiteSession,
we can create a similar system using conversation history management.

Key features:
- Conversation history persistence
- Memory integration with OpenAI Agents SDK
- Proper MCP server integration
- Session-based context management
"""

import asyncio
import logging
import json
import sqlite3
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

# OpenAI Agents SDK imports
from agents import Agent, Runner, gen_trace_id, RunConfig, set_default_openai_key
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings

# CrystaLyse imports
from ..memory import CrystaLyseMemory, get_memory_tools
from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class ConversationItem:
    """Represents a single conversation item (similar to SQLiteSession concept)."""
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


class CrystaLyseSession:
    """
    Session-based conversation management for CrystaLyse.
    
    This implements a SQLiteSession-like system using OpenAI Agents SDK patterns.
    Provides automatic conversation history management and memory integration.
    """
    
    def __init__(self, session_id: str, user_id: str = "default", db_path: Optional[Path] = None, max_turns: int = 100):
        """
        Initialize CrystaLyse session.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier for memory system
            db_path: Path to SQLite database (default: ~/.crystalyse/conversations.db)
            max_turns: Maximum number of turns for agent execution (default: 100)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.max_turns = max_turns
        
        # Setup database
        if db_path is None:
            db_path = Path.home() / ".crystalyse" / "conversations.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory system
        self.memory = CrystaLyseMemory(user_id=user_id)
        
        # Initialize database
        self._init_database()
        
        # Configure OpenAI API key - use OPENAI_MDG_API_KEY if available, fallback to OPENAI_API_KEY
        mdg_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
        if mdg_api_key:
            set_default_openai_key(mdg_api_key)
            logger.info("✅ OpenAI API key configured (MDG or standard)")
        else:
            logger.warning("⚠️ No OpenAI API key found - operations may fail")
        
        # Agent will be created when needed
        self.agent = None
        self.mcp_servers = []
        
        logger.info(f"CrystaLyseSession initialized: {session_id} for user {user_id}")
    
    def _init_database(self):
        """Initialize SQLite database for conversation storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)
            ''')
    
    async def setup_agent(self, mode: str = "creative") -> Agent:
        """
        Setup the CrystaLyse agent with MCP servers and memory tools.
        
        Args:
            mode: Analysis mode ('creative' or 'rigorous')
            
        Returns:
            Configured agent instance
        """
        # Setup MCP servers
        await self._setup_mcp_servers(mode)
        
        # Get memory tools with user context
        memory_tools = get_memory_tools(user_id=self.user_id)
        
        # Create agent with all tools
        self.agent = Agent(
            name="CrystaLyse",
            instructions=self._get_system_prompt(mode),
            model="o4-mini" if mode == "creative" else "o3",
            tools=memory_tools,
            mcp_servers=self.mcp_servers,
            model_settings=ModelSettings(
                tool_choice="auto"
            )
        )
        
        logger.info(f"Agent setup completed in {mode} mode with {len(self.mcp_servers)} MCP servers")
        return self.agent
    
    async def _setup_mcp_servers(self, mode: str):
        """Setup MCP servers based on mode with fallback options."""
        self.mcp_servers = []
        
        # Chemistry server selection based on mode with fallback
        if mode == "creative":
            server_candidates = ["chemistry_creative", "chemistry_unified"]
        else:
            server_candidates = ["chemistry_unified", "chemistry_creative"]
        
        # Try each server candidate in order
        for server_name in server_candidates:
            try:
                # Get server config
                server_config = config.get_server_config(server_name)
                
                # Create MCP server with extended timeout for long-running operations
                mcp_server = MCPServerStdio(
                    params={
                        "command": server_config["command"],
                        "args": server_config["args"],
                        "env": server_config.get("env", {})
                    },
                    client_session_timeout_seconds=300  # 5 minutes for complex calculations
                )
                
                # Connect to server
                await mcp_server.connect()
                self.mcp_servers.append(mcp_server)
                
                logger.info(f"✅ Connected to {server_name} MCP server")
                break  # Success, exit the loop
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to connect to {server_name}: {e}")
                continue  # Try the next server
        
        # If no MCP servers are available, continue without them
        if not self.mcp_servers:
            logger.warning("⚠️ No MCP servers available - continuing with memory tools only")
            logger.info("💡 The session will work but without computational chemistry tools")
        else:
            logger.info(f"✅ Session ready with {len(self.mcp_servers)} MCP servers")
    
    def _get_system_prompt(self, mode: str) -> str:
        """Get system prompt for the agent."""
        base_prompt = f"""You are CrystaLyse, an AI assistant specializing in computational materials discovery.

Mode: {mode.capitalize()}
- Creative mode: Explore novel materials and unconventional approaches
- Rigorous mode: Use validated computational methods and established protocols

You have access to:
- Memory system for persistent context and discoveries
- Chemistry tools (SMACT, Chemeleon, MACE) for computational validation
- Visualization tools for structure analysis

Always:
- Use tools for computational claims
- Save important discoveries to memory
- Build on previous session context
- Provide transparent explanations of your methods
"""
        
        # Add memory context
        memory_context = self.memory.get_context_for_agent()
        if memory_context != "No previous context available.":
            base_prompt += f"\n\nMemory Context:\n{memory_context}"
        
        return base_prompt
    
    def add_conversation_item(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add an item to the conversation history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO conversations (session_id, user_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.session_id,
                self.user_id,
                role,
                content,
                json.dumps(metadata) if metadata else None
            ))
    
    def get_conversation_history(self, limit: int = 50) -> List[ConversationItem]:
        """Get conversation history for this session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT role, content, timestamp, metadata
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (self.session_id, limit))
            
            items = []
            for row in cursor:
                items.append(ConversationItem(
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                ))
            
            return list(reversed(items))  # Return in chronological order
    
    def pop_last_item(self) -> Optional[ConversationItem]:
        """Remove and return the last conversation item (like SQLiteSession.pop_item)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get the last item
            cursor = conn.execute('''
                SELECT id, role, content, timestamp, metadata
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (self.session_id,))
            
            row = cursor.fetchone()
            if row:
                # Delete the item
                conn.execute('DELETE FROM conversations WHERE id = ?', (row['id'],))
                
                return ConversationItem(
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                )
            
            return None
    
    def clear_conversation(self):
        """Clear all conversation history for this session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM conversations WHERE session_id = ?', (self.session_id,))
    
    def _format_conversation_for_agent(self, history: List[ConversationItem]) -> List[Dict[str, str]]:
        """Format conversation history for agent input."""
        formatted = []
        
        for item in history:
            formatted.append({
                "role": item.role,
                "content": item.content
            })
        
        return formatted
    
    async def run_with_history(self, user_input: str) -> Dict[str, Any]:
        """
        Run the agent with conversation history (like SQLiteSession behavior).
        
        This automatically:
        1. Retrieves conversation history
        2. Adds it to the agent input
        3. Runs the agent
        4. Saves the interaction to history
        
        Args:
            user_input: User's input message
            
        Returns:
            Agent result with conversation context
        """
        if not self.agent:
            await self.setup_agent()
        
        # Get conversation history
        history = self.get_conversation_history()
        
        # Format input with history
        input_messages = self._format_conversation_for_agent(history)
        input_messages.append({"role": "user", "content": user_input})
        
        try:
            # Run the agent
            result = await Runner.run(
                starting_agent=self.agent,
                input=input_messages,
                max_turns=self.max_turns,
                run_config=RunConfig(
                    trace_id=gen_trace_id(),
                    workflow_name="CrystaLyse Session"
                )
            )
            
            # Save the interaction
            self.add_conversation_item("user", user_input)
            self.add_conversation_item("assistant", str(result.final_output))
            
            # Update memory with interaction
            self.memory.add_interaction(user_input, str(result.final_output))
            
            return {
                "status": "success",
                "response": str(result.final_output),
                "history_length": len(history),
                "memory_updated": True
            }
            
        except Exception as e:
            logger.error(f"Error running agent with history: {e}")
            return {
                "status": "error",
                "error": str(e),
                "history_length": len(history)
            }
    
    async def cleanup(self):
        """Cleanup session resources."""
        # Cleanup MCP servers
        for server in self.mcp_servers:
            try:
                await server.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up MCP server: {e}")
        
        # Cleanup memory
        self.memory.cleanup()
        
        logger.info(f"Session {self.session_id} cleaned up")


# Session manager for multiple sessions
class CrystaLyseSessionManager:
    """Manages multiple CrystaLyse sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, CrystaLyseSession] = {}
    
    def get_or_create_session(self, session_id: str, user_id: str = "default", max_turns: int = 100) -> CrystaLyseSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = CrystaLyseSession(session_id, user_id, max_turns=max_turns)
        
        return self.sessions[session_id]
    
    async def close_session(self, session_id: str):
        """Close and cleanup a session."""
        if session_id in self.sessions:
            await self.sessions[session_id].cleanup()
            del self.sessions[session_id]
    
    async def cleanup_all(self):
        """Cleanup all sessions."""
        for session in self.sessions.values():
            await session.cleanup()
        self.sessions.clear()


# Global session manager instance
_session_manager = CrystaLyseSessionManager()


def get_session_manager() -> CrystaLyseSessionManager:
    """Get the global session manager."""
    return _session_manager


# Example usage functions
async def example_usage():
    """Example of how to use the session-based system."""
    
    # Get session manager
    manager = get_session_manager()
    
    # Create session for user
    session = manager.get_or_create_session("research_project_1", "researcher1")
    
    # Run multiple queries with persistent context
    print("Query 1: Initial analysis")
    result1 = await session.run_with_history("Analyze the stability of perovskite CaTiO3")
    print(f"Response: {result1['response'][:100]}...")
    
    print("\nQuery 2: Follow-up (automatic context)")
    result2 = await session.run_with_history("What about under pressure?")
    print(f"Response: {result2['response'][:100]}...")
    
    print("\nQuery 3: Comparative analysis")
    result3 = await session.run_with_history("Compare with SrTiO3")
    print(f"Response: {result3['response'][:100]}...")
    
    # Show conversation history
    history = session.get_conversation_history()
    print(f"\nConversation history: {len(history)} items")
    
    # Cleanup
    await session.cleanup()


if __name__ == "__main__":
    asyncio.run(example_usage()) 