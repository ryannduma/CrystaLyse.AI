"""
Persistent Session Manager for Crystalyse
Manages long-lived sessions to maintain context and connections across queries.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .mcp_connection_pool import MCPConnectionPool
from .resilient_tool_caller import ResilientToolCaller

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Context information maintained across queries in a session."""

    user_id: str
    session_id: str
    created_at: float
    last_accessed: float
    query_count: int
    mode: str  # "rigorous" or "creative"

    # Material discovery context
    discovered_materials: list
    validated_compositions: dict
    generated_structures: dict
    calculated_energies: dict

    # Tool usage statistics
    tool_calls_count: dict
    successful_operations: list
    failed_operations: list


class PersistentSession:
    """A persistent session that maintains MCP connections and context."""

    def __init__(self, user_id: str, agent_config: Any, session_timeout: int = 3600):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.agent_config = agent_config
        self.session_timeout = session_timeout

        # Session components
        self.connection_pool = MCPConnectionPool()
        self.resilient_caller = ResilientToolCaller()

        # Session context
        self.context = SessionContext(
            user_id=user_id,
            session_id=self.session_id,
            created_at=time.time(),
            last_accessed=time.time(),
            query_count=0,
            mode=agent_config.mode,
            discovered_materials=[],
            validated_compositions={},
            generated_structures={},
            calculated_energies={},
            tool_calls_count={"smact": 0, "chemeleon": 0, "mace": 0},
            successful_operations=[],
            failed_operations=[],
        )

        logger.info(f"Created new session {self.session_id} for user {user_id}")

    async def initialize_connections(self, server_configs: dict[str, Any]) -> None:
        """Initialize MCP server connections for this session."""
        try:
            for server_name, config in server_configs.items():
                await self.connection_pool.register_server(server_name, config)
                # Test connection
                connection = await self.connection_pool.get_connection(server_name)
                if connection:
                    logger.info(f"✅ Session {self.session_id}: Connected to {server_name}")
                else:
                    logger.warning(
                        f"⚠️ Session {self.session_id}: Failed to connect to {server_name}"
                    )
        except Exception as e:
            logger.error(f"❌ Session {self.session_id}: Failed to initialize connections: {e}")
            raise

    def update_access_time(self) -> None:
        """Update the last accessed time for session management."""
        self.context.last_accessed = time.time()
        self.context.query_count += 1

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return (time.time() - self.context.last_accessed) > self.session_timeout

    async def is_healthy(self) -> bool:
        """Check if the session connections are healthy."""
        try:
            status = self.connection_pool.get_connection_status()
            return any(info["connected"] for info in status.values())
        except Exception as e:
            logger.error(f"Session {self.session_id} health check failed: {e}")
            return False

    def add_discovered_material(self, material: str, properties: dict[str, Any]) -> None:
        """Add a discovered material to the session context."""
        self.context.discovered_materials.append(
            {
                "formula": material,
                "properties": properties,
                "discovered_at": time.time(),
                "query_number": self.context.query_count,
            }
        )

    def add_validation_result(self, composition: str, result: dict[str, Any]) -> None:
        """Add a validation result to the session context."""
        self.context.validated_compositions[composition] = {
            "result": result,
            "validated_at": time.time(),
            "query_number": self.context.query_count,
        }

    def add_structure_result(self, composition: str, structures: list) -> None:
        """Add structure generation results to the session context."""
        self.context.generated_structures[composition] = {
            "structures": structures,
            "generated_at": time.time(),
            "query_number": self.context.query_count,
        }

    def add_energy_result(self, composition: str, energy: float) -> None:
        """Add energy calculation result to the session context."""
        self.context.calculated_energies[composition] = {
            "energy": energy,
            "calculated_at": time.time(),
            "query_number": self.context.query_count,
        }

    def record_tool_call(self, tool_name: str, success: bool, operation: str) -> None:
        """Record a tool call for statistics."""
        self.context.tool_calls_count[tool_name] = (
            self.context.tool_calls_count.get(tool_name, 0) + 1
        )

        operation_record = {
            "tool": tool_name,
            "operation": operation,
            "timestamp": time.time(),
            "query_number": self.context.query_count,
        }

        if success:
            self.context.successful_operations.append(operation_record)
        else:
            self.context.failed_operations.append(operation_record)

    def get_context_summary(self) -> dict[str, Any]:
        """Get a summary of the session context for debugging."""
        return {
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "created_at": self.context.created_at,
                "last_accessed": self.context.last_accessed,
                "query_count": self.context.query_count,
                "mode": self.context.mode,
                "age_minutes": (time.time() - self.context.created_at) / 60,
            },
            "discoveries": {
                "materials_count": len(self.context.discovered_materials),
                "validated_compositions": len(self.context.validated_compositions),
                "generated_structures": len(self.context.generated_structures),
                "calculated_energies": len(self.context.calculated_energies),
            },
            "tool_usage": {
                "calls_by_tool": self.context.tool_calls_count,
                "successful_operations": len(self.context.successful_operations),
                "failed_operations": len(self.context.failed_operations),
                "success_rate": (
                    len(self.context.successful_operations)
                    / (
                        len(self.context.successful_operations)
                        + len(self.context.failed_operations)
                    )
                )
                if (len(self.context.successful_operations) + len(self.context.failed_operations))
                > 0
                else 0,
            },
            "connection_status": self.connection_pool.get_connection_status(),
        }

    async def cleanup(self) -> None:
        """Clean up session resources."""
        logger.info(f"Cleaning up session {self.session_id}")
        await self.connection_pool.close_all_connections()


class PersistentSessionManager:
    """Manages multiple persistent sessions across users."""

    def __init__(self, default_timeout: int = 3600, cleanup_interval: int = 300):
        self.sessions: dict[str, PersistentSession] = {}
        self.default_timeout = default_timeout
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task | None = None

        # Start background cleanup task (only if event loop is available)
        self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        except RuntimeError:
            # No event loop available (CLI context) - cleanup will be done manually
            logger.info("No event loop available, background cleanup disabled")

    async def _cleanup_expired_sessions(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup task: {e}")

    async def _cleanup_expired(self) -> None:
        """Clean up expired sessions."""
        expired_sessions = []

        for user_id, session in self.sessions.items():
            if session.is_expired() or not await session.is_healthy():
                expired_sessions.append(user_id)

        for user_id in expired_sessions:
            logger.info(f"Cleaning up expired session for user {user_id}")
            session = self.sessions.pop(user_id)
            await session.cleanup()

    async def get_or_create_session(
        self, user_id: str, agent_config: Any, server_configs: dict[str, Any]
    ) -> PersistentSession:
        """Get existing session or create a new one for the user."""

        # Check if we have a valid session
        if user_id in self.sessions:
            session = self.sessions[user_id]
            if not session.is_expired() and await session.is_healthy():
                session.update_access_time()
                logger.info(f"Reusing existing session {session.session_id} for user {user_id}")
                return session
            else:
                # Clean up expired/unhealthy session
                logger.info(f"Cleaning up expired session for user {user_id}")
                await session.cleanup()
                del self.sessions[user_id]

        # Create new session
        session = PersistentSession(user_id, agent_config, self.default_timeout)
        await session.initialize_connections(server_configs)
        self.sessions[user_id] = session

        logger.info(f"Created new session {session.session_id} for user {user_id}")
        return session

    async def close_session(self, user_id: str) -> None:
        """Explicitly close a user's session."""
        if user_id in self.sessions:
            session = self.sessions.pop(user_id)
            await session.cleanup()
            logger.info(f"Closed session for user {user_id}")

    async def close_all_sessions(self) -> None:
        """Close all sessions and cleanup resources."""
        logger.info("Closing all sessions...")

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        for session in self.sessions.values():
            await session.cleanup()

        self.sessions.clear()
        logger.info("✅ All sessions closed")

    def get_session_stats(self) -> dict[str, Any]:
        """Get statistics about all sessions."""
        return {
            "total_sessions": len(self.sessions),
            "sessions": {
                user_id: session.get_context_summary() for user_id, session in self.sessions.items()
            },
        }


# Global session manager instance
_session_manager: PersistentSessionManager | None = None


def get_session_manager() -> PersistentSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = PersistentSessionManager()
    return _session_manager


async def cleanup_session_manager() -> None:
    """Cleanup the global session manager."""
    global _session_manager
    if _session_manager is not None:
        await _session_manager.close_all_sessions()
        _session_manager = None
