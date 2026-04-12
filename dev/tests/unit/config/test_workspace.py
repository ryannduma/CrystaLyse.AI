"""Tests for .crystalyse/ project-root discovery and scaffolding.

Covers all acceptance criteria from spec §4.5:
- find_crystalyse_root() walks upward correctly (nested subdirectory)
- .gitignore template writes on first creation
- ensure_crystalyse_root(interactive=False) creates silently
- ensure_crystalyse_root(create_if_missing=False) raises when not found
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crystalyse.config.workspace import (
    _SCAFFOLD_DIRS,
    _scaffold_crystalyse_dir,
    ensure_crystalyse_root,
    find_crystalyse_root,
)

# ---------------------------------------------------------------------------
# find_crystalyse_root
# ---------------------------------------------------------------------------


class TestFindCrystalyseRoot:
    def test_finds_root_in_current_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".crystalyse").mkdir()
        assert find_crystalyse_root(start=tmp_path) == tmp_path

    def test_walks_upward_from_nested_subdir(self, tmp_path: Path) -> None:
        """Acceptance criterion: walks upward correctly with a nested subdir."""
        (tmp_path / ".crystalyse").mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert find_crystalyse_root(start=nested) == tmp_path

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        # tmp_path has no .crystalyse/ anywhere up the tree
        # (unless the test runner's cwd happens to have one — use tmp_path explicitly)
        bare = tmp_path / "bare_project"
        bare.mkdir()
        assert find_crystalyse_root(start=bare) is None

    def test_finds_nearest_root_with_multiple(self, tmp_path: Path) -> None:
        """When multiple .crystalyse/ dirs exist, the nearest one wins."""
        (tmp_path / ".crystalyse").mkdir()
        inner = tmp_path / "sub"
        inner.mkdir()
        (inner / ".crystalyse").mkdir()

        deeper = inner / "deep"
        deeper.mkdir()

        # Starting from deeper, should find inner (not tmp_path)
        assert find_crystalyse_root(start=deeper) == inner

    def test_ignores_file_named_crystalyse(self, tmp_path: Path) -> None:
        """A regular file named .crystalyse should not be treated as root."""
        (tmp_path / ".crystalyse").write_text("not a directory")
        assert find_crystalyse_root(start=tmp_path) is None


# ---------------------------------------------------------------------------
# _scaffold_crystalyse_dir
# ---------------------------------------------------------------------------


class TestScaffoldCrystalyseDir:
    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        result = _scaffold_crystalyse_dir(tmp_path)
        assert result == tmp_path

        crystalyse_dir = tmp_path / ".crystalyse"
        assert crystalyse_dir.is_dir()

        for subdir in _SCAFFOLD_DIRS:
            assert (crystalyse_dir / subdir).is_dir()

    def test_writes_gitignore_template(self, tmp_path: Path) -> None:
        """Acceptance criterion: .gitignore template writes on first creation."""
        _scaffold_crystalyse_dir(tmp_path)

        gitignore = tmp_path / ".crystalyse" / ".gitignore"
        assert gitignore.is_file()
        content = gitignore.read_text()
        assert "runs/" in content
        assert "plans/latest.md" in content
        assert "agent/" in content
        # plans/*.md must NOT be ignored (reproducibility)
        assert "plans/*.md" not in content

    def test_writes_empty_config_toml(self, tmp_path: Path) -> None:
        _scaffold_crystalyse_dir(tmp_path)
        config = tmp_path / ".crystalyse" / "config.toml"
        assert config.is_file()

    def test_does_not_clobber_existing_gitignore(self, tmp_path: Path) -> None:
        crystalyse_dir = tmp_path / ".crystalyse"
        crystalyse_dir.mkdir()
        gitignore = crystalyse_dir / ".gitignore"
        gitignore.write_text("custom content\n")

        _scaffold_crystalyse_dir(tmp_path)
        assert gitignore.read_text() == "custom content\n"

    def test_does_not_clobber_existing_config_toml(self, tmp_path: Path) -> None:
        crystalyse_dir = tmp_path / ".crystalyse"
        crystalyse_dir.mkdir()
        config = crystalyse_dir / "config.toml"
        config.write_text('default_model = "custom"\n')

        _scaffold_crystalyse_dir(tmp_path)
        assert 'default_model = "custom"' in config.read_text()

    def test_idempotent(self, tmp_path: Path) -> None:
        """Calling scaffold twice doesn't error or clobber."""
        _scaffold_crystalyse_dir(tmp_path)
        _scaffold_crystalyse_dir(tmp_path)
        assert (tmp_path / ".crystalyse" / ".gitignore").is_file()


# ---------------------------------------------------------------------------
# ensure_crystalyse_root
# ---------------------------------------------------------------------------


class TestEnsureCrystalyseRoot:
    def test_returns_existing_root(self, tmp_path: Path) -> None:
        (tmp_path / ".crystalyse").mkdir()
        result = ensure_crystalyse_root(base=tmp_path, interactive=False)
        assert result == tmp_path

    def test_creates_silently_when_non_interactive(self, tmp_path: Path) -> None:
        """Acceptance criterion: ensure_crystalyse_root(interactive=False)
        creates the directory silently (for non-interactive/CI runs)."""
        result = ensure_crystalyse_root(base=tmp_path, interactive=False, create_if_missing=True)
        assert result == tmp_path
        assert (tmp_path / ".crystalyse").is_dir()
        assert (tmp_path / ".crystalyse" / "config.toml").is_file()
        assert (tmp_path / ".crystalyse" / ".gitignore").is_file()

    def test_raises_when_create_if_missing_false(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No .crystalyse/ directory found"):
            ensure_crystalyse_root(base=tmp_path, create_if_missing=False)

    def test_walks_upward_before_creating(self, tmp_path: Path) -> None:
        """If a parent has .crystalyse/, don't create a new one."""
        (tmp_path / ".crystalyse").mkdir()
        nested = tmp_path / "sub" / "deep"
        nested.mkdir(parents=True)

        result = ensure_crystalyse_root(base=nested, interactive=False)
        assert result == tmp_path
        # No new .crystalyse/ created in nested dir
        assert not (nested / ".crystalyse").exists()
