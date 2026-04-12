"""Tests for crystalyse.plan.cleanup — Feature 2.7 acceptance criteria.

Acceptance criteria from spec §5 Feature 2.7:
  - Synthetic old plan files are deleted
  - Git-tracked plans are not deleted
  - retention_days=0 does not delete latest.md symlink
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from crystalyse.plan.cleanup import cleanup_old_plans


def _make_old_plan(plans_dir: Path, name: str, age_days: int) -> Path:
    """Create a plan file with an artificially old mtime."""
    path = plans_dir / name
    path.write_text("---\nschema_version: '1.0'\n---\nOld plan.\n")
    old_time = time.time() - (age_days * 86400) - 100  # extra 100s buffer
    import os

    os.utime(path, (old_time, old_time))
    return path


class TestCleanupOldPlans:
    """Synthetic old plan files are deleted."""

    def test_old_plan_deleted(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_old_plan(plans_dir, "old-plan.md", age_days=60)

        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert len(deleted) == 1
        assert not (plans_dir / "old-plan.md").exists()

    def test_recent_plan_kept(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        recent = plans_dir / "recent-plan.md"
        recent.write_text("---\n---\nRecent.\n")

        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert len(deleted) == 0
        assert recent.exists()

    def test_mixed_old_and_recent(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_old_plan(plans_dir, "old.md", age_days=60)
        recent = plans_dir / "recent.md"
        recent.write_text("---\n---\nRecent.\n")

        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert len(deleted) == 1
        assert not (plans_dir / "old.md").exists()
        assert recent.exists()


class TestLatestSymlinkPreserved:
    """latest.md symlink is never deleted."""

    def test_latest_symlink_not_deleted(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        target = plans_dir / "actual-plan.md"
        target.write_text("plan content")
        latest = plans_dir / "latest.md"
        latest.symlink_to(target)

        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert latest.exists() or latest.is_symlink()
        assert "latest.md" not in [d.name for d in deleted]

    def test_retention_zero_deletes_nothing(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_old_plan(plans_dir, "ancient.md", age_days=365)
        latest = plans_dir / "latest.md"
        latest.symlink_to(plans_dir / "ancient.md")

        deleted = cleanup_old_plans(plans_dir, retention_days=0)
        assert len(deleted) == 0
        assert (plans_dir / "ancient.md").exists()


class TestGitTrackedPreserved:
    """Git-tracked plans are never deleted."""

    def test_git_tracked_plan_not_deleted(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_old_plan(plans_dir, "tracked-plan.md", age_days=60)

        # Mock git ls-files to return this file as tracked
        with patch("crystalyse.plan.cleanup._get_git_tracked_files") as mock_git:
            mock_git.return_value = {"tracked-plan.md"}
            deleted = cleanup_old_plans(plans_dir, retention_days=30)

        assert len(deleted) == 0
        assert (plans_dir / "tracked-plan.md").exists()

    def test_untracked_old_plan_deleted_tracked_kept(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_old_plan(plans_dir, "tracked.md", age_days=60)
        _make_old_plan(plans_dir, "untracked.md", age_days=60)

        with patch("crystalyse.plan.cleanup._get_git_tracked_files") as mock_git:
            mock_git.return_value = {"tracked.md"}
            deleted = cleanup_old_plans(plans_dir, retention_days=30)

        assert len(deleted) == 1
        assert (plans_dir / "tracked.md").exists()
        assert not (plans_dir / "untracked.md").exists()


class TestEdgeCases:
    def test_nonexistent_directory(self, tmp_path):
        deleted = cleanup_old_plans(tmp_path / "nope", retention_days=30)
        assert deleted == []

    def test_empty_directory(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert deleted == []

    def test_non_md_files_ignored(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        txt = plans_dir / "notes.txt"
        txt.write_text("not a plan")
        import os

        old_time = time.time() - 86400 * 60
        os.utime(txt, (old_time, old_time))

        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert len(deleted) == 0
        assert txt.exists()

    def test_symlink_files_not_deleted(self, tmp_path):
        """Symlinks (other than latest.md) are also skipped."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        target = plans_dir / "real.md"
        target.write_text("content")
        link = plans_dir / "alias.md"
        link.symlink_to(target)

        deleted = cleanup_old_plans(plans_dir, retention_days=30)
        assert len(deleted) == 0
