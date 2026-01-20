"""
Manages the interactive chat user experience for Crystalyse.
"""

import logging
import os
from typing import Any

from openai import AsyncOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from crystalyse.agents.openai_agents_bridge import EnhancedCrystaLyseAgent
from crystalyse.config import Config
from crystalyse.ui.ascii_art import get_responsive_logo
from crystalyse.ui.enhanced_clarification import IntegratedClarificationSystem
from crystalyse.ui.provenance_bridge import PROVENANCE_AVAILABLE, CrystaLyseProvenanceHandler
from crystalyse.ui.slash_commands import SlashCommandHandler
from crystalyse.ui.trace_handler import ToolTraceHandler
from crystalyse.workspace import workspace_tools

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
        self.clarification_system = IntegratedClarificationSystem(self.console, user_id=user_id)
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

    async def _handle_clarification_request(
        self, request: workspace_tools.ClarificationRequest
    ) -> dict[str, Any]:
        """Handles the UI for asking the user clarifying questions with the integrated, adaptive system."""
        try:
            # The new system requires the original query to perform analysis
            if not self.current_query:
                self.console.print(
                    "[red]Error: Cannot handle clarification without the original query context.[/red]"
                )
                return self._simple_clarification_fallback(request)

            # NEW LOGIC: If the agent is explicitly asking specific questions, show them directly
            # This prevents the auto-configuration from overriding the agent's specific questions
            if self._agent_requested_specific_questions(request):
                self.console.print("\n[cyan]🔍 The agent has specific questions for you:[/cyan]")
                return self._simple_clarification_fallback(request)

            # CRITICAL: Check if we should skip clarification entirely before asking
            analysis = await self.clarification_system._analyze_query_with_llm(self.current_query)
            if analysis is None:
                # Fallback if LLM analysis fails
                self.console.print(
                    "[yellow]Warning: Query analysis failed, proceeding with clarification.[/yellow]"
                )
                analysis = None
                should_skip = False
            else:
                should_skip = await self.clarification_system._should_skip_clarification(
                    analysis, request
                )

            if should_skip:
                # Skip clarification and return smart assumptions
                return await self.clarification_system._handle_high_confidence_skip(
                    self.current_query, request, analysis, None, self.mode
                )

            answers = await self.clarification_system.analyze_and_clarify(
                self.current_query, request, self.mode
            )

            # Show personalization info if relevant
            if answers.get("_method") == "high_confidence_skip":
                self.console.print(
                    "\n[cyan]✨ Used your learned preferences to proceed quickly![/cyan]"
                )
            elif "personalization_confidence" in str(answers):
                self.console.print("\n[dim]💡 Adapting based on your interaction history...[/dim]")

            self.console.print("\n[green]Thank you! Continuing with the analysis...[/green]")
            return answers
        except Exception as e:
            self.console.print(f"[red]Error in adaptive clarification: {e}[/red]")
            return self._simple_clarification_fallback(request)

    def _agent_requested_specific_questions(
        self, request: workspace_tools.ClarificationRequest
    ) -> bool:
        """Check if the agent is asking specific, targeted questions that should be shown directly."""
        # If there are specific, well-formed questions, show them directly
        # This prevents auto-configuration from overriding agent's specific questions
        if not request.questions:
            return False

        # Check if questions are specific and actionable (not generic)
        specific_indicators = [
            "type",
            "application",
            "property",
            "constraint",
            "temperature",
            "material",
            "element",
            "performance",
            "method",
            "target",
        ]

        for question in request.questions:
            question_text = question.text.lower()
            if any(indicator in question_text for indicator in specific_indicators):
                return True

        return False

    def _simple_clarification_fallback(
        self, request: workspace_tools.ClarificationRequest
    ) -> dict[str, Any]:
        """Simple fallback clarification if the adaptive system fails."""
        self.console.print(
            Panel(
                "I need a few more details. Please answer the following:",
                title="[bold yellow][?] Clarification Needed[/bold yellow]",
                border_style="yellow",
            )
        )

        answers = {"_mode": self.mode}  # Ensure mode is preserved
        for q in request.questions:
            if q.options:
                answers[q.id] = Prompt.ask(
                    f"[bold]{q.text}[/bold]", choices=q.options, default=q.options[0]
                )
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
                    default="",
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

            self.console.print(
                Panel(
                    f"""[bold cyan]Your CrystaLyse Learning Profile[/bold cyan]

"""
                    f"User ID: {stats['user_id']}\n"
                    f"Interactions: {stats['interaction_count']}\n"
                    f"Detected Expertise: {stats['expertise_level']} ({stats['expertise_score']:.2f})\n"
                    f"Speed Preference: {stats['speed_preference']:.2f} (0=thorough, 1=fast)\n"
                    f"Preferred Mode: {stats['preferred_mode']}\n"
                    f"Personalization Active: {'Yes' if stats['personalization_active'] else 'No'}\n\n"
                    f"Domain Expertise:\n"
                    + "\n".join(
                        f"  {domain}: {score:.2f}"
                        for domain, score in stats["domain_expertise"].items()
                    )
                    + "\n\nSuccessful Modes:\n"
                    + "\n".join(
                        f"  {mode}: {score:.2f}"
                        for mode, score in stats["successful_modes"].items()
                    ),
                    title="[bold green]💡 Learning Stats[/bold green]",
                    border_style="green",
                )
            )
        except Exception as e:
            self.console.print(f"[red]Error retrieving stats: {e}[/red]")

    async def run_loop(self):
        """The main input/output loop for the chat experience."""
        self._show_welcome_banner()

        # NEW ARCHITECTURE: Disable agent clarification since we pre-process queries
        # workspace_tools.CLARIFICATION_CALLBACK = self._handle_clarification_request

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

                # Store the current query so the clarification callback can access it
                self.current_query = query

                # NEW ARCHITECTURE: Pre-process query through clarification system
                # IMPORTANT: Do this BEFORE appending to history so first query gets clarification
                enriched_query = await self._preprocess_query_with_clarification(query)

                # Append to history after preprocessing
                self.history.append({"role": "user", "content": query})

                # Create provenance handler for this query (always-on provenance capture)
                if PROVENANCE_AVAILABLE:
                    trace_handler = CrystaLyseProvenanceHandler(
                        console=self.console, config=self.config, mode=self.mode
                    )
                    self.provenance_handler = trace_handler
                    # Record the user's original query
                    trace_handler.set_user_query(query)
                    # Record enriched query if different from original
                    if enriched_query != query:
                        trace_handler.add_enriched_query(enriched_query)
                else:
                    trace_handler = ToolTraceHandler(self.console)

                results = await self.agent.discover(
                    enriched_query, history=self.history, trace_handler=trace_handler
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

                    # Optionally collect user feedback for learning
                    await self._collect_feedback_if_appropriate()

                else:
                    error_message = results.get("error", "An unknown error occurred.")
                    self._display_message(
                        "assistant", f"[bold red]Error:[/bold red] {error_message}"
                    )

                    # Record negative feedback for errors
                    self.clarification_system.record_user_feedback(
                        f"Error occurred: {error_message}", 0.2
                    )

            except KeyboardInterrupt:
                break
            except Exception as e:
                self._display_message(
                    "assistant", f"[bold red]An unexpected error occurred:[/bold red] {e}"
                )

        self.console.print("\n[bold cyan]Thank you for using Crystalyse! Goodbye.[/bold cyan]")

    async def _preprocess_query_with_clarification(self, raw_query: str) -> str:
        """
        NEW ARCHITECTURE: Pre-process the query through the clarification system.
        Uses LLM-based question generation for surgical, context-aware clarification.

        Flow: Raw Query -> Analysis -> LLM Question Generation -> [Questions if needed] -> Enriched Query -> Agent
        """
        try:
            # Skip clarification for follow-up queries (session has history)
            if len(self.history) > 0:
                # This is a follow-up query in an existing conversation
                return raw_query

            # Step 1: Analyze the query for completeness and expertise
            analysis = await self.clarification_system._analyze_query_with_llm(raw_query)

            if analysis is None:
                self.console.print(
                    "[yellow]Warning: Query analysis failed, proceeding with original query.[/yellow]"
                )
                return self._create_enriched_query(raw_query, {}, analysis)

            self.console.print(
                f"[dim]Query Analysis: {analysis.expertise_level} level, {analysis.specificity_score:.1%} specificity[/dim]"
            )

            # Step 2: Use LLM to generate surgical questions (or skip entirely)
            question_result = await self._generate_llm_questions(raw_query, analysis)

            # DEBUG: Log what the LLM decided
            logger.info(
                f"LLM Question Generation: should_skip={question_result['should_skip']}, num_questions={len(question_result['questions'])}"
            )
            logger.info(f"Question result: {question_result}")

            if question_result["should_skip"] or len(question_result["questions"]) == 0:
                # No clarification needed - show extracted info and proceed
                if question_result["extracted_info"]:
                    self._show_smart_auto_configuration(question_result["extracted_info"], analysis)
                return self._create_enriched_query(
                    raw_query, question_result["extracted_info"], analysis
                )

            # Step 3: Ask the generated questions
            potential_questions = [
                workspace_tools.Question(id=q["id"], text=q["text"], options=q.get("options"))
                for q in question_result["questions"]
            ]

            # Show GPT-5 generated questions for all expertise levels
            self.console.print(
                "\n[cyan]🔍 I need a few details to provide the best analysis:[/cyan]"
            )
            clarification_answers = await self._ask_clarification_questions_directly(
                potential_questions
            )

            # Merge extracted info with clarification answers
            merged_answers = {**question_result["extracted_info"], **clarification_answers}

            # Create enriched query with complete context
            return self._create_enriched_query(raw_query, merged_answers, analysis)

        except Exception as e:
            self.console.print(f"[red]Error in query preprocessing: {e}[/red]")
            logger.exception("Query preprocessing failed")
            return raw_query  # Fallback to original query

    def _create_enriched_query(self, original_query: str, context: dict[str, Any], analysis) -> str:
        """Create an enriched query with full context for the agent."""

        # Build context section
        context_lines = []
        for key, value in context.items():
            if not key.startswith("_") and value:
                context_lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        context_section = (
            "\n".join(context_lines) if context_lines else "No additional context provided."
        )

        # Create enriched query with clear structure
        enriched_query = f"""ORIGINAL USER REQUEST:
{original_query}

CONTEXT AND CONSTRAINTS:
{context_section}

ANALYSIS MODE: {self.mode}
EXPERTISE LEVEL: {analysis.expertise_level if analysis else "unknown"}

INSTRUCTIONS: This request has been pre-processed and clarified. You can proceed directly with analysis using the comprehensive_materials_analysis tool. All necessary context has been provided above."""

        return enriched_query

    async def _ask_clarification_questions_directly(
        self, questions: list[workspace_tools.Question]
    ) -> dict[str, Any]:
        """Ask clarification questions with intelligent, flexible response handling."""
        answers = {"_mode": self.mode}

        for question in questions:
            if question.options:
                # Show options but accept flexible responses
                options_text = "/".join(question.options)
                self.console.print(f"[bold]{question.text}[/bold] [{options_text}]")

                raw_answer = self.console.input("Your choice: ")

                # Smart response matching
                matched_answer = self._smart_match_response(
                    raw_answer, question.options, question.id
                )

                final_answer = None
                if matched_answer:
                    answers[question.id] = matched_answer
                    final_answer = matched_answer
                elif self._is_exit_signal(raw_answer):
                    self.console.print(
                        "[yellow]Understood - let's proceed with what you've provided.[/yellow]"
                    )
                    # Record the skip in provenance
                    if PROVENANCE_AVAILABLE and self.provenance_handler:
                        self.provenance_handler.add_clarification_exchange(
                            question=question.text,
                            answer="[skipped]",
                            question_id=question.id,
                            options=question.options,
                        )
                    break
                else:
                    # Accept the custom response and continue
                    self.console.print(f"[green]Got it: {raw_answer}[/green]")
                    answers[question.id] = raw_answer
                    answers[f"{question.id}_custom"] = True
                    final_answer = raw_answer

                # Record clarification exchange in provenance
                if final_answer and PROVENANCE_AVAILABLE and self.provenance_handler:
                    self.provenance_handler.add_clarification_exchange(
                        question=question.text,
                        answer=final_answer,
                        question_id=question.id,
                        options=question.options,
                    )
            else:
                answer = Prompt.ask(f"[bold]{question.text}[/bold]")
                if self._is_exit_signal(answer):
                    break
                answers[question.id] = answer
                # Record clarification exchange in provenance
                if PROVENANCE_AVAILABLE and self.provenance_handler:
                    self.provenance_handler.add_clarification_exchange(
                        question=question.text, answer=answer, question_id=question.id, options=None
                    )

        return answers

    def _smart_match_response(
        self, response: str, options: list[str], question_id: str
    ) -> str | None:
        """Intelligent response matching with flexibility and context awareness."""
        if not response or not response.strip():
            return options[0]  # Default to first option for empty response

        response_clean = response.strip().lower()

        # Direct case-insensitive match
        for option in options:
            if response_clean == option.lower():
                return option

        # Handle common variants and spelling
        variants = {
            "maximise": "maximize",
            "minimise": "minimize",
            "centre": "center",
            "colour": "color",
            "grey": "gray",
            "sulphur": "sulfur",
            "aluminium": "aluminum",
            "defence": "defense",
            # Temperature variants
            "mid": "mid-range",
            "middle": "mid-range",
            "medium": "mid-range",
            "low": "room temperature",
            "ambient": "room temperature",
            "high": "high temperature",
            "elevated": "high temperature",
            # Common abbreviations
            "rm temp": "room temperature",
            "rt": "room temperature",
            "pb free": "no toxic elements",
            "lead free": "no toxic elements",
            "te free": "no toxic elements",
            "tellurium free": "no toxic elements",
        }

        # Try variant matching
        normalized_response = variants.get(response_clean, response_clean)
        for option in options:
            if normalized_response == option.lower():
                return option

        # Partial matching (smart abbreviations and contains)
        for option in options:
            option_lower = option.lower()
            # Check if response is contained in option or vice versa (minimum 3 chars)
            if (response_clean in option_lower and len(response_clean) >= 3) or (
                option_lower in response_clean and len(option_lower) >= 3
            ):
                return option

        # Context-aware fuzzy matching
        fuzzy_matches = {
            "temperature_range": {
                "500": "Mid-range (400-700K)",
                "600": "Mid-range (400-700K)",
                "700": "Mid-range (400-700K)",
                "800": "High temperature (>700K)",
                "400": "Mid-range (400-700K)",
                "300": "Room temperature (<400K)",
            },
            "target_zt": {
                "high": "ZT ≥ 1.5 (high performance)",
                "good": "ZT ≥ 1.0 (competitive)",
                "decent": "ZT ≥ 0.5 (practical)",
                "best": "ZT ≥ 2.0 (cutting edge)",
                "1": "ZT ≥ 1.0 (competitive)",
                "2": "ZT ≥ 2.0 (cutting edge)",
            },
            "material_constraints": {
                "toxic": "No toxic elements (Pb, Te-free)",
                "safe": "No toxic elements (Pb, Te-free)",
                "abundant": "Earth-abundant only",
                "common": "Earth-abundant only",
                "stable": "Air-stable required",
                "pb": "No toxic elements (Pb, Te-free)",
                "te": "No toxic elements (Pb, Te-free)",
                "lead": "No toxic elements (Pb, Te-free)",
                "tellurium": "No toxic elements (Pb, Te-free)",
            },
        }

        if question_id in fuzzy_matches:
            for keyword, mapped_option in fuzzy_matches[question_id].items():
                if keyword in response_clean:
                    return mapped_option

        # If no match found, return None (will be handled as custom response)
        return None

    def _is_exit_signal(self, response: str) -> bool:
        """Check if user wants to exit/skip clarification."""
        exit_signals = [
            "quit",
            "exit",
            "stop",
            "cancel",
            "nevermind",
            "forget it",
            "skip",
            "pass",
            "none",
            "n/a",
            "not applicable",
            "done",
        ]

        response_lower = response.strip().lower()
        return any(signal in response_lower for signal in exit_signals)

    def _show_smart_auto_configuration(self, assumptions: dict[str, Any], analysis):
        """Show the smart auto-configuration panel."""
        assumption_lines = "\n".join(
            f"• {key.replace('_', ' ').title()}: {value}"
            for key, value in assumptions.items()
            if not key.startswith("_")
        )

        self.console.print(
            Panel(
                f"[bold green]🚀 Smart Auto-Configuration[/bold green]\n\n"
                f"Based on your {analysis.expertise_level}-level query, I'm proceeding with:\n{assumption_lines}\n\n"
                f"→ Using [bold]{self.mode}[/bold] mode for analysis.\n\n"
                f"[dim]If these assumptions are incorrect, you can provide more details in your next message.[/dim]",
                title="[bold cyan]⚡ High-Confidence Analysis[/bold cyan]",
                border_style="cyan",
            )
        )

    async def _generate_llm_questions(self, query: str, analysis) -> dict[str, Any]:
        """
        Use GPT-5 with Structured Outputs to generate surgical, context-aware clarification questions.
        Returns dict with: {"questions": [...], "should_skip": bool, "reasoning": str}
        """
        try:
            # Define Pydantic models for structured outputs
            from pydantic import BaseModel, Field

            class ClarificationQuestion(BaseModel):
                id: str
                text: str
                options: list[str] = Field(description="3-4 short, intelligent suggested choices")
                reasoning: str

            class ClarificationResponse(BaseModel):
                questions: list[ClarificationQuestion]
                should_skip: bool
                reasoning: str
                # Note: extracted_info removed due to strict schema incompatibility with additionalProperties

            # Get OpenAI client
            mdg_api_key = os.getenv("OPENAI_MDG_API_KEY")
            client = AsyncOpenAI(api_key=mdg_api_key) if mdg_api_key else AsyncOpenAI()

            # Load clarification prompt
            from pathlib import Path

            prompt_path = Path(__file__).parent.parent / "prompts" / "clarification_llm_prompt.md"
            with open(prompt_path) as f:
                clarification_prompt = f.read()

            # Prepare context
            analysis_context = f"""
Query Analysis Results:
- Expertise Level: {analysis.expertise_level}
- Specificity Score: {analysis.specificity_score:.2f}
- Domain Confidence: {analysis.domain_confidence:.2f}
- Technical Terms: {", ".join(analysis.technical_terms) if analysis.technical_terms else "None"}
- Should Skip Clarification (initial): {analysis.should_skip_clarification}
- Suggested Mode: {analysis.suggested_mode}
"""

            # Use GPT-5 with Structured Outputs via responses.parse()
            response = await client.responses.parse(
                model="gpt-5",
                reasoning={"effort": "low"},  # Minimal reasoning for faster responses
                text={"verbosity": "medium"},  # Medium verbosity for complete question generation
                input=[
                    {"role": "system", "content": clarification_prompt},
                    {
                        "role": "user",
                        "content": f"""Task: generate_questions

{analysis_context}

User Query: "{query}"

Generate expertise-aware clarification questions following these STRICT requirements:
- EXPERT (specificity ≥70%): Zero questions (skip)
- INTERMEDIATE (40-70%): Exactly 1-2 targeted, surgical questions
- NOVICE (<40%): MUST generate 2-4 educational questions (never fewer than 2)

For NOVICE users, be educational and comprehensive, not minimal. Help them explore the domain.

IMPORTANT: Every question MUST include 3-4 intelligent, domain-specific suggested choices in the "options" array.
Make choices short, clear, and scientifically relevant to the query context.""",
                    },
                ],
                text_format=ClarificationResponse,  # Pydantic model for structured output
                max_output_tokens=2048,  # Sufficient for question generation
            )

            # Get parsed Pydantic object directly - no JSON parsing needed!
            result = response.output_parsed

            # Convert Pydantic model to dict for compatibility
            questions_dict = {
                "questions": [q.model_dump() for q in result.questions],
                "should_skip": result.should_skip,
                "reasoning": result.reasoning,
                "extracted_info": {},  # Always empty dict (not included in Pydantic model due to strict schema)
            }

            logger.info(
                f"LLM question generation: {len(questions_dict['questions'])} questions, should_skip={questions_dict['should_skip']}"
            )

            return questions_dict

        except Exception as e:
            logger.warning(f"LLM question generation failed: {e}, falling back to empty questions")
            return {
                "questions": [],
                "should_skip": True,
                "reasoning": f"Error generating questions: {str(e)}",
                "extracted_info": {},  # Always include extracted_info
            }
