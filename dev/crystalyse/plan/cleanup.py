"""Plan cleanup policy (Feature 2.7).

Deletes plan files older than ``retention_days`` from
``.crystalyse/plans/``.  Runs cheaply (one directory scan) and is
safe to call on every ``crystalyse`` invocation.

Safety rules:
  - Git-tracked plans are never deleted (checked via ``git ls-files``).
  - The ``latest.md`` symlink is never deleted.
  - ``retention_days=0`` means "delete nothing" (not "delete everything").
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


def cleanup_old_plans(
    plans_dir: Path,
    retention_days: int,
) -> list[Path]:
    """Delete plan files older than *retention_days*.

    Parameters
    ----------
    plans_dir:
        The ``.crystalyse/plans/`` directory.
    retention_days:
        Plans older than this many days are eligible for deletion.
        ``0`` means no cleanup (keep everything).

    Returns
    -------
    list[Path]
        Paths that were deleted.
    """
    if retention_days <= 0:
        return []

    if not plans_dir.is_dir():
        return []

    cutoff = time.time() - (retention_days * 86400)
    git_tracked = _get_git_tracked_files(plans_dir)
    deleted: list[Path] = []

    for path in plans_dir.iterdir():
        # Never delete the latest.md symlink
        if path.name == "latest.md":
            continue

        # Only clean up .md files
        if not path.suffix == ".md":
            continue

        # Never delete symlinks (they point to other plan files)
        if path.is_symlink():
            continue

        # Never delete git-tracked files
        if path.name in git_tracked:
            continue

        # Check modification time
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        if mtime < cutoff:
            try:
                path.unlink()
                deleted.append(path)
            except OSError:
                pass

    return deleted


def _get_git_tracked_files(plans_dir: Path) -> set[str]:
    """Return the set of filenames in *plans_dir* that are tracked by git.

    Falls back to an empty set if git is not available or the directory
    is not inside a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(plans_dir)],
            capture_output=True,
            text=True,
            cwd=plans_dir.parent,
            timeout=5,
        )
        if result.returncode == 0:
            tracked = set()
            for line in result.stdout.strip().splitlines():
                # git ls-files returns paths relative to cwd
                tracked.add(Path(line).name)
            return tracked
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return set()
