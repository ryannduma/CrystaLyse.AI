"""Sandbox policy definitions.

Defines sandbox policy levels and writable root configuration.
Based on Codex patterns for declarative sandbox policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class SandboxLevel(Enum):
    """Sandbox restriction level.

    Controls the degree of filesystem and network access.
    """

    NONE = "none"
    """No sandbox - full access (dangerous, requires explicit opt-in)."""

    READ_ONLY = "read_only"
    """Full disk read access, no write access anywhere."""

    WORKSPACE = "workspace"
    """Write access only in workspace directory + /tmp."""


@dataclass(frozen=True)
class WritableRoot:
    """A directory that can be written to, with optional read-only subpaths.

    Attributes:
        root: The writable directory path.
        read_only_subpaths: Paths within root that should remain read-only
            (e.g., .git/, .crystalyse/).
    """

    root: Path
    read_only_subpaths: tuple[Path, ...] = field(default_factory=tuple)

    @classmethod
    def from_path(cls, path: Path) -> WritableRoot:
        """Create a WritableRoot, auto-detecting protected subpaths.

        Automatically marks .git and .crystalyse directories as read-only.
        For .git files (worktree pointers), also protects the gitdir.
        """
        read_only: list[Path] = []

        # Check for .git (directory or worktree pointer file)
        git_path = path / ".git"
        if git_path.exists():
            read_only.append(git_path)

            # If .git is a file, it's a worktree pointer - protect the gitdir too
            if git_path.is_file():
                gitdir = _parse_gitdir(git_path)
                if gitdir and gitdir.exists():
                    read_only.append(gitdir)

        # Check for .crystalyse config directory
        crystalyse_path = path / ".crystalyse"
        if crystalyse_path.is_dir():
            read_only.append(crystalyse_path)

        return cls(root=path, read_only_subpaths=tuple(read_only))


@dataclass(frozen=True)
class SandboxPolicy:
    """Complete sandbox policy configuration.

    Attributes:
        level: The restriction level (none, read_only, workspace).
        writable_roots: Directories with write access (for workspace level).
        network_access: Whether network access is allowed.
        include_tmpdir: Include $TMPDIR in writable roots.
        include_tmp: Include /tmp in writable roots.
    """

    level: SandboxLevel = SandboxLevel.WORKSPACE
    writable_roots: tuple[Path, ...] = field(default_factory=tuple)
    network_access: bool = True
    include_tmpdir: bool = True
    include_tmp: bool = True

    @classmethod
    def none(cls) -> SandboxPolicy:
        """Create a policy with no restrictions (dangerous)."""
        return cls(level=SandboxLevel.NONE, network_access=True)

    @classmethod
    def read_only(cls, *, network_access: bool = False) -> SandboxPolicy:
        """Create a read-only policy."""
        return cls(level=SandboxLevel.READ_ONLY, network_access=network_access)

    @classmethod
    def workspace(
        cls,
        cwd: Path,
        *,
        additional_roots: Sequence[Path] | None = None,
        network_access: bool = True,
    ) -> SandboxPolicy:
        """Create a workspace policy allowing writes in cwd.

        Args:
            cwd: Current working directory (primary writable root).
            additional_roots: Additional directories to make writable.
            network_access: Whether to allow network access.
        """
        roots = [cwd]
        if additional_roots:
            roots.extend(additional_roots)

        return cls(
            level=SandboxLevel.WORKSPACE,
            writable_roots=tuple(roots),
            network_access=network_access,
        )

    def has_full_disk_write_access(self) -> bool:
        """Check if this policy allows writing anywhere on disk."""
        return self.level == SandboxLevel.NONE

    def has_full_disk_read_access(self) -> bool:
        """Check if this policy allows reading anywhere on disk."""
        # All current levels allow full read access
        return True

    def has_full_network_access(self) -> bool:
        """Check if this policy allows unrestricted network access."""
        return self.network_access

    def get_writable_roots_with_cwd(self, cwd: Path) -> list[WritableRoot]:
        """Compute effective writable roots for execution.

        Includes the specified writable_roots, cwd, and optionally /tmp
        and $TMPDIR. Automatically detects and marks .git/.crystalyse
        as read-only within each root.

        Args:
            cwd: Current working directory for command execution.

        Returns:
            List of WritableRoot objects with auto-detected protections.
        """
        import os

        if self.level == SandboxLevel.NONE:
            # No restrictions - return empty list (everything writable)
            return []

        if self.level == SandboxLevel.READ_ONLY:
            # Only /dev/null writable
            return [WritableRoot(root=Path("/dev/null"))]

        # WORKSPACE level - compute writable roots
        roots: list[WritableRoot] = []
        seen: set[Path] = set()

        def add_root(path: Path) -> None:
            """Add a root if not already seen."""
            try:
                canonical = path.resolve()
            except OSError:
                canonical = path

            if canonical not in seen:
                seen.add(canonical)
                roots.append(WritableRoot.from_path(canonical))

        # Add explicit writable roots
        for root in self.writable_roots:
            add_root(root)

        # Add cwd if not already included
        add_root(cwd)

        # Add /tmp if enabled
        if self.include_tmp:
            add_root(Path("/tmp"))

        # Add $TMPDIR if enabled and set
        if self.include_tmpdir:
            tmpdir = os.environ.get("TMPDIR")
            if tmpdir:
                add_root(Path(tmpdir))

        return roots


def _parse_gitdir(git_file: Path) -> Path | None:
    """Parse a .git file (worktree pointer) to find the gitdir.

    Git worktrees use a .git file containing 'gitdir: <path>'.
    """
    try:
        content = git_file.read_text().strip()
        if content.startswith("gitdir:"):
            gitdir_str = content[7:].strip()
            # Handle relative paths
            if not gitdir_str.startswith("/"):
                gitdir = git_file.parent / gitdir_str
            else:
                gitdir = Path(gitdir_str)
            return gitdir.resolve()
    except OSError:
        pass
    return None
