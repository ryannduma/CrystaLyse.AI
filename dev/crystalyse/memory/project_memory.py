"""Load project-specific instructions from CRYSTALYSE.md files.

Supports hierarchical project memory like Claude Code's CLAUDE.md:
- CRYSTALYSE.md in current directory
- .crystalyse/CRYSTALYSE.md for hidden config
- .crystalyse/rules/*.md for modular rules
"""

from pathlib import Path

MEMORY_FILES = ["CRYSTALYSE.md", ".crystalyse/CRYSTALYSE.md"]
RULES_DIR = ".crystalyse/rules"


def find_project_memory(cwd: Path | None = None) -> list[Path]:
    """Find all CRYSTALYSE.md files from cwd up to root.

    Walks up the directory tree looking for memory files and rules.
    Files closer to cwd take precedence (returned first).

    Args:
        cwd: Starting directory (defaults to current working directory)

    Returns:
        List of found memory file paths, ordered by proximity to cwd
    """
    if cwd is None:
        cwd = Path.cwd()

    memory_files = []
    current = cwd.resolve()

    while current != current.parent:
        for name in MEMORY_FILES:
            path = current / name
            if path.exists():
                memory_files.append(path)

        rules_dir = current / RULES_DIR
        if rules_dir.is_dir():
            memory_files.extend(sorted(rules_dir.glob("*.md")))

        current = current.parent

    return memory_files


def load_project_memory(cwd: Path | None = None) -> str:
    """Load and concatenate all project memory files.

    Combines all found CRYSTALYSE.md files and rules into a single
    string suitable for injection into agent instructions.

    Args:
        cwd: Starting directory (defaults to current working directory)

    Returns:
        Combined content of all memory files, or empty string if none found
    """
    files = find_project_memory(cwd)
    if not files:
        return ""

    base_cwd = cwd or Path.cwd()
    sections = []

    for path in files:
        content = path.read_text()
        try:
            relative = path.relative_to(base_cwd)
        except ValueError:
            relative = path
        sections.append(f"# From {relative}\n\n{content}")

    return "\n\n---\n\n".join(sections)


def get_project_memory_paths(cwd: Path | None = None) -> list[str]:
    """Get paths to all project memory files (for debugging/display).

    Args:
        cwd: Starting directory

    Returns:
        List of path strings
    """
    return [str(p) for p in find_project_memory(cwd)]
