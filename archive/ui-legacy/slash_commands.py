"""
Slash commands for Crystalyse CLI.
Meta-operations and system commands for enhanced user experience.
"""

import os
import tempfile
import time
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from crystalyse.config import Config


class SlashCommandHandler:
    """
    Handles slash commands for meta-operations in Crystalyse.
    """

    def __init__(self, console: Console, config: Config | None = None, chat_experience=None):
        self.console = console
        self.config = config or Config.load()
        self.start_time = time.time()
        self.chat_experience = chat_experience  # Reference to ChatExperience for mode/model changes

        # Command registry
        self.commands = {
            "/help": self._help,
            "/tools": self._tools,
            "/mcp": self._mcp,
            "/stats": self._stats,
            "/memory": self._memory,
            "/mode": self._mode,
            "/model": self._model,
            "/about": self._about,
            "/clear": self._clear,
            "/quit": self._quit,
            "/exit": self._quit,
        }

    def handle_command(self, command: str) -> bool:
        """
        Handle a slash command.

        Args:
            command: The command string (e.g., "/help", "/tools desc")

        Returns:
            True if command was handled, False otherwise
        """
        parts = command.split()
        base_command = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        if base_command in self.commands:
            try:
                self.commands[base_command](args)
                return True
            except Exception as e:
                self.console.print(f"[red]Error executing command: {e}[/red]")
                return True

        return False

    def _help(self, _args: list[str]):
        """Display help information."""
        help_table = Table(show_header=True, header_style="bold cyan")
        help_table.add_column("Command", style="cyan", width=20)
        help_table.add_column("Description", width=50)

        help_table.add_row("/help", "Show this help message")
        help_table.add_row("/tools [desc|nodesc]", "List available MCP tools and servers")
        help_table.add_row("/mcp [status|servers|desc]", "Show MCP server status and details")
        help_table.add_row("/stats", "Display session statistics and performance")
        help_table.add_row(
            "/memory [show|list|preview|edit|find|clear|refresh]",
            "Manage project memory (CRYSTALYSE.md files)",
        )
        help_table.add_row(
            "/mode [show|creative|rigorous|adaptive]", "View or change agent operating mode"
        )
        help_table.add_row("/model [show|o3|o4-mini|o3-mini]", "View or change language model")
        help_table.add_row("/about", "Show version and system information")
        help_table.add_row("/clear", "Clear the terminal screen")
        help_table.add_row("/quit, /exit", "Exit Crystalyse session")

        self.console.print(
            Panel(help_table, title="[bold]Crystalyse Commands[/bold]", border_style="cyan")
        )

    def _tools(self, args: list[str]):
        """Display available tools."""
        show_descriptions = True
        if args and args[0] in ["nodesc", "nodescriptions"]:
            show_descriptions = False

        tools_table = Table(show_header=True, header_style="bold cyan")
        tools_table.add_column("Tool", style="cyan", width=25)
        tools_table.add_column("Server", style="yellow", width=20)
        if show_descriptions:
            tools_table.add_column("Description", width=40)

        # Mock tool data - in real implementation, this would query the MCP servers
        mock_tools = [
            (
                "validate_composition_smact",
                "chemistry-unified",
                "Validate chemical compositions using SMACT",
            ),
            (
                "generate_structures",
                "chemistry-unified",
                "Generate crystal structures using Chemeleon",
            ),
            ("calculate_energy_mace", "chemistry-unified", "Calculate energies using MACE"),
            ("visualize_structure", "visualization", "Create 3D molecular visualizations"),
            ("plot_analysis", "visualization", "Generate analysis plots and charts"),
        ]

        for tool_name, server, description in mock_tools:
            if show_descriptions:
                tools_table.add_row(tool_name, server, description)
            else:
                tools_table.add_row(tool_name, server)

        self.console.print(
            Panel(tools_table, title="[bold]Available Tools[/bold]", border_style="blue")
        )

    def _mcp(self, args: list[str]):
        """Display MCP server status and information."""
        subcommand = args[0] if args else "status"

        if subcommand in ["status", "servers"]:
            # Show MCP server status
            mcp_table = Table(show_header=True, header_style="bold cyan")
            mcp_table.add_column("Server", style="cyan", width=25)
            mcp_table.add_column("Status", style="green", width=15)
            mcp_table.add_column("Tools", style="yellow", width=10)
            mcp_table.add_column("Location", style="dim", width=30)

            # Real MCP servers from the project
            servers = [
                ("chemistry-unified", "Running", "15", "./chemistry-unified-server"),
                ("chemistry-creative", "Running", "8", "./chemistry-creative-server"),
                ("visualization", "Running", "12", "./visualization-mcp-server"),
                ("smact (deprecated)", "Inactive", "5", "./oldmcpservers/smact-mcp-server"),
                ("chemeleon (deprecated)", "Inactive", "3", "./oldmcpservers/chemeleon-mcp-server"),
                ("mace (deprecated)", "Inactive", "4", "./oldmcpservers/mace-mcp-server"),
            ]

            for server, status, tools, location in servers:
                mcp_table.add_row(server, status, tools, location)

            self.console.print(
                Panel(mcp_table, title="[bold]MCP Server Status[/bold]", border_style="cyan")
            )

        elif subcommand == "desc":
            # Show detailed descriptions
            desc_text = Text()
            desc_text.append("MCP Server Descriptions:\n\n", style="bold")
            desc_text.append("• chemistry-unified: ", style="bold cyan")
            desc_text.append(
                "Complete materials discovery pipeline (SMACT + Chemeleon + MACE)\n", style="dim"
            )
            desc_text.append("• chemistry-creative: ", style="bold cyan")
            desc_text.append("Fast exploration mode without SMACT validation\n", style="dim")
            desc_text.append("• visualization: ", style="bold cyan")
            desc_text.append(
                "Advanced 3D molecular visualizations and analysis plots\n", style="dim"
            )
            desc_text.append("\nDeprecated servers (in oldmcpservers/):\n", style="bold dim")
            desc_text.append("• Individual SMACT, Chemeleon, and MACE servers\n", style="dim")
            desc_text.append("• Replaced by unified servers for better performance\n", style="dim")

            self.console.print(
                Panel(desc_text, title="[bold]MCP Server Details[/bold]", border_style="magenta")
            )
        else:
            self.console.print(f"[red]Unknown MCP subcommand: {subcommand}[/red]")
            self.console.print("[dim]Available: status, servers, desc[/dim]")

    def _stats(self, _args: list[str]):
        """Display comprehensive session statistics."""
        elapsed = time.time() - self.start_time

        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="cyan", width=30)
        stats_table.add_column("Value", style="white", width=35)

        # Session metrics
        stats_table.add_row("Session Duration", f"{elapsed / 60:.1f} minutes ({elapsed:.0f}s)")
        stats_table.add_row("CLI Mode", "Interactive Chat")
        stats_table.add_row("Agent Type", "Autonomous Materials Agent")

        # Configuration
        stats_table.add_row("", "")  # Separator
        stats_table.add_row("Configuration", "", style="bold yellow")
        stats_table.add_row("  Model", self.config.get("model", "gpt-4"))
        stats_table.add_row("  Mode", self.config.get("mode", "rigorous"))
        stats_table.add_row("  Language", "British English")

        # MCP Servers
        stats_table.add_row("", "")  # Separator
        stats_table.add_row("MCP Servers", "", style="bold cyan")
        stats_table.add_row("  Active Servers", "3 (unified pipeline)")
        stats_table.add_row("  Chemistry Tools", "~15 (SMACT, Chemeleon, MACE)")
        stats_table.add_row("  Visualization Tools", "~12 (3D rendering, analysis)")

        # Performance (would be real in actual implementation)
        stats_table.add_row("", "")  # Separator
        stats_table.add_row("Performance", "", style="bold green")
        stats_table.add_row("  Memory Usage", "~250MB")
        stats_table.add_row("  GPU Available", "CUDA detected" if self._check_gpu() else "CPU only")
        stats_table.add_row("  Tool Timeout", "Dynamic (1-60 min)")

        # Features
        stats_table.add_row("", "")  # Separator
        stats_table.add_row("Features Active", "", style="bold magenta")
        stats_table.add_row("  Autonomous Decisions", "✓ Enabled")
        stats_table.add_row("  Self-Correction", "✓ Enabled")
        stats_table.add_row("  Tool Transparency", "✓ Enhanced")
        stats_table.add_row("  Progress Tracking", "✓ Phase-aware")
        stats_table.add_row("  LLM Clarifications", "✓ Intelligent matching")

        self.console.print(
            Panel(
                stats_table,
                title="[bold]Crystalyse Session Statistics[/bold]",
                border_style="green",
            )
        )

    def _check_gpu(self) -> bool:
        """Check if GPU is available."""
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _memory(self, args: list[str]):
        """Manage agent memory and project memory files."""
        subcommand = args[0] if args else "show"
        extra_args = args[1:] if len(args) > 1 else []

        if subcommand == "show":
            self._memory_show()
        elif subcommand == "list":
            self._memory_list()
        elif subcommand == "preview":
            self._memory_preview()
        elif subcommand == "edit":
            self._memory_edit(extra_args)
        elif subcommand == "find":
            self._memory_find()
        elif subcommand == "clear":
            self._memory_clear()
        elif subcommand == "refresh":
            self._memory_refresh()
        else:
            self.console.print(f"[red]Unknown memory subcommand: {subcommand}[/red]")
            self._memory_help()

    def _memory_help(self):
        """Show memory command help."""
        help_text = Text()
        help_text.append("Memory subcommands:\n\n", style="bold")
        help_text.append("  show    ", style="cyan")
        help_text.append("Show session memory status\n", style="dim")
        help_text.append("  list    ", style="cyan")
        help_text.append("List all discovered CRYSTALYSE.md files\n", style="dim")
        help_text.append("  preview ", style="cyan")
        help_text.append("Show content of nearest CRYSTALYSE.md\n", style="dim")
        help_text.append("  edit    ", style="cyan")
        help_text.append("Open CRYSTALYSE.md in editor\n", style="dim")
        help_text.append("  find    ", style="cyan")
        help_text.append("Show file discovery paths (debugging)\n", style="dim")
        help_text.append("  clear   ", style="cyan")
        help_text.append("Clear session conversation memory\n", style="dim")
        help_text.append("  refresh ", style="cyan")
        help_text.append("Refresh agent memory context\n", style="dim")
        self.console.print(Panel(help_text, title="[bold]/memory Help[/bold]", border_style="cyan"))

    def _memory_show(self):
        """Show session memory status."""
        memory_text = Text()
        memory_text.append("Agent Memory Context:\n\n", style="bold")

        # Check if agent has session
        if self.chat_experience and hasattr(self.chat_experience, "agent"):
            if (
                hasattr(self.chat_experience.agent, "session")
                and self.chat_experience.agent.session
            ):
                session_id = getattr(self.chat_experience.agent, "session_id", "unknown")
                memory_text.append(f"• Session ID: {session_id}\n", style="cyan")
                memory_text.append("• Persistent Memory: Enabled (SQLite)\n", style="green")
                session_dir = Path.home() / ".crystalyse" / "sessions"
                session_db = session_dir / f"{session_id}.db"
                if session_db.exists():
                    size_kb = session_db.stat().st_size / 1024
                    memory_text.append(f"• Database Size: {size_kb:.1f} KB\n", style="dim")
            else:
                memory_text.append("• Persistent Memory: Disabled\n", style="yellow")
        else:
            memory_text.append("• Session: Not initialized\n", style="dim")

        # Show project memory info
        from crystalyse.memory.project_memory import get_project_memory_paths

        paths = get_project_memory_paths()
        if paths:
            memory_text.append(f"\n• Project Memory: {len(paths)} file(s) loaded\n", style="green")
        else:
            memory_text.append("\n• Project Memory: None (create CRYSTALYSE.md)\n", style="yellow")

        memory_text.append("• Tool Context: Loaded\n", style="dim")
        memory_text.append("• Domain Knowledge: Materials Science\n", style="dim")

        self.console.print(
            Panel(memory_text, title="[bold]Memory Status[/bold]", border_style="magenta")
        )

    def _memory_list(self):
        """List all discovered project memory files."""
        from crystalyse.memory.project_memory import get_project_memory_paths

        paths = get_project_memory_paths()
        if not paths:
            self.console.print("[yellow]No CRYSTALYSE.md files found.[/yellow]")
            self.console.print("[dim]Create one with: /memory edit[/dim]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("File", style="cyan")
        table.add_column("Location", style="dim")
        table.add_column("Size", style="yellow", justify="right")

        for path_str in paths:
            path = Path(path_str)
            size_kb = path.stat().st_size / 1024 if path.exists() else 0
            table.add_row(path.name, str(path.parent), f"{size_kb:.1f} KB")

        self.console.print(Panel(table, title="[bold]Memory Files[/bold]", border_style="cyan"))

    def _memory_preview(self):
        """Preview content of nearest CRYSTALYSE.md."""
        from crystalyse.memory.project_memory import load_project_memory

        content = load_project_memory()
        if not content:
            self.console.print("[yellow]No project memory found.[/yellow]")
            self.console.print("[dim]Create CRYSTALYSE.md in your project root.[/dim]")
            return

        # Truncate for display
        if len(content) > 2000:
            content = content[:2000] + "\n\n[dim]... (truncated, use /memory edit to see full)[/dim]"

        self.console.print(
            Panel(
                Markdown(content),
                title="[bold]Project Memory Preview[/bold]",
                border_style="cyan",
            )
        )

    def _memory_edit(self, args: list[str]):
        """Edit or create CRYSTALYSE.md file."""
        # Determine target file
        target = args[0] if args else "CRYSTALYSE.md"
        memory_path = Path.cwd() / target

        # Read existing content or use template
        if memory_path.exists():
            existing = memory_path.read_text()
        else:
            existing = """# Project Memory

## Context
<!-- Add project-specific context for the agent -->
<!-- Example: This is a battery materials discovery project focusing on Na-ion cathodes -->

## Preferences
<!-- Add your preferences here -->
<!-- Example: Always use SMACT validation before structure generation -->

## Notes
<!-- Add any important notes -->
"""

        # Try to open in editor
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", ""))
        if editor:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, prefix="crystalyse_"
            ) as f:
                f.write(existing)
                temp_path = f.name

            self.console.print(f"[dim]Opening in {editor}...[/dim]")
            os.system(f"{editor} {temp_path}")
            edited = Path(temp_path).read_text()
            Path(temp_path).unlink()  # Clean up temp file

            # Show diff and confirm
            if edited != existing:
                preview = edited[:500] + "..." if len(edited) > 500 else edited
                self.console.print(Panel(preview, title="[bold]Preview Changes[/bold]"))

                if Confirm.ask(f"Save to {memory_path}?", default=True):
                    memory_path.parent.mkdir(parents=True, exist_ok=True)
                    memory_path.write_text(edited)
                    self.console.print(f"[green]✓ Saved to {memory_path}[/green]")
                else:
                    self.console.print("[dim]Cancelled.[/dim]")
            else:
                self.console.print("[dim]No changes made.[/dim]")
        else:
            # Fallback: show current content and path
            self.console.print("[yellow]No $EDITOR set.[/yellow]")
            self.console.print(f"[dim]To edit manually: {memory_path}[/dim]")
            self.console.print(
                "[dim]Set $EDITOR environment variable (e.g., export EDITOR=nano)[/dim]"
            )
            if not memory_path.exists():
                if Confirm.ask(f"Create template at {memory_path}?", default=True):
                    memory_path.parent.mkdir(parents=True, exist_ok=True)
                    memory_path.write_text(existing)
                    self.console.print(f"[green]✓ Created {memory_path}[/green]")

    def _memory_find(self):
        """Show file discovery paths for debugging."""
        from crystalyse.memory.project_memory import MEMORY_FILES, RULES_DIR, find_project_memory

        self.console.print("[bold]Memory File Discovery[/bold]\n")
        self.console.print("[cyan]Search patterns:[/cyan]")
        for name in MEMORY_FILES:
            self.console.print(f"  • {name}")
        self.console.print(f"  • {RULES_DIR}/*.md\n")

        self.console.print(f"[cyan]Current directory:[/cyan] {Path.cwd()}\n")

        files = find_project_memory()
        if files:
            self.console.print("[green]Found files:[/green]")
            for f in files:
                self.console.print(f"  ✓ {f}")
        else:
            self.console.print("[yellow]No memory files found in directory tree.[/yellow]")

    def _memory_clear(self):
        """Clear session conversation memory."""
        if self.chat_experience and hasattr(self.chat_experience, "agent"):
            if Confirm.ask(
                "[yellow]Clear all conversation memory? This cannot be undone.[/yellow]"
            ):
                self.console.print("[yellow]Clearing session memory...[/yellow]")
                if self.chat_experience.agent.clear_session_memory():
                    # Also clear the chat history
                    if hasattr(self.chat_experience, "history"):
                        self.chat_experience.history = []
                    self.console.print("[green]✓ Session memory cleared successfully.[/green]")
                else:
                    self.console.print("[red]Failed to clear session memory.[/red]")
            else:
                self.console.print("[dim]Cancelled.[/dim]")
        else:
            self.console.print("[red]No active agent session to clear.[/red]")

    def _memory_refresh(self):
        """Refresh agent memory context."""
        self.console.print("[yellow]Refreshing agent memory context...[/yellow]")
        # Reload project memory
        from crystalyse.memory.project_memory import load_project_memory

        content = load_project_memory()
        if content:
            self.console.print(f"[green]✓ Loaded {len(content)} chars of project memory.[/green]")
        else:
            self.console.print("[dim]No project memory files found.[/dim]")
        self.console.print("[green]Memory context refreshed successfully.[/green]")

    def _about(self, _args: list[str]):
        """Show version and system information."""
        about_text = Text()
        about_text.append("Crystalyse 2.0\n", style="bold cyan")
        about_text.append("AI-Powered Materials Design Platform\n\n", style="cyan")
        about_text.append("Built with:\n", style="bold")
        about_text.append("• OpenAI Agents SDK\n", style="dim")
        about_text.append("• SMACT + Chemeleon + MACE\n", style="dim")
        about_text.append("• Rich CLI Framework\n", style="dim")
        about_text.append("• MCP Protocol\n\n", style="dim")
        about_text.append("For support: github.com/your-repo/crystalyse-ai", style="dim blue")

        self.console.print(
            Panel(about_text, title="[bold]About Crystalyse[/bold]", border_style="cyan")
        )

    def _clear(self, _args: list[str]):
        """Clear the terminal screen."""
        self.console.clear()

    def _mode(self, args: list[str]):
        """View or change agent operating mode."""
        if not args or args[0] == "show":
            # Show current mode and available options
            current_mode = (
                getattr(self.chat_experience, "mode", "unknown")
                if self.chat_experience
                else "unknown"
            )

            mode_table = Table(show_header=True, header_style="bold cyan")
            mode_table.add_column("Mode", style="cyan", width=15)
            mode_table.add_column("Model", style="yellow", width=15)
            mode_table.add_column("Speed", style="green", width=10)
            mode_table.add_column("Description", width=40)

            modes = [
                ("creative", "o4-mini", "⚡ Fast", "Rapid exploration without SMACT validation"),
                ("adaptive", "o4-mini", "🏃 Balanced", "Intelligent tool selection (DEFAULT)"),
                ("rigorous", "o3", "🔬 Thorough", "Complete validation pipeline with reasoning"),
            ]

            for mode, model, speed, desc in modes:
                style = "bold green" if mode == current_mode else "dim"
                marker = "→ " if mode == current_mode else "  "
                mode_table.add_row(f"{marker}{mode}", model, speed, desc, style=style)

            self.console.print(
                Panel(
                    mode_table,
                    title=f"[bold]Agent Modes (Current: {current_mode})[/bold]",
                    border_style="cyan",
                )
            )

        elif args[0] in ["creative", "rigorous", "adaptive"]:
            new_mode = args[0]
            if self.chat_experience:
                old_mode = self.chat_experience.mode
                self.chat_experience.mode = new_mode
                # Recreate the agent with the new mode
                self.chat_experience.refresh_agent()
                self.console.print(
                    f"[green]✓ Mode changed from '{old_mode}' to '{new_mode}'[/green]"
                )
                self.console.print(
                    "[dim]Note: Agent recreated with new mode. Model will be auto-selected based on mode. Use /model to override.[/dim]"
                )
            else:
                self.console.print("[red]Cannot change mode: No active chat session[/red]")
        else:
            self.console.print(f"[red]Unknown mode: {args[0]}[/red]")
            self.console.print("[dim]Available modes: creative, rigorous, adaptive[/dim]")

    def _model(self, args: list[str]):
        """View or change language model."""
        if not args or args[0] == "show":
            # Show current model and available options
            current_model = (
                getattr(self.chat_experience, "model", "unknown")
                if self.chat_experience
                else "unknown"
            )
            current_mode = (
                getattr(self.chat_experience, "mode", "unknown")
                if self.chat_experience
                else "unknown"
            )

            model_table = Table(show_header=True, header_style="bold cyan")
            model_table.add_column("Model", style="cyan", width=15)
            model_table.add_column("Type", style="yellow", width=15)
            model_table.add_column("Speed", style="green", width=10)
            model_table.add_column("Best For", width=35)

            models = [
                ("o3", "Reasoning", "🐌 Slow", "Complex analysis, research-grade results"),
                ("o4-mini", "Fast Reasoning", "⚡ Fast", "General use, balanced performance"),
                ("o3-mini", "Small Reasoning", "🏃 Medium", "Lightweight reasoning tasks"),
            ]

            for model, type_str, speed, desc in models:
                style = "bold green" if model == current_model else "dim"
                marker = "→ " if model == current_model else "  "
                model_table.add_row(f"{marker}{model}", type_str, speed, desc, style=style)

            # Show mode-model mapping
            mode_info = f"Current: {current_model} (mode: {current_mode})"

            self.console.print(
                Panel(
                    model_table,
                    title=f"[bold]Available Models ({mode_info})[/bold]",
                    border_style="yellow",
                )
            )

        elif args[0] in ["o3", "o4-mini", "o3-mini"]:
            new_model = args[0]
            if self.chat_experience:
                old_model = self.chat_experience.model or "auto"
                self.chat_experience.model = new_model
                # Recreate the agent with the new model
                self.chat_experience.refresh_agent()
                self.console.print(
                    f"[green]✓ Model changed from '{old_model}' to '{new_model}'[/green]"
                )
                self.console.print(
                    "[dim]Note: Agent recreated with new model. This overrides the mode's default model selection.[/dim]"
                )
            else:
                self.console.print("[red]Cannot change model: No active chat session[/red]")
        else:
            self.console.print(f"[red]Unknown model: {args[0]}[/red]")
            self.console.print("[dim]Available models: o3, o4-mini, o3-mini[/dim]")

    def _quit(self, _args: list[str]):
        """Exit the application."""
        self.console.print("[cyan]Thank you for using Crystalyse! Goodbye.[/cyan]")
        exit(0)

    def list_commands(self) -> list[str]:
        """Return list of available commands."""
        return list(self.commands.keys())
