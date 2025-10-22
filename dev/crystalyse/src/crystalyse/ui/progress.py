"""
Provides a phase-aware progress display for the CrystaLyse CLI.
"""
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from typing import Optional

class PhaseAwareProgress:
    """
    Manages and displays a phase-aware progress indicator for long-running tasks.
    """
    def __init__(self, console: Console):
        self.console = console
        self.live: Optional[Live] = None
        self.current_phase = ""
        self.details = ""

    def _make_panel(self) -> Panel:
        """Creates the rich Panel for the current phase."""
        phase_map = {
            "INITIALIZING": ("⚙️", "Initializing...", "dim"),
            "THINKING": ("🧠", "Analyzing requirements...", "cyan"),
            "PLANNING": ("📋", "Creating strategy...", "magenta"),
            "EXECUTING_TOOLS": ("🔧", "Running computational tools...", "yellow"),
            "ANALYZING": ("📊", "Analyzing results...", "green"),
        }
        
        icon, description, color = phase_map.get(self.current_phase, ("⚙️", self.current_phase, "white"))

        table = Table.grid(expand=True)
        table.add_column(style=color)
        table.add_row(Spinner("dots", style=color), f" [bold]{description}[/bold]")
        if self.details:
            table.add_row("", f"   [dim]{self.details}[/dim]")
            
        return Panel(table, border_style=color, title="Current Status")

    def start(self):
        """Starts the live display."""
        self.live = Live(self._make_panel(), console=self.console, refresh_per_second=10, transient=True)
        self.live.start()

    def stop(self):
        """Stops the live display."""
        if self.live:
            self.live.stop()
            # The final message is now handled by the main CLI logic
            # self.console.print(f"[bold green]✓[/bold green] [green]Processing complete.[/green]")

    def update(self, phase: str, details: str = ""):
        """Updates the progress phase and details."""
        self.current_phase = phase
        self.details = details
        if self.live:
            self.live.update(self._make_panel())

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()