"""
Workspace management for Crystalyse projects.
"""

from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.tree import Tree

# A callback function that takes a path and content, and returns True if approved.
ApprovalCallback = Callable[[Path, str], bool]


class MaterialsWorkspace:
    """
    Manages a dedicated workspace for a research project.
    Ensures all file operations are contained within the project directory.
    """

    def __init__(
        self,
        project_name: str,
        base_path: Path | None = None,
        approval_callback: ApprovalCallback | None = None,
    ):
        self.base_path = base_path or Path.home() / "crystalyse_projects"
        self.project_name = project_name
        self.project_root = self.base_path / self.project_name
        self.approval_callback = approval_callback
        self.console = Console()

        self.project_root.mkdir(parents=True, exist_ok=True)

    def get_full_path(self, relative_path: str) -> Path:
        """
        Resolves a relative path to an absolute path within the workspace.
        Crucially, this prevents directory traversal attacks.
        """
        full_path = self.project_root.joinpath(relative_path).resolve()
        if self.project_root not in full_path.parents and full_path != self.project_root:
            raise PermissionError("Attempted to access a file outside the project workspace.")
        return full_path

    def write_file(self, relative_path: str, content: str) -> str:
        """
        Writes content to a file, requesting approval if a callback is set.
        """
        full_path = self.get_full_path(relative_path)

        if self.approval_callback:
            if not self.approval_callback(full_path, content):
                return f"Write operation to {relative_path} was not approved by the user."

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {relative_path}."
        except Exception as e:
            return f"Error writing to file {relative_path}: {e}"

    def read_file(self, relative_path: str) -> str:
        """Reads content from a file within the workspace."""
        full_path = self.get_full_path(relative_path)
        try:
            if not full_path.is_file():
                return f"Error: File not found at {relative_path}."
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file {relative_path}: {e}"

    def list_files(self, relative_path: str = ".") -> str:
        """Lists files and directories in a tree-like format."""
        full_path = self.get_full_path(relative_path)
        if not full_path.is_dir():
            return f"Error: Directory not found at {relative_path}."

        tree = Tree(f"[bold cyan]Workspace: {self.project_name}/{relative_path}[/bold cyan]")

        paths = sorted(full_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))

        for path in paths:
            if path.is_dir():
                tree.add(f"📁 [bold]{path.name}/[/bold]")
            else:
                tree.add(f"📄 {path.name}")

        # To capture the output of a rich Tree, we need to print it to a console
        # and capture the output. This is a bit of a workaround.
        from io import StringIO

        string_io = StringIO()
        temp_console = Console(file=string_io, force_terminal=True)
        temp_console.print(tree)
        return string_io.getvalue()
