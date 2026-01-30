"""Unit tests for project memory (CRYSTALYSE.md loading).

Tests the hierarchical loading of project-specific instructions.
"""

from __future__ import annotations

from pathlib import Path

from crystalyse.memory.project_memory import (
    find_project_memory,
    get_project_memory_paths,
    load_project_memory,
)


class TestFindProjectMemory:
    """Tests for find_project_memory function."""

    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        """Test that find_project_memory returns empty when no files exist."""
        files = find_project_memory(cwd=tmp_path)
        assert files == []

    def test_finds_crystalyse_md(self, tmp_path: Path) -> None:
        """Test that CRYSTALYSE.md is found."""
        crystalyse_md = tmp_path / "CRYSTALYSE.md"
        crystalyse_md.write_text("# Project Memory")

        files = find_project_memory(cwd=tmp_path)
        assert len(files) == 1
        assert files[0] == crystalyse_md

    def test_finds_hidden_crystalyse_md(self, tmp_path: Path) -> None:
        """Test that .crystalyse/CRYSTALYSE.md is found."""
        hidden_dir = tmp_path / ".crystalyse"
        hidden_dir.mkdir()
        hidden_md = hidden_dir / "CRYSTALYSE.md"
        hidden_md.write_text("# Hidden Memory")

        files = find_project_memory(cwd=tmp_path)
        assert len(files) == 1
        assert files[0] == hidden_md

    def test_finds_rules_directory(self, tmp_path: Path) -> None:
        """Test that .crystalyse/rules/*.md files are found."""
        rules_dir = tmp_path / ".crystalyse" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "rule1.md").write_text("# Rule 1")
        (rules_dir / "rule2.md").write_text("# Rule 2")

        files = find_project_memory(cwd=tmp_path)
        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"rule1.md", "rule2.md"}

    def test_finds_all_types(self, tmp_path: Path) -> None:
        """Test that all memory file types are found."""
        # Create CRYSTALYSE.md
        (tmp_path / "CRYSTALYSE.md").write_text("# Main")

        # Create .crystalyse/CRYSTALYSE.md
        hidden_dir = tmp_path / ".crystalyse"
        hidden_dir.mkdir()
        (hidden_dir / "CRYSTALYSE.md").write_text("# Hidden")

        # Create rules
        rules_dir = hidden_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "rule.md").write_text("# Rule")

        files = find_project_memory(cwd=tmp_path)
        assert len(files) == 3

    def test_walks_up_directory_tree(self, tmp_path: Path) -> None:
        """Test that find_project_memory walks up the directory tree."""
        # Create parent CRYSTALYSE.md
        (tmp_path / "CRYSTALYSE.md").write_text("# Parent")

        # Create child directory
        child_dir = tmp_path / "child"
        child_dir.mkdir()

        files = find_project_memory(cwd=child_dir)
        assert len(files) == 1
        assert "Parent" in files[0].read_text()

    def test_order_is_closest_first(self, tmp_path: Path) -> None:
        """Test that files closer to cwd are listed first."""
        # Create parent CRYSTALYSE.md
        (tmp_path / "CRYSTALYSE.md").write_text("# Parent")

        # Create child directory with its own CRYSTALYSE.md
        child_dir = tmp_path / "child"
        child_dir.mkdir()
        (child_dir / "CRYSTALYSE.md").write_text("# Child")

        files = find_project_memory(cwd=child_dir)
        assert len(files) == 2
        # Child should be first
        assert "Child" in files[0].read_text()
        assert "Parent" in files[1].read_text()


class TestLoadProjectMemory:
    """Tests for load_project_memory function."""

    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        """Test that load_project_memory returns empty string when no files."""
        content = load_project_memory(cwd=tmp_path)
        assert content == ""

    def test_loads_single_file(self, tmp_path: Path) -> None:
        """Test loading a single CRYSTALYSE.md file."""
        (tmp_path / "CRYSTALYSE.md").write_text("Test content here")

        content = load_project_memory(cwd=tmp_path)
        assert "Test content here" in content

    def test_adds_source_header(self, tmp_path: Path) -> None:
        """Test that source file path is included in output."""
        (tmp_path / "CRYSTALYSE.md").write_text("Content")

        content = load_project_memory(cwd=tmp_path)
        assert "# From" in content

    def test_combines_multiple_files(self, tmp_path: Path) -> None:
        """Test that multiple files are combined with separators."""
        (tmp_path / "CRYSTALYSE.md").write_text("File One Content")

        hidden_dir = tmp_path / ".crystalyse"
        hidden_dir.mkdir()
        (hidden_dir / "CRYSTALYSE.md").write_text("File Two Content")

        content = load_project_memory(cwd=tmp_path)
        assert "File One Content" in content
        assert "File Two Content" in content
        assert "---" in content  # Separator


class TestGetProjectMemoryPaths:
    """Tests for get_project_memory_paths function."""

    def test_returns_string_paths(self, tmp_path: Path) -> None:
        """Test that paths are returned as strings."""
        (tmp_path / "CRYSTALYSE.md").write_text("Content")

        paths = get_project_memory_paths(cwd=tmp_path)
        assert len(paths) == 1
        assert isinstance(paths[0], str)

    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        """Test that empty list is returned when no files."""
        paths = get_project_memory_paths(cwd=tmp_path)
        assert paths == []
