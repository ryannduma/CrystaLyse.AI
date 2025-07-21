#!/usr/bin/env python3
"""
Unified CLI Interface for CrystaLyse.AI

This provides a single, clean entry point similar to Gemini and Claude Code,
with a text input box and in-session mode switching.
"""

import sys
import asyncio
import logging
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt
from rich.layout import Layout
from rich.align import Align

# Enhanced UI Components
from crystalyse.ui.themes import ThemeManager, ThemeType
from crystalyse.ui.components import (
    CrystaLyseHeader, 
    ChatDisplay, 
    MaterialDisplay,
    ProgressIndicator
)
from crystalyse.ui.gradients import create_gradient_text, GradientStyle

# Import session-based system
try:
    from crystalyse.agents.session_based_agent import (
        CrystaLyseSession, 
        CrystaLyseSessionManager,
        get_session_manager
    )
    SESSION_BASED_AVAILABLE = True
except ImportError as e:
    SESSION_BASED_AVAILABLE = False

# Import legacy agent functionality
try:
    from crystalyse.agents.crystalyse_agent import analyse_materials
    LEGACY_AGENT_AVAILABLE = True
except ImportError as e:
    LEGACY_AGENT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class UnifiedCrystaLyseInterface:
    """Unified interface for CrystaLyse.AI with single entry point."""
    
    def __init__(self):
        # Initialize enhanced UI with red theme
        self.theme_manager = ThemeManager(ThemeType.CRYSTALYSE_RED)
        self.console = Console(
            theme=self.theme_manager.current_theme.rich_theme,
            width=None,
            height=None,
            force_terminal=True
        )
        
        # Initialize UI components
        self.header = CrystaLyseHeader(self.console)
        self.chat_display = ChatDisplay(self.console)
        self.material_display = MaterialDisplay(self.console)
        self.progress_indicator = ProgressIndicator(self.console)
        
        # Session state
        self.current_mode = "creative"  # creative or rigorous
        self.current_agent = "chat"     # chat or analyse
        self.current_user = "default"
        self.current_session = None
        self.session_manager = None
        
        # Initialize session manager if available
        if SESSION_BASED_AVAILABLE:
            self.session_manager = get_session_manager()
    
    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()
    
    def show_header(self):
        """Show the enhanced header."""
        header_panel = self.header.render("1.0.0")
        self.console.print(header_panel)
    
    def show_status_bar(self):
        """Show the status bar with current mode and agent."""
        # Create status content
        status_text = Text()
        
        # Mode indicator
        mode_color = "accent.red" if self.current_mode == "rigorous" else "accent.blue"
        status_text.append(f"Mode: {self.current_mode.title()}", style=mode_color)
        
        status_text.append(" | ", style="dim")
        
        # Agent indicator
        agent_color = "accent.green" if self.current_agent == "chat" else "accent.yellow"
        status_text.append(f"Agent: {self.current_agent.title()}", style=agent_color)
        
        status_text.append(" | ", style="dim")
        
        # User indicator
        status_text.append(f"User: {self.current_user}", style="accent.cyan")
        
        # Session indicator
        if self.current_session:
            status_text.append(" | ", style="dim")
            status_text.append(f"Session: {self.current_session.session_id}", style="accent.purple")
        
        # Create status panel
        status_panel = Panel(
            Align.center(status_text),
            border_style=self.theme_manager.current_theme.colors.border,
            padding=(0, 2)
        )
        
        self.console.print(status_panel)
    
    def show_input_prompt(self):
        """Show the clean text input interface."""
        # Create input panel content
        input_text = Text()
        input_text.append("Type your materials discovery query or use commands:\n\n", style="dim")
        
        # Show available commands
        commands = [
            ("/mode creative", "Switch to creative mode"),
            ("/mode rigorous", "Switch to rigorous mode"),
            ("/agent chat", "Switch to conversation mode"),
            ("/agent analyse", "Switch to one-shot analysis mode"),
            ("/help", "Show help"),
            ("/exit", "Exit")
        ]
        
        input_text.append("Available commands: ", style="comment")
        for i, (cmd, desc) in enumerate(commands):
            if i > 0:
                input_text.append(", ", style="dim")
            input_text.append(cmd, style="accent.cyan")
        
        # Create input panel
        input_panel = Panel(
            input_text,
            border_style=self.theme_manager.current_theme.colors.accent_red,
            padding=(1, 2)
        )
        
        self.console.print(input_panel)
    
    def get_user_input(self) -> str:
        """Get user input with enhanced prompt."""
        prompt_text = Text()
        prompt_text.append("➤ ", style="accent.red")
        
        self.console.print(prompt_text, end="")
        return Prompt.ask("", console=self.console)
    
    def handle_command(self, command: str) -> bool:
        """Handle in-session commands. Returns True if command was handled."""
        cmd = command.lower().strip()
        
        if cmd.startswith('/mode '):
            mode = cmd[6:].strip()
            if mode in ['creative', 'rigorous']:
                self.current_mode = mode
                self.show_system_message(f"Mode switched to {mode.title()}", "success")
                return True
            else:
                self.show_system_message("Invalid mode. Use 'creative' or 'rigorous'", "error")
                return True
        
        elif cmd.startswith('/agent '):
            agent = cmd[7:].strip()
            if agent in ['chat', 'analyse']:
                self.current_agent = agent
                self.show_system_message(f"Agent switched to {agent.title()}", "success")
                return True
            else:
                self.show_system_message("Invalid agent. Use 'chat' or 'analyse'", "error")
                return True
        
        elif cmd == '/help':
            self.show_help()
            return True
        
        elif cmd == '/exit':
            return False
        
        elif cmd == '/clear':
            self.clear_screen()
            self.show_interface()
            return True
        
        elif cmd.startswith('/'):
            self.show_system_message(f"Unknown command: {command}", "error")
            return True
        
        return False
    
    def show_system_message(self, message: str, message_type: str = "info"):
        """Show system message with styling."""
        panel = self.chat_display.render_system_message(message, message_type)
        self.console.print(panel)
    
    def show_help(self):
        """Show help information."""
        help_text = Text()
        help_text.append("CrystaLyse.AI Unified Interface Help\n\n", style="title")
        
        help_text.append("🎯 Modes:\n", style="accent.blue")
        help_text.append("  Creative  - Fast exploration and idea generation\n", style="dim")
        help_text.append("  Rigorous  - Complete computational validation\n\n", style="dim")
        
        help_text.append("🤖 Agents:\n", style="accent.green")
        help_text.append("  Chat     - Conversational interface with memory\n", style="dim")
        help_text.append("  Analyse  - One-shot analysis mode\n\n", style="dim")
        
        help_text.append("⚡ Commands:\n", style="accent.red")
        commands = [
            ("/mode creative", "Switch to creative mode"),
            ("/mode rigorous", "Switch to rigorous mode"),
            ("/agent chat", "Switch to conversation mode"),
            ("/agent analyse", "Switch to one-shot analysis mode"),
            ("/clear", "Clear screen"),
            ("/help", "Show this help"),
            ("/exit", "Exit interface")
        ]
        
        for cmd, desc in commands:
            help_text.append(f"  {cmd:<15} - {desc}\n", style="dim")
        
        help_text.append("\n💡 Examples:\n", style="accent.yellow")
        examples = [
            "find a novel photocatalyst for water splitting",
            "analyze the stability of LiCoO2 cathode materials",
            "suggest high-temperature superconductors",
            "explore perovskite solar cell materials"
        ]
        
        for example in examples:
            help_text.append(f"  • {example}\n", style="accent.cyan")
        
        help_panel = Panel(
            help_text,
            title="[bold]Help[/bold]",
            border_style=self.theme_manager.current_theme.colors.accent_blue,
            padding=(1, 2)
        )
        
        self.console.print(help_panel)
    
    def show_interface(self):
        """Show the main interface."""
        self.show_header()
        self.show_status_bar()
        self.show_input_prompt()
    
    async def process_query(self, query: str):
        """Process a user query based on current mode and agent."""
        # Show user input
        user_panel = self.chat_display.render_user_message(query)
        self.console.print(user_panel)
        
        try:
            if self.current_agent == "chat":
                await self.process_chat_query(query)
            else:  # analyse
                await self.process_analysis_query(query)
        except Exception as e:
            self.show_system_message(f"Error processing query: {str(e)}", "error")
    
    async def process_chat_query(self, query: str):
        """Process query in chat mode."""
        if not SESSION_BASED_AVAILABLE:
            self.show_system_message("Session-based chat not available due to missing MCP dependencies", "error")
            self.show_system_message("Please upgrade to Python 3.10+ and install MCP packages", "warning")
            self.show_system_message("Fallback: Using analysis mode for this query", "info")
            await self.process_analysis_query(query)
            return
        
        # Initialize session if needed
        if not self.current_session:
            session_id = f"unified_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_session = self.session_manager.get_or_create_session(
                session_id, self.current_user
            )
            await self.current_session.setup_agent(self.current_mode)
        
        # Process with session
        with self.console.status("[bold cyan]Processing query...", spinner="dots"):
            try:
                result = await self.current_session.run_with_history(query)
                response = result.get("response", "No response received")
                
                # Show response
                assistant_panel = self.chat_display.render_assistant_message(response)
                self.console.print(assistant_panel)
                
            except Exception as e:
                self.show_system_message(f"Chat processing failed: {str(e)}", "error")
    
    async def process_analysis_query(self, query: str):
        """Process query in analysis mode."""
        if not LEGACY_AGENT_AVAILABLE:
            self.show_system_message("Analysis functionality not available", "error")
            return
        
        # Process with analysis agent
        with self.console.status("[bold cyan]Running analysis...", spinner="dots"):
            try:
                # Use the legacy analysis function
                result = await analyse_materials(query, self.current_mode, self.current_user)
                
                # Show results
                if result.get("status") == "completed":
                    success_text = create_gradient_text(
                        "✅ Analysis Complete",
                        GradientStyle.CRYSTALYSE_RED,
                        self.theme_manager.current_theme.get_gradient_colors()
                    )
                    
                    # Show discovery result
                    discovery_result = result.get("discovery_result", "No result found.")
                    assistant_panel = self.chat_display.render_assistant_message(discovery_result)
                    self.console.print(assistant_panel)
                    
                    # Show metrics if available
                    metrics = result.get("metrics", {})
                    if metrics:
                        self.show_metrics(metrics)
                        
                else:
                    error_message = result.get("error", "Analysis failed")
                    self.show_system_message(error_message, "error")
                    
            except Exception as e:
                self.show_system_message(f"Analysis failed: {str(e)}", "error")
    
    def show_metrics(self, metrics: dict):
        """Show analysis metrics."""
        metrics_text = Text()
        metrics_text.append("Performance Metrics:\n", style="title")
        
        for key, value in metrics.items():
            if isinstance(value, (int, float, str)):
                metrics_text.append(f"  {key.replace('_', ' ').title()}: ", style="dim")
                metrics_text.append(f"{value}\n", style="accent.green")
        
        metrics_panel = Panel(
            metrics_text,
            title="[bold]Metrics[/bold]",
            border_style=self.theme_manager.current_theme.colors.accent_blue,
            padding=(1, 2)
        )
        
        self.console.print(metrics_panel)
    
    async def run(self):
        """Run the unified interface."""
        self.clear_screen()
        self.show_interface()
        
        # Main interaction loop
        while True:
            try:
                user_input = self.get_user_input()
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    should_continue = self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue
                
                # Process as query
                await self.process_query(user_input)
                
            except KeyboardInterrupt:
                self.show_system_message("Session interrupted", "warning")
                break
            except EOFError:
                break
        
        # Cleanup
        if self.current_session:
            await self.current_session.cleanup()
        
        self.show_system_message("Goodbye!", "info")


def main():
    """Main entry point for the unified interface."""
    interface = UnifiedCrystaLyseInterface()
    asyncio.run(interface.run())


if __name__ == "__main__":
    main() 