"""Tests for slash commands including /memory subcommands."""

import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console


class TestSlashCommandHandler:
    """Test SlashCommandHandler class."""

    @pytest.fixture
    def console(self):
        """Create a console that captures output."""
        return Console(file=StringIO(), force_terminal=True)

    @pytest.fixture
    def handler(self, console):
        """Create a SlashCommandHandler instance."""
        from crystalyse.ui.slash_commands import SlashCommandHandler

        return SlashCommandHandler(console=console)

    def test_handle_unknown_command(self, handler):
        """Test handling of unknown command."""
        result = handler.handle_command("/unknown")
        assert result is False

    def test_handle_help_command(self, handler):
        """Test /help command."""
        result = handler.handle_command("/help")
        assert result is True

    def test_handle_about_command(self, handler):
        """Test /about command."""
        result = handler.handle_command("/about")
        assert result is True

    def test_handle_stats_command(self, handler):
        """Test /stats command."""
        result = handler.handle_command("/stats")
        assert result is True

    def test_list_commands(self, handler):
        """Test that list_commands returns all available commands."""
        commands = handler.list_commands()
        assert "/help" in commands
        assert "/memory" in commands
        assert "/quit" in commands


class TestMemorySubcommands:
    """Test /memory subcommands."""

    @pytest.fixture
    def console(self):
        """Create a console that captures output."""
        return Console(file=StringIO(), force_terminal=True)

    @pytest.fixture
    def handler(self, console):
        """Create a SlashCommandHandler instance."""
        from crystalyse.ui.slash_commands import SlashCommandHandler

        return SlashCommandHandler(console=console)

    def test_memory_show(self, handler):
        """Test /memory show subcommand."""
        result = handler.handle_command("/memory show")
        assert result is True

    def test_memory_default_is_show(self, handler):
        """Test /memory with no args defaults to show."""
        result = handler.handle_command("/memory")
        assert result is True

    @patch("crystalyse.memory.project_memory.get_project_memory_paths")
    def test_memory_list_with_files(self, mock_paths, handler, tmp_path):
        """Test /memory list when files exist."""
        # Create a temp file
        memory_file = tmp_path / "CRYSTALYSE.md"
        memory_file.write_text("# Test Memory")
        mock_paths.return_value = [str(memory_file)]

        result = handler.handle_command("/memory list")
        assert result is True

    @patch("crystalyse.memory.project_memory.get_project_memory_paths")
    def test_memory_list_no_files(self, mock_paths, handler):
        """Test /memory list when no files exist."""
        mock_paths.return_value = []

        result = handler.handle_command("/memory list")
        assert result is True

    @patch("crystalyse.memory.project_memory.load_project_memory")
    def test_memory_preview_with_content(self, mock_load, handler):
        """Test /memory preview with content."""
        mock_load.return_value = "# Project Memory\n\nSome content here."

        result = handler.handle_command("/memory preview")
        assert result is True

    @patch("crystalyse.memory.project_memory.load_project_memory")
    def test_memory_preview_no_content(self, mock_load, handler):
        """Test /memory preview with no content."""
        mock_load.return_value = ""

        result = handler.handle_command("/memory preview")
        assert result is True

    @patch("crystalyse.memory.project_memory.find_project_memory")
    def test_memory_find(self, mock_find, handler):
        """Test /memory find subcommand."""
        mock_find.return_value = []

        result = handler.handle_command("/memory find")
        assert result is True

    def test_memory_unknown_subcommand(self, handler, console):
        """Test /memory with unknown subcommand."""
        result = handler.handle_command("/memory foobar")
        assert result is True  # Still handled, just shows help


class TestMemoryHelp:
    """Test memory help display."""

    @pytest.fixture
    def console(self):
        """Create a console that captures output."""
        return Console(file=StringIO(), force_terminal=True)

    @pytest.fixture
    def handler(self, console):
        """Create a SlashCommandHandler instance."""
        from crystalyse.ui.slash_commands import SlashCommandHandler

        return SlashCommandHandler(console=console)

    def test_memory_help_shows_subcommands(self, handler, console):
        """Test that /memory with unknown subcommand shows help."""
        handler.handle_command("/memory unknown")
        output = console.file.getvalue()
        # Help should mention available subcommands
        assert "show" in output or "list" in output or "Memory" in output
