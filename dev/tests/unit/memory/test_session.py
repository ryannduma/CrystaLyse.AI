"""Unit tests for V2 session management.

Tests the SQLite-backed session persistence using OpenAI SDK's SQLiteSession.
"""

from __future__ import annotations

from pathlib import Path

from crystalyse.memory.session import (
    SessionInfo,
    delete_session,
    get_session,
    list_sessions,
)


class TestGetSession:
    """Tests for get_session function."""

    def test_creates_session(self, tmp_path: Path) -> None:
        """Test that get_session creates a new session."""
        db_path = tmp_path / "test_sessions.db"
        session = get_session("test-session-1", db_path=db_path)

        assert session is not None
        assert session.session_id == "test-session-1"

    def test_creates_database_directory(self, tmp_path: Path) -> None:
        """Test that get_session creates parent directories."""
        db_path = tmp_path / "subdir" / "nested" / "sessions.db"
        session = get_session("test-session", db_path=db_path)

        assert session is not None
        assert db_path.parent.exists()

    def test_same_session_id_returns_fresh_session(self, tmp_path: Path) -> None:
        """Test that same session ID returns a usable session."""
        db_path = tmp_path / "sessions.db"
        session1 = get_session("shared-session", db_path=db_path)
        session2 = get_session("shared-session", db_path=db_path)

        # Both sessions should work
        assert session1.session_id == session2.session_id


class TestListSessions:
    """Tests for list_sessions function."""

    def test_returns_empty_when_no_db(self, tmp_path: Path) -> None:
        """Test that list_sessions returns empty when no database exists."""
        db_path = tmp_path / "nonexistent.db"
        sessions = list_sessions(db_path=db_path)

        assert sessions == []

    def test_returns_empty_when_no_sessions(self, tmp_path: Path) -> None:
        """Test that list_sessions returns empty when database is empty."""
        db_path = tmp_path / "empty.db"
        # Create session but don't add any messages
        get_session("empty-session", db_path=db_path)
        sessions = list_sessions(db_path=db_path)

        # No messages means no sessions to list
        assert sessions == []


class TestDeleteSession:
    """Tests for delete_session function."""

    def test_returns_false_when_no_db(self, tmp_path: Path) -> None:
        """Test that delete_session returns False when no database exists."""
        db_path = tmp_path / "nonexistent.db"
        result = delete_session("any-session", db_path=db_path)

        assert result is False

    def test_returns_false_for_nonexistent_session(self, tmp_path: Path) -> None:
        """Test that delete_session returns False for nonexistent session."""
        db_path = tmp_path / "sessions.db"
        get_session("some-session", db_path=db_path)

        result = delete_session("nonexistent-session", db_path=db_path)
        assert result is False


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_session_info_attributes(self) -> None:
        """Test SessionInfo has correct attributes."""
        info = SessionInfo(
            session_id="test-123",
            message_count=5,
            last_updated="2024-01-15 10:30:00",
        )

        assert info.session_id == "test-123"
        assert info.message_count == 5
        assert info.last_updated == "2024-01-15 10:30:00"

    def test_session_info_with_none_timestamp(self) -> None:
        """Test SessionInfo allows None for last_updated."""
        info = SessionInfo(
            session_id="new-session",
            message_count=0,
            last_updated=None,
        )

        assert info.last_updated is None
