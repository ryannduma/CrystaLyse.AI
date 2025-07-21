"""
UI Components for CrystaLyse.AI

Provides sophisticated UI components with theming and gradient support.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.status import Status
from rich.box import ROUNDED, SIMPLE, MINIMAL

from .themes import theme_manager
from .gradients import create_gradient_text, create_multiline_gradient_text, GradientStyle
from .ascii_art import get_logo_with_subtitle


class CrystaLyseHeader:
    """Sophisticated header component with responsive design."""

    def __init__(self, console: Console, show_version: bool = True):
        self.console = console
        self.show_version = show_version
        self.theme = theme_manager.current_theme

    def render(self, version: Optional[str] = None) -> Panel:
        """Render the header with logo and subtitle."""
        terminal_width = self.console.size.width

        # Get responsive logo
        logo, subtitle = get_logo_with_subtitle(terminal_width, version)

        # Apply gradient to logo
        gradient_logo = create_multiline_gradient_text(
            logo, 
            GradientStyle.CRYSTALYSE_BLUE,
            self.theme.get_gradient_colors()
        )

        # Create subtitle with theme colors
        subtitle_text = Text(subtitle, style="dim")

        # Combine logo and subtitle
        content = Text()
        content.append(gradient_logo.plain, style=gradient_logo.style)
        content.append("\n")
        content.append(subtitle_text.plain, style=subtitle_text.style)

        # Create panel with theme styling
        return Panel(
            Align.center(content),
            border_style=self.theme.colors.accent_blue,
            padding=(1, 2),
            box=ROUNDED
        )


class StatusBar:
    """Status bar component showing system information."""

    def __init__(self, console: Console):
        self.console = console
        self.theme = theme_manager.current_theme

    def render(self, 
               model: str = "unknown",
               session_id: Optional[str] = None,
               user_id: Optional[str] = None,
               context_items: int = 0,
               memory_entries: int = 0) -> Panel:
        """Render status bar with system information."""

        # Create status table
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")

        # Left side - model and session info
        left_content = Text()
        left_content.append("Model: ", style="dim")
        left_content.append(model, style="accent.blue")

        if session_id:
            left_content.append(" | Session: ", style="dim")
            left_content.append(session_id, style="accent.cyan")

        if user_id:
            left_content.append(" | User: ", style="dim")
            left_content.append(user_id, style="accent.green")

        # Right side - context and memory info
        right_content = Text()
        if context_items > 0:
            right_content.append(f"Context: {context_items}", style="accent.purple")

        if memory_entries > 0:
            if context_items > 0:
                right_content.append(" | ", style="dim")
            right_content.append(f"Memory: {memory_entries}", style="accent.yellow")

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        if right_content.plain:
            right_content.append(" | ", style="dim")
        right_content.append(timestamp, style="dim")

        table.add_row(left_content, right_content)

        return Panel(
            table,
            border_style=self.theme.colors.border,
            box=MINIMAL,
            padding=(0, 1)
        )


class ChatDisplay:
    """Chat display component with styled messages."""

    def __init__(self, console: Console):
        self.console = console
        self.theme = theme_manager.current_theme

    def render_user_message(self, message: str, timestamp: Optional[str] = None) -> Panel:
        """Render user message with styling."""
        content = Text()
        content.append("➤ ", style="chat.user")
        content.append(message, style="input")

        if timestamp:
            content.append(f" ({timestamp})", style="chat.timestamp")

        return Panel(
            content,
            border_style=self.theme.colors.accent_blue,
            title="[bold]You[/bold]",
            title_align="left",
            box=SIMPLE,
            padding=(0, 1)
        )

    def render_assistant_message(self, message: str, timestamp: Optional[str] = None) -> Panel:
        """Render assistant message with styling."""
        content = Text()
        content.append("🔬 ", style="chat.assistant")
        content.append(message, style="output")

        if timestamp:
            content.append(f" ({timestamp})", style="chat.timestamp")

        return Panel(
            content,
            border_style=self.theme.colors.accent_green,
            title="[bold]CrystaLyse.AI[/bold]",
            title_align="left",
            box=SIMPLE,
            padding=(0, 1)
        )

    def render_system_message(self, message: str, message_type: str = "info") -> Panel:
        """Render system message with appropriate styling."""
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }

        # Map message types to theme colors
        border_colors = {
            "info": self.theme.colors.info,
            "success": self.theme.colors.success,
            "warning": self.theme.colors.warning,
            "error": self.theme.colors.error
        }

        content = Text()
        content.append(f"{icons.get(message_type, 'ℹ️')} ", style="chat.system")
        content.append(message, style=f"status.{message_type}")

        return Panel(
            content,
            border_style=border_colors.get(message_type, self.theme.colors.info),
            title="[bold]System[/bold]",
            title_align="left",
            box=MINIMAL,
            padding=(0, 1)
        )


class InputPanel:
    """Input panel with prompt styling."""

    def __init__(self, console: Console):
        self.console = console
        self.theme = theme_manager.current_theme

    def render_prompt(self, prompt_text: str = "Enter your query") -> Text:
        """Render styled input prompt."""
        content = Text()
        content.append("➤ ", style="prompt")
        content.append(prompt_text, style="dim")
        return content

    def render_input_area(self, 
                         placeholder: str = "Describe the material you want to discover...",
                         show_commands: bool = True) -> Panel:
        """Render input area with instructions."""
        content = Text()
        content.append(placeholder, style="dim")

        if show_commands:
            content.append("\n\n")
            content.append("Commands: ", style="comment")
            content.append("/help", style="accent.cyan")
            content.append(" | ", style="dim")
            content.append("/exit", style="accent.red")
            content.append(" | ", style="dim")
            content.append("/history", style="accent.yellow")
            content.append(" | ", style="dim")
            content.append("/clear", style="accent.purple")

        return Panel(
            content,
            border_style=self.theme.colors.border,
            title="[bold]Input[/bold]",
            title_align="left",
            box=SIMPLE,
            padding=(1, 2)
        )


class ProgressIndicator:
    """Progress indicator with theming."""

    def __init__(self, console: Console):
        self.console = console
        self.theme = theme_manager.current_theme

    def create_progress(self, description: str = "Processing...") -> Progress:
        """Create a themed progress bar."""
        return Progress(
            SpinnerColumn(spinner_style="progress.bar"),
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=None, complete_style="progress.complete"),
            TaskProgressColumn(),
            console=self.console
        )

    def create_status(self, message: str = "Working...") -> Status:
        """Create a themed status indicator."""
        return Status(
            message,
            console=self.console,
            spinner="dots",
            spinner_style="progress.bar"
        )


class MaterialDisplay:
    """Display component for material discovery results."""

    def __init__(self, console: Console):
        self.console = console
        self.theme = theme_manager.current_theme

    def render_material_result(self, material: Dict[str, Any]) -> Panel:
        """Render material discovery result with enhanced formatting."""
        from rich.console import Group

        content_items = []

        # Material formula
        if "formula" in material:
            formula_text = create_gradient_text(
                material["formula"],
                GradientStyle.CRYSTALYSE_BLUE,
                self.theme.get_gradient_colors()
            )
            content_items.append(formula_text)
            content_items.append(Text())  # Empty line

        # Properties table
        if "properties" in material:
            table = Table.grid(expand=True, padding=(0, 1))
            table.add_column("Property", style="material.property")
            table.add_column("Value", style="material.value")
            table.add_column("Unit", style="material.unit")

            for prop, value in material["properties"].items():
                if isinstance(value, dict):
                    val_str = str(value.get("value", ""))
                    unit_str = value.get("unit", "")
                else:
                    val_str = str(value)
                    unit_str = ""

                table.add_row(prop.replace("_", " ").title(), val_str, unit_str)

            content_items.append(table)

        # Use Group to combine different content types
        content = Group(*content_items)

        return Panel(
            content,
            border_style=self.theme.colors.accent_blue,
            title="[bold]Material Discovery Result[/bold]",
            title_align="left",
            box=ROUNDED,
            padding=(1, 2)
        )


class ThemeSelector:
    """Theme selection component."""

    def __init__(self, console: Console):
        self.console = console
        self.theme = theme_manager.current_theme

    def render_theme_selection(self) -> Panel:
        """Render theme selection interface."""
        content = Text()
        content.append("Available Themes:\n\n", style="title")

        for i, theme_type in enumerate(theme_manager.get_available_themes(), 1):
            content.append(f"{i}. ", style="dim")
            content.append(theme_type.value.replace("_", " ").title(), 
                         style="accent.blue")
            content.append(f" - {theme_manager.get_theme_description(theme_type)}\n",
                         style="dim")

        content.append("\nEnter theme number: ", style="prompt")

        return Panel(
            content,
            border_style=self.theme.colors.border,
            title="[bold]Theme Selection[/bold]",
            title_align="left",
            box=ROUNDED,
            padding=(1, 2)
        )
