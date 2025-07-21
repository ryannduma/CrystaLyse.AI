"""
Enhanced CLI with sophisticated UI components.

This module provides the enhanced CLI interface using the new UI components
with theming, gradients, and responsive design.
"""

import sys
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt

from .themes import theme_manager, ThemeType
from .components import (
    CrystaLyseHeader,
    StatusBar,
    ChatDisplay,
    InputPanel,
    ProgressIndicator,
    MaterialDisplay,
    ThemeSelector
)
from .gradients import create_gradient_text, GradientStyle


class EnhancedCLI:
    """Enhanced CLI with sophisticated UI components."""

    def __init__(self, theme_type: ThemeType = ThemeType.CRYSTALYSE_DARK):
        # Set up theme
        theme_manager.set_theme(theme_type)

        # Initialize console with theme
        self.console = Console(
            theme=theme_manager.current_theme.rich_theme,
            width=None,  # Auto-detect
            height=None,  # Auto-detect
            force_terminal=True,
            legacy_windows=False
        )

        # Initialize UI components
        self.header = CrystaLyseHeader(self.console)
        self.status_bar = StatusBar(self.console)
        self.chat_display = ChatDisplay(self.console)
        self.input_panel = InputPanel(self.console)
        self.progress_indicator = ProgressIndicator(self.console)
        self.material_display = MaterialDisplay(self.console)
        self.theme_selector = ThemeSelector(self.console)

        # State tracking
        self.current_session = None
        self.current_user = None
        self.context_items = 0
        self.memory_entries = 0

    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()

    def show_header(self, version: Optional[str] = None):
        """Display the main header."""
        header_panel = self.header.render(version)
        self.console.print(header_panel)

    def show_status_bar(self, model: str = "unknown"):
        """Display the status bar."""
        status_panel = self.status_bar.render(
            model=model,
            session_id=self.current_session,
            user_id=self.current_user,
            context_items=self.context_items,
            memory_entries=self.memory_entries
        )
        self.console.print(status_panel)

    def show_welcome_message(self, 
                           user_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           mode: str = "interactive"):
        """Display welcome message for interactive sessions."""
        self.current_user = user_id
        self.current_session = session_id

        # Create welcome content
        welcome_text = Text()
        welcome_text.append("Welcome to ", style="dim")
        gradient_text = create_gradient_text(
            "CrystaLyse.AI", 
            GradientStyle.CRYSTALYSE_BLUE,
            theme_manager.current_theme.get_gradient_colors()
        )
        welcome_text.append(gradient_text.plain, style=gradient_text.style)
        welcome_text.append(" - AI-Powered Materials Discovery\n\n", style="dim")

        if user_id:
            welcome_text.append(f"User: {user_id}\n", style="accent.green")

        if session_id:
            welcome_text.append(f"Session: {session_id}\n", style="accent.cyan")

        welcome_text.append(f"Mode: {mode.title()}\n\n", style="accent.blue")

        welcome_text.append("Available Commands:\n", style="title")
        commands = [
            ("/help", "Show available commands"),
            ("/exit", "Exit the session"),
            ("/history", "Show conversation history"),
            ("/clear", "Clear conversation"),
            ("/theme", "Change theme"),
            ("/status", "Show system status")
        ]

        for cmd, desc in commands:
            welcome_text.append(f"  {cmd}", style="accent.cyan")
            welcome_text.append(f" - {desc}\n", style="dim")

        welcome_panel = Panel(
            welcome_text,
            border_style=theme_manager.current_theme.colors.accent_blue,
            title="[bold]Session Started[/bold]",
            title_align="left",
            padding=(1, 2)
        )

        self.console.print(welcome_panel)

    def show_user_input(self, message: str, timestamp: Optional[str] = None):
        """Display user input message."""
        panel = self.chat_display.render_user_message(message, timestamp)
        self.console.print(panel)

    def show_assistant_response(self, message: str, timestamp: Optional[str] = None):
        """Display assistant response."""
        panel = self.chat_display.render_assistant_message(message, timestamp)
        self.console.print(panel)

    def show_system_message(self, message: str, message_type: str = "info"):
        """Display system message."""
        panel = self.chat_display.render_system_message(message, message_type)
        self.console.print(panel)

    def show_material_result(self, material: Dict[str, Any]):
        """Display material discovery result."""
        panel = self.material_display.render_material_result(material)
        self.console.print(panel)

    def show_progress(self, description: str = "Processing..."):
        """Show progress indicator."""
        return self.progress_indicator.create_progress(description)

    def show_status(self, message: str = "Working..."):
        """Show status indicator."""
        return self.progress_indicator.create_status(message)

    def get_user_input(self, prompt_text: str = "Enter your query") -> str:
        """Get user input with styled prompt."""
        prompt_display = self.input_panel.render_prompt(prompt_text)
        self.console.print(prompt_display)
        return Prompt.ask("", console=self.console)

    def show_theme_selector(self) -> int:
        """Show theme selection interface."""
        theme_panel = self.theme_selector.render_theme_selection()
        self.console.print(theme_panel)

        while True:
            try:
                choice = int(Prompt.ask("Theme", console=self.console))
                if 1 <= choice <= len(theme_manager.get_available_themes()):
                    return choice
                else:
                    self.show_system_message("Invalid choice. Please try again.", "error")
            except ValueError:
                self.show_system_message("Please enter a valid number.", "error")

    def change_theme(self, theme_type: ThemeType):
        """Change the current theme."""
        theme_manager.set_theme(theme_type)

        # Update console theme
        self.console.push_theme(theme_manager.current_theme.rich_theme)

        # Update component themes
        self.header.theme = theme_manager.current_theme
        self.status_bar.theme = theme_manager.current_theme
        self.chat_display.theme = theme_manager.current_theme
        self.input_panel.theme = theme_manager.current_theme
        self.progress_indicator.theme = theme_manager.current_theme
        self.material_display.theme = theme_manager.current_theme
        self.theme_selector.theme = theme_manager.current_theme

        self.show_system_message(f"Theme changed to {theme_type.value.replace('_', ' ').title()}", "success")

    def show_help(self):
        """Display help information."""
        help_text = Text()
        help_text.append("CrystaLyse.AI Help\n\n", style="title")

        sections = [
            ("Basic Commands", [
                ("/help", "Show this help message"),
                ("/exit", "Exit the current session"),
                ("/quit", "Exit the application"),
                ("/clear", "Clear the conversation history"),
                ("/history", "Show conversation history"),
            ]),
            ("Session Commands", [
                ("/status", "Show system status"),
                ("/theme", "Change visual theme"),
                ("/save <fact>", "Save information to memory"),
                ("/search <query>", "Search saved information"),
            ]),
            ("Material Discovery", [
                ("Query", "Describe the material you want to discover"),
                ("Example", "Find a lead-free perovskite for solar cells"),
                ("Example", "Analyze lithium battery cathode materials"),
                ("Example", "Design high-temperature superconductors"),
            ])
        ]

        for section_name, commands in sections:
            help_text.append(f"{section_name}:\n", style="accent.blue")
            for cmd, desc in commands:
                help_text.append(f"  {cmd}", style="accent.cyan")
                help_text.append(f" - {desc}\n", style="dim")
            help_text.append("\n")

        help_panel = Panel(
            help_text,
            border_style=theme_manager.current_theme.colors.accent_blue,
            title="[bold]Help[/bold]",
            title_align="left",
            padding=(1, 2)
        )

        self.console.print(help_panel)

    def show_error(self, error_message: str, details: Optional[str] = None):
        """Display error message with optional details."""
        error_text = Text()
        error_text.append("❌ Error: ", style="status.error")
        error_text.append(error_message, style="status.error")

        if details:
            error_text.append("\n\nDetails:\n", style="dim")
            error_text.append(details, style="dim")

        error_panel = Panel(
            error_text,
            border_style=theme_manager.current_theme.colors.error,
            title="[bold]Error[/bold]",
            title_align="left",
            padding=(1, 2)
        )

        self.console.print(error_panel)

    def show_analysis_result(self, result: Dict[str, Any]):
        """Display analysis result with enhanced formatting."""
        if result.get("status") == "completed":
            # Success case
            self.show_system_message("Analysis completed successfully!", "success")

            # Show discovery results
            if "discovery_result" in result:
                discovery_text = result["discovery_result"]

                # Try to parse as material data
                try:
                    import json
                    material_data = json.loads(discovery_text)
                    if isinstance(material_data, dict):
                        self.show_material_result(material_data)
                    else:
                        self.show_assistant_response(discovery_text)
                except (json.JSONDecodeError, TypeError):
                    self.show_assistant_response(discovery_text)

            # Show metrics if available
            if "metrics" in result:
                metrics = result["metrics"]
                metrics_text = Text()
                metrics_text.append("Performance Metrics:\n", style="title")

                for key, value in metrics.items():
                    if isinstance(value, dict):
                        continue  # Skip complex nested metrics
                    metrics_text.append(f"  {key.replace('_', ' ').title()}: ", style="dim")
                    metrics_text.append(f"{value}\n", style="accent.green")

                metrics_panel = Panel(
                    metrics_text,
                    border_style=theme_manager.current_theme.colors.accent_blue,
                    title="[bold]Metrics[/bold]",
                    title_align="left",
                    padding=(1, 2)
                )

                self.console.print(metrics_panel)

        else:
            # Error case
            error_msg = result.get("error", "Unknown error occurred")
            self.show_error(error_msg)

    def create_layout(self) -> Layout:
        """Create a full-screen layout for advanced UI."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=8),
            Layout(name="main", ratio=1),
            Layout(name="status", size=3),
            Layout(name="input", size=5)
        )

        return layout

    def run_interactive_session(self):
        """Run an interactive session with the enhanced UI."""
        self.clear_screen()
        self.show_header("1.0.0")
        self.show_welcome_message()

        while True:
            try:
                user_input = self.get_user_input("Your query")

                if not user_input.strip():
                    continue

                # Show user input
                self.show_user_input(user_input)

                # Handle commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                else:
                    # Process as regular query
                    with self.show_status("Analyzing materials..."):
                        # Simulate processing
                        import time
                        time.sleep(2)

                    # Show mock response
                    self.show_assistant_response(
                        f"Based on your query '{user_input}', I would recommend exploring "
                        f"perovskite materials with specific dopant configurations. "
                        f"Let me analyze the most promising candidates..."
                    )

            except KeyboardInterrupt:
                self.show_system_message("Session interrupted by user", "warning")
                break
            except EOFError:
                break

        self.show_system_message("Session ended", "info")

    def _handle_command(self, command: str):
        """Handle slash commands."""
        cmd = command.lower().strip()

        if cmd == '/help':
            self.show_help()
        elif cmd == '/exit' or cmd == '/quit':
            self.show_system_message("Goodbye!", "info")
            sys.exit(0)
        elif cmd == '/clear':
            self.clear_screen()
            self.show_header("1.0.0")
            self.show_system_message("Screen cleared", "info")
        elif cmd == '/theme':
            choice = self.show_theme_selector()
            theme_types = list(theme_manager.get_available_themes())
            if 1 <= choice <= len(theme_types):
                selected_theme = theme_types[choice - 1]
                self.change_theme(selected_theme)
        elif cmd == '/status':
            self.show_status_bar()
        else:
            self.show_system_message(f"Unknown command: {command}", "error")


def main():
    """Main entry point for the enhanced CLI."""
    cli = EnhancedCLI()
    cli.run_interactive_session()


if __name__ == "__main__":
    main()
