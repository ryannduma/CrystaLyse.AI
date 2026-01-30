"""Session management using OpenAI Agents SDK.

Uses SQLiteSession for persistent conversation history. The SDK handles:
- Thread-local connections for file databases
- WAL mode for concurrent access
- Automatic table creation (agent_sessions, agent_messages)
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from agents.memory import SQLiteSession

DEFAULT_DB = Path.home() / ".crystalyse" / "sessions.db"


def get_session(session_id: str, db_path: Path = DEFAULT_DB) -> SQLiteSession:
    """Get or create a session for conversation persistence.

    Args:
        session_id: Unique identifier for the session (e.g., UUID or user-provided)
        db_path: Path to SQLite database file

    Returns:
        SQLiteSession instance ready for use with Runner
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteSession(session_id, db_path=str(db_path))


@dataclass
class SessionInfo:
    """Summary information about a saved session."""

    session_id: str
    message_count: int
    last_updated: str | None


def list_sessions(db_path: Path = DEFAULT_DB, limit: int = 50) -> list[SessionInfo]:
    """List saved sessions with summary info.

    Args:
        db_path: Path to SQLite database
        limit: Maximum sessions to return (newest first)

    Returns:
        List of SessionInfo with id, message count, and last update time
    """
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        # Query SDK's tables for session summaries
        try:
            rows = conn.execute(
                """
                SELECT
                    session_id,
                    COUNT(*) as msg_count,
                    MAX(created_at) as last_updated
                FROM agent_messages
                GROUP BY session_id
                ORDER BY last_updated DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

            return [
                SessionInfo(
                    session_id=r[0],
                    message_count=r[1],
                    last_updated=r[2],
                )
                for r in rows
            ]
        except sqlite3.OperationalError:
            # Table doesn't exist yet (no sessions created)
            return []


def delete_session(session_id: str, db_path: Path = DEFAULT_DB) -> bool:
    """Delete a session and its messages.

    Args:
        session_id: Session to delete
        db_path: Path to SQLite database

    Returns:
        True if session was deleted, False if not found
    """
    if not db_path.exists():
        return False

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM agent_messages WHERE session_id = ?",
            (session_id,),
        )
        conn.execute(
            "DELETE FROM agent_sessions WHERE session_id = ?",
            (session_id,),
        )
        return cursor.rowcount > 0
