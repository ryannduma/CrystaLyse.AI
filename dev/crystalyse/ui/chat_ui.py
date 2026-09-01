"""
Manages the interactive chat user experience for Crystalyse.
"""

import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from crystalyse.agents.agents_bridge import EnhancedCrystaLyseAgent
from crystalyse.config import Config
from crystalyse.ui.ascii_art import get_responsive_logo
from crystalyse.ui.provenance_bridge import PROVENANCE_AVAILABLE, CrystaLyseProvenanceHandler
from crystalyse.ui.slash_commands import SlashCommandHandler
from crystalyse.ui.trace_handler import ToolTraceHandler

logger = logging.getLogger(__name__)


class ChatExperience:
    """
    Handles the entire interactive chat session, providing a polished
    user experience with real-time tool transparency and meta-commands.
    """

    def __init__(self, project: str, mode: str, model: str, user_id: str = "default"):
        self.project = project
        self.mode = mode
        self.model = model
        self.user_id = user_id
        self.console = Console()
        self.history: list[dict[str, Any]] = []
        self.slash_handler = SlashCommandHandler(self.console, chat_experience=self)
        self.current_query: str = ""
        self.agent = None  # Will be created in run_loop
        self.config = Config.load()  # Load config for provenance settings
        self.provenance_handler = None  # Will be created per query

    def _create_agent(self):
        """Create or recreate the agent with current mode and model settings."""
        return EnhancedCrystaLyseAgent(
            config=Config.load(),
            project_name=self.project,
            mode=self.mode,
            model=self.model,
        )

    def refresh_agent(self):
        """Recreate the agent when mode or model changes."""
        # Update global mode manager with new mode
        try:
            from crystalyse.agents.mode_injector import GlobalModeManager

            GlobalModeManager.set_mode(self.mode, lock_mode=True)
            self.console.print(f"[dim]Mode injection updated to '{self.mode}'[/dim]")
        except ImportError:
            pass  # Mode injector not available

        self.agent = self._create_agent()

    def _show_welcome_banner(self):
        """Displays a clean welcome banner with responsive ASCII art."""
        terminal_width = self.console.size.width
        logo = get_responsive_logo(terminal_width)

        # If ASCII art is too wide, fall back to simple text
        if isinstance(logo, str) and not logo.startswith(" "):
            # Text fallback
            banner_text = Text(justify="center")
            banner_text.append(logo + "\n", style="bold cyan")
            banner_text.append(
                "Your interactive materials science research partner.\n", style="cyan"
            )
            banner_text.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", style="dim")
            banner_text.append(
                "Type your query to begin, /help for commands, or 'quit' to exit.", style="dim"
            )
            self.console.print(Panel(banner_text, border_style="cyan"))
        else:
            # ASCII art display
            self.console.print(Text(logo, style="bold cyan", justify="center"))
            banner_text = Text(justify="center")
            banner_text.append(
                "Your interactive materials science research partner.\n", style="cyan"
            )
            banner_text.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", style="dim")
            banner_text.append(
                "Type your query to begin, /help for commands, or 'quit' to exit.", style="dim"
            )
            self.console.print(Panel(banner_text, border_style="cyan"))

    def _display_message(self, role: str, content: str):
        """Displays a message in a formatted panel."""
        if role == "user":
            panel = Panel(content, title="[bold green]You[/bold green]", border_style="green")
        else:  # assistant
            panel = Panel(content, title="[bold cyan]CrystaLyse[/bold cyan]", border_style="cyan")
        self.console.print(panel)

    def _display_provenance_summary(self, summary: dict[str, Any]):
        """Display provenance summary in a compact format."""
        from rich.table import Table

        # Create summary table
        table = Table(title="Provenance Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        # Add key metrics (using actual keys from summary)
        table.add_row("Session ID", summary.get("session_id", "N/A"))
        table.add_row("Materials Found", str(summary.get("materials_found", 0)))

        # Use mcp_operations (actual key) instead of mcp_tools_detected
        mcp_ops = summary.get("mcp_operations", 0)
        table.add_row("MCP Tool Calls", str(mcp_ops))

        # Show tool call breakdown
        tool_calls = summary.get("tool_calls_total", 0)
        table.add_row("Total Tool Calls", str(tool_calls))

        # Add file location (check both possible locations)
        session_info = summary.get("session_info", {})
        output_dir = session_info.get("output_dir") or summary.get("output_dir")
        if output_dir:
            table.add_row("Output Directory", str(output_dir))

        self.console.print("\n")
        self.console.print(table)
        self.console.print(
            f"[dim]Analyse with: crystalyse analyse-provenance --session {summary.get('session_id', 'N/A')}[/dim]\n"
        )

    async def run_loop(self):
        """The main input/output loop for the chat experience."""
        self._show_welcome_banner()

        # Create the initial agent
        self.agent = self._create_agent()

        while True:
            try:
                query = self.console.input("[bold green]➤ [/bold green]")
                if query.lower() in ["quit", "exit"]:
                    break
                if not query.strip():
                    continue

                # Handle slash commands
                if query.startswith("/"):
                    if self.slash_handler.handle_command(query):
                        continue
                    else:
                        self.console.print(f"[red]Unknown command: {query}[/red]")
                        self.console.print("[dim]Type /help for available commands[/dim]")
                        continue

                self._display_message("user", query)

                self.current_query = query

                # Append to history
                self.history.append({"role": "user", "content": query})

                # Create provenance handler for this query (always-on provenance capture)
                if PROVENANCE_AVAILABLE:
                    trace_handler = CrystaLyseProvenanceHandler(
                        console=self.console, config=self.config, mode=self.mode
                    )
                    self.provenance_handler = trace_handler
                    # Record the user's original query
                    trace_handler.set_user_query(query)
                else:
                    trace_handler = ToolTraceHandler(self.console)

                # Query goes straight to the agent with no preprocessing
                results = await self.agent.discover(
                    query, history=self.history, trace_handler=trace_handler
                )

                if results and results.get("status") == "completed":
                    response = results.get("response", "I don't have a response for that.")
                    self._display_message("assistant", response)
                    self.history.append({"role": "assistant", "content": response})

                    # Finalize and display provenance summary if available
                    if PROVENANCE_AVAILABLE and self.provenance_handler:
                        try:
                            summary = self.provenance_handler.finalize()
                            if summary and self.config.provenance.get("show_summary", True):
                                self._display_provenance_summary(summary)
                        except Exception as e:
                            self.console.print(
                                f"[dim yellow]Provenance summary unavailable: {e}[/dim yellow]"
                            )

                else:
                    error_message = results.get("error", "An unknown error occurred.")
                    self._display_message(
                        "assistant", f"[bold red]Error:[/bold red] {error_message}"
                    )

            except KeyboardInterrupt:
                break
            except Exception as e:
                self._display_message(
                    "assistant", f"[bold red]An unexpected error occurred:[/bold red] {e}"
                )

        self.console.print("\n[bold cyan]Thank you for using Crystalyse! Goodbye.[/bold cyan]")
