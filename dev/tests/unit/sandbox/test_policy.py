"""Tests for sandbox policy module."""

import tempfile
from pathlib import Path

from crystalyse.sandbox.policy import (
    SandboxLevel,
    SandboxPolicy,
    WritableRoot,
    _parse_gitdir,
)


class TestSandboxLevel:
    """Tests for SandboxLevel enum."""

    def test_sandbox_levels_exist(self):
        """Test that all expected sandbox levels are defined."""
        assert SandboxLevel.NONE.value == "none"
        assert SandboxLevel.READ_ONLY.value == "read_only"
        assert SandboxLevel.WORKSPACE.value == "workspace"


class TestWritableRoot:
    """Tests for WritableRoot dataclass."""

    def test_simple_writable_root(self):
        """Test creating a simple writable root."""
        root = WritableRoot(root=Path("/tmp"))
        assert root.root == Path("/tmp")
        assert root.read_only_subpaths == ()

    def test_writable_root_with_read_only_subpaths(self):
        """Test creating a writable root with protected subpaths."""
        root = WritableRoot(
            root=Path("/home/user/project"),
            read_only_subpaths=(Path("/home/user/project/.git"),),
        )
        assert len(root.read_only_subpaths) == 1
        assert Path("/home/user/project/.git") in root.read_only_subpaths

    def test_from_path_detects_git_directory(self):
        """Test that from_path detects .git directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create .git directory
            git_dir = tmppath / ".git"
            git_dir.mkdir()

            root = WritableRoot.from_path(tmppath)
            assert root.root == tmppath
            # .git should be in read_only_subpaths
            assert any(".git" in str(p) for p in root.read_only_subpaths)

    def test_from_path_detects_crystalyse_directory(self):
        """Test that from_path detects .crystalyse directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create .crystalyse directory
            crystalyse_dir = tmppath / ".crystalyse"
            crystalyse_dir.mkdir()

            root = WritableRoot.from_path(tmppath)
            # .crystalyse should be in read_only_subpaths
            assert any(".crystalyse" in str(p) for p in root.read_only_subpaths)

    def test_from_path_empty_directory(self):
        """Test from_path on directory without .git or .crystalyse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            root = WritableRoot.from_path(tmppath)
            assert root.root == tmppath
            assert root.read_only_subpaths == ()


class TestSandboxPolicy:
    """Tests for SandboxPolicy dataclass."""

    def test_none_policy(self):
        """Test creating a no-restrictions policy."""
        policy = SandboxPolicy.none()
        assert policy.level == SandboxLevel.NONE
        assert policy.has_full_disk_write_access()
        assert policy.has_full_network_access()

    def test_read_only_policy(self):
        """Test creating a read-only policy."""
        policy = SandboxPolicy.read_only()
        assert policy.level == SandboxLevel.READ_ONLY
        assert not policy.has_full_disk_write_access()
        assert not policy.has_full_network_access()

    def test_read_only_with_network(self):
        """Test read-only policy with network access."""
        policy = SandboxPolicy.read_only(network_access=True)
        assert policy.level == SandboxLevel.READ_ONLY
        assert not policy.has_full_disk_write_access()
        assert policy.has_full_network_access()

    def test_workspace_policy(self):
        """Test creating a workspace policy."""
        cwd = Path("/home/user/project")
        policy = SandboxPolicy.workspace(cwd)
        assert policy.level == SandboxLevel.WORKSPACE
        assert not policy.has_full_disk_write_access()
        assert policy.has_full_network_access()
        assert cwd in policy.writable_roots

    def test_workspace_with_additional_roots(self):
        """Test workspace policy with additional writable roots."""
        cwd = Path("/home/user/project")
        extra = Path("/data/output")
        policy = SandboxPolicy.workspace(cwd, additional_roots=[extra])
        assert cwd in policy.writable_roots
        assert extra in policy.writable_roots

    def test_workspace_no_network(self):
        """Test workspace policy without network access."""
        cwd = Path("/home/user/project")
        policy = SandboxPolicy.workspace(cwd, network_access=False)
        assert not policy.has_full_network_access()

    def test_get_writable_roots_with_cwd_none_level(self):
        """Test get_writable_roots_with_cwd for NONE level."""
        policy = SandboxPolicy.none()
        roots = policy.get_writable_roots_with_cwd(Path("/somewhere"))
        assert roots == []  # Everything writable, no restrictions

    def test_get_writable_roots_with_cwd_read_only_level(self):
        """Test get_writable_roots_with_cwd for READ_ONLY level."""
        policy = SandboxPolicy.read_only()
        roots = policy.get_writable_roots_with_cwd(Path("/somewhere"))
        # Only /dev/null should be writable
        assert len(roots) == 1
        assert roots[0].root == Path("/dev/null")

    def test_get_writable_roots_with_cwd_workspace_level(self):
        """Test get_writable_roots_with_cwd for WORKSPACE level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            policy = SandboxPolicy.workspace(tmppath)
            roots = policy.get_writable_roots_with_cwd(tmppath)

            # Should include cwd and /tmp at minimum
            root_paths = [wr.root for wr in roots]
            assert any(tmppath.resolve() == rp or str(tmppath) in str(rp) for rp in root_paths)

    def test_get_writable_roots_deduplicates(self):
        """Test that get_writable_roots_with_cwd deduplicates paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Pass same path as cwd and additional root
            policy = SandboxPolicy.workspace(tmppath, additional_roots=[tmppath])
            roots = policy.get_writable_roots_with_cwd(tmppath)

            # Count how many times tmppath appears
            count = sum(1 for wr in roots if wr.root.resolve() == tmppath.resolve())
            assert count == 1  # Should only appear once


class TestParseGitdir:
    """Tests for _parse_gitdir helper function."""

    def test_parse_gitdir_file(self):
        """Test parsing a .git file (worktree pointer)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a gitdir
            gitdir = tmppath / "actual-gitdir"
            gitdir.mkdir()

            # Create .git file pointing to gitdir
            git_file = tmppath / ".git"
            git_file.write_text(f"gitdir: {gitdir}\n")

            result = _parse_gitdir(git_file)
            assert result is not None
            assert result.resolve() == gitdir.resolve()

    def test_parse_gitdir_relative_path(self):
        """Test parsing a .git file with relative path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create nested structure
            worktree = tmppath / "worktree"
            worktree.mkdir()
            gitdir = tmppath / ".git" / "worktrees" / "worktree"
            gitdir.mkdir(parents=True)

            # Create .git file with relative path
            git_file = worktree / ".git"
            git_file.write_text("gitdir: ../.git/worktrees/worktree\n")

            result = _parse_gitdir(git_file)
            assert result is not None

    def test_parse_gitdir_not_a_pointer(self):
        """Test parsing a file that's not a gitdir pointer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_file = Path(tmpdir) / ".git"
            git_file.write_text("not a gitdir pointer\n")

            result = _parse_gitdir(git_file)
            assert result is None

    def test_parse_gitdir_nonexistent(self):
        """Test parsing a nonexistent file."""
        result = _parse_gitdir(Path("/nonexistent/.git"))
        assert result is None
