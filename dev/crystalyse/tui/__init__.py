"""Terminal User Interface for Crystalyse.

A Textual-based TUI for interactive materials discovery sessions.
Provides a rich terminal interface with:
- Chat-style message display
- Collapsible tool execution output
- Status bar with model/token info
- Keyboard shortcuts for navigation
"""

from __future__ import annotations

# TUI components are imported conditionally to avoid textual dependency
# when not using TUI mode

__all__ = ["run_tui", "CrystalyseApp"]


def run_tui(rigorous: bool = False, session_id: str | None = None) -> None:
    """Launch the TUI application.

    Args:
        rigorous: Whether to use rigorous mode.
        session_id: Optional session ID to resume.
    """
    try:
        from .app import CrystalyseApp
    except ImportError as e:
        raise ImportError("TUI requires textual. Install with: pip install crystalyse[tui]") from e

    app = CrystalyseApp(rigorous=rigorous, session_id=session_id)
    app.run()


# Lazy import for type checking
def __getattr__(name: str):
    if name == "CrystalyseApp":
        from .app import CrystalyseApp

        return CrystalyseApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
