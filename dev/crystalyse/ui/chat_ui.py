
"""
Manages the interactive chat user experience for CrystaLyse.AI.
"""
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

from crystalyse.agents.openai_agents_bridge import EnhancedCrystaLyseAgent
from crystalyse.config import Config
from crystalyse.ui.trace_handler import ToolTraceHandler
from crystalyse.ui.ascii_art import get_responsive_logo
from crystalyse.ui.slash_commands import SlashCommandHandler
from crystalyse.ui.enhanced_clarification import IntegratedClarificationSystem
from crystalyse.workspace import workspace_tools

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
        self.history: List[Dict[str, Any]] = []
        self.slash_handler = SlashCommandHandler(self.console, chat_experience=self)
        self.clarification_system = IntegratedClarificationSystem(self.console, user_id=user_id)
        self.current_query: str = ""

    def _show_welcome_banner(self):
        """Displays a clean welcome banner with responsive ASCII art."""
        terminal_width = self.console.size.width
        logo = get_responsive_logo(terminal_width)
        
        # If ASCII art is too wide, fall back to simple text
        if isinstance(logo, str) and not logo.startswith(" "):
            # Text fallback
            banner_text = Text(justify="center")
            banner_text.append(logo + "\n", style="bold cyan")
            banner_text.append("Your interactive materials science research partner.\n", style="cyan")
            banner_text.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", style="dim")
            banner_text.append("Type your query to begin, /help for commands, or 'quit' to exit.", style="dim")
            self.console.print(Panel(banner_text, border_style="cyan"))
        else:
            # ASCII art display
            self.console.print(Text(logo, style="bold cyan", justify="center"))
            banner_text = Text(justify="center")
            banner_text.append("Your interactive materials science research partner.\n", style="cyan")
            banner_text.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", style="dim")
            banner_text.append("Type your query to begin, /help for commands, or 'quit' to exit.", style="dim")
            self.console.print(Panel(banner_text, border_style="cyan"))

    def _display_message(self, role: str, content: str):
        """Displays a message in a formatted panel."""
        if role == "user":
            panel = Panel(content, title="[bold green]You[/bold green]", border_style="green")
        else: # assistant
            panel = Panel(content, title="[bold cyan]CrystaLyse[/bold cyan]", border_style="cyan")
        self.console.print(panel)

    async def _handle_clarification_request(self, request: workspace_tools.ClarificationRequest) -> Dict[str, Any]:
        """Handles the UI for asking the user clarifying questions with the integrated, adaptive system."""
        try:
            # The new system requires the original query to perform analysis
            if not self.current_query:
                self.console.print("[red]Error: Cannot handle clarification without the original query context.[/red]")
                return self._simple_clarification_fallback(request)

            # CRITICAL: Check if we should skip clarification entirely before asking
            analysis = await self.clarification_system._analyze_query_with_llm(self.current_query)
            if analysis is None:
                # Fallback if LLM analysis fails
                self.console.print("[yellow]Warning: Query analysis failed, proceeding with clarification.[/yellow]")
                analysis = None
                should_skip = False
            else:
                should_skip = await self.clarification_system._should_skip_clarification(analysis, request)
            
            if should_skip:
                # Skip clarification and return smart assumptions
                return await self.clarification_system._handle_high_confidence_skip(
                    self.current_query, request, analysis
                )

            answers = await self.clarification_system.analyze_and_clarify(self.current_query, request)
            
            # Show personalization info if relevant
            if answers.get("_method") == "high_confidence_skip":
                self.console.print("\n[cyan]✨ Used your learned preferences to proceed quickly![/cyan]")
            elif "personalization_confidence" in str(answers):
                self.console.print("\n[dim]💡 Adapting based on your interaction history...[/dim]")
            
            self.console.print("\n[green]Thank you! Continuing with the analysis...[/green]")
            return answers
        except Exception as e:
            self.console.print(f"[red]Error in adaptive clarification: {e}[/red]")
            return self._simple_clarification_fallback(request)
    
    def _simple_clarification_fallback(self, request: workspace_tools.ClarificationRequest) -> Dict[str, Any]:
        """Simple fallback clarification if the adaptive system fails."""
        self.console.print(Panel(
            "I need a few more details. Please answer the following:",
            title="[bold yellow][?] Clarification Needed[/bold yellow]",
            border_style="yellow"
        ))
        
        answers = {}
        for q in request.questions:
            if q.options:
                answers[q.id] = Prompt.ask(f"[bold]{q.text}[/bold]", choices=q.options, default=q.options[0])
            else:
                answers[q.id] = Prompt.ask(f"[bold]{q.text}[/bold]")
        
        return answers
    
    async def _collect_feedback_if_appropriate(self):
        """Occasionally collect user feedback for learning (non-intrusive)."""
        import random
        
        # Only ask for feedback occasionally (10% chance) to avoid annoyance
        if random.random() < 0.1:
            try:
                feedback = Prompt.ask(
                    "\n[dim]Quick feedback (optional): How was that response? (good/ok/bad or press enter to skip)[/dim]",
                    default=""
                )
                
                if feedback.strip():
                    self.clarification_system.record_user_feedback(feedback)
                    self.console.print("[dim]Thanks! This helps me learn your preferences.[/dim]")
                    
            except KeyboardInterrupt:
                pass  # User doesn't want to provide feedback
    
    def show_user_stats(self):
        """Display user learning statistics."""
        try:
            stats = self.clarification_system.get_user_statistics()
            
            self.console.print(Panel(
                f"""[bold cyan]Your CrystaLyse Learning Profile[/bold cyan]

"""
                f"User ID: {stats['user_id']}\n"
                f"Interactions: {stats['interaction_count']}\n"
                f"Detected Expertise: {stats['expertise_level']} ({stats['expertise_score']:.2f})\n"
                f"Speed Preference: {stats['speed_preference']:.2f} (0=thorough, 1=fast)\n"
                f"Preferred Mode: {stats['preferred_mode']}\n"
                f"Personalization Active: {'Yes' if stats['personalization_active'] else 'No'}\n\n"
                f"Domain Expertise:\n" + 
                "\n".join(f"  {domain}: {score:.2f}" for domain, score in stats['domain_expertise'].items()) +
                "\n\nSuccessful Modes:\n" +
                "\n".join(f"  {mode}: {score:.2f}" for mode, score in stats['successful_modes'].items()),
                title="[bold green]💡 Learning Stats[/bold green]",
                border_style="green"
            ))
        except Exception as e:
            self.console.print(f"[red]Error retrieving stats: {e}[/red]")
    
    async def run_loop(self):
        """The main input/output loop for the chat experience."""
        self._show_welcome_banner()

        # Set the callback for the workspace tools
        workspace_tools.CLARIFICATION_CALLBACK = self._handle_clarification_request

        agent = EnhancedCrystaLyseAgent(
            config=Config.load(),
            project_name=self.project,
            mode=self.mode,
            model=self.model,
        )

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
                self.history.append({"role": "user", "content": query})
                
                # Store the current query so the clarification callback can access it
                self.current_query = query

                trace_handler = ToolTraceHandler(self.console)
                
                results = await agent.discover(
                    query,
                    history=self.history,
                    trace_handler=trace_handler
                )
                
                if results and results.get("status") == "completed":
                    response = results.get("response", "I don't have a response for that.")
                    self._display_message("assistant", response)
                    self.history.append({"role": "assistant", "content": response})
                    
                    # Optionally collect user feedback for learning
                    await self._collect_feedback_if_appropriate()
                    
                else:
                    error_message = results.get("error", "An unknown error occurred.")
                    self._display_message("assistant", f"[bold red]Error:[/bold red] {error_message}")
                    
                    # Record negative feedback for errors
                    self.clarification_system.record_user_feedback(f"Error occurred: {error_message}", 0.2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self._display_message("assistant", f"[bold red]An unexpected error occurred:[/bold red] {e}")

        self.console.print("\n[bold cyan]Thank you for using CrystaLyse.AI! Goodbye.[/bold cyan]")
