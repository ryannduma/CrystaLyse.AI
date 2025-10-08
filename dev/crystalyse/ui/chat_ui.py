
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
from crystalyse.ui.provenance_bridge import CrystaLyseProvenanceHandler, PROVENANCE_AVAILABLE
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

    def _display_provenance_summary(self, summary: Dict[str, Any]):
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
        self.console.print(f"[dim]Analyse with: crystalyse analyse-provenance --session {summary.get('session_id', 'N/A')}[/dim]\n")

    async def _handle_clarification_request(self, request: workspace_tools.ClarificationRequest) -> Dict[str, Any]:
        """Handles the UI for asking the user clarifying questions with the integrated, adaptive system."""
        try:
            # The new system requires the original query to perform analysis
            if not self.current_query:
                self.console.print("[red]Error: Cannot handle clarification without the original query context.[/red]")
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
                self.console.print("[yellow]Warning: Query analysis failed, proceeding with clarification.[/yellow]")
                analysis = None
                should_skip = False
            else:
                should_skip = await self.clarification_system._should_skip_clarification(analysis, request)
            
            if should_skip:
                # Skip clarification and return smart assumptions
                return await self.clarification_system._handle_high_confidence_skip(
                    self.current_query, request, analysis, None, self.mode
                )

            answers = await self.clarification_system.analyze_and_clarify(self.current_query, request, self.mode)
            
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
    
    def _agent_requested_specific_questions(self, request: workspace_tools.ClarificationRequest) -> bool:
        """Check if the agent is asking specific, targeted questions that should be shown directly."""
        # If there are specific, well-formed questions, show them directly
        # This prevents auto-configuration from overriding agent's specific questions
        if not request.questions:
            return False
        
        # Check if questions are specific and actionable (not generic)
        specific_indicators = [
            "type", "application", "property", "constraint", "temperature", 
            "material", "element", "performance", "method", "target"
        ]
        
        for question in request.questions:
            question_text = question.text.lower()
            if any(indicator in question_text for indicator in specific_indicators):
                return True
        
        return False
    
    def _simple_clarification_fallback(self, request: workspace_tools.ClarificationRequest) -> Dict[str, Any]:
        """Simple fallback clarification if the adaptive system fails."""
        self.console.print(Panel(
            "I need a few more details. Please answer the following:",
            title="[bold yellow][?] Clarification Needed[/bold yellow]",
            border_style="yellow"
        ))
        
        answers = {"_mode": self.mode}  # Ensure mode is preserved
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
                self.history.append({"role": "user", "content": query})
                
                # Store the current query so the clarification callback can access it
                self.current_query = query

                # NEW ARCHITECTURE: Pre-process query through clarification system
                enriched_query = await self._preprocess_query_with_clarification(query)

                # Create provenance handler for this query (always-on provenance capture)
                if PROVENANCE_AVAILABLE:
                    trace_handler = CrystaLyseProvenanceHandler(
                        console=self.console,
                        config=self.config,
                        mode=self.mode
                    )
                    self.provenance_handler = trace_handler
                else:
                    trace_handler = ToolTraceHandler(self.console)

                results = await self.agent.discover(
                    enriched_query,
                    history=self.history,
                    trace_handler=trace_handler
                )
                
                if results and results.get("status") == "completed":
                    response = results.get("response", "I don't have a response for that.")
                    self._display_message("assistant", response)
                    self.history.append({"role": "assistant", "content": response})

                    # Finalize and display provenance summary if available
                    if PROVENANCE_AVAILABLE and self.provenance_handler:
                        try:
                            summary = self.provenance_handler.finalize()
                            if summary and self.config.provenance.get('show_summary', True):
                                self._display_provenance_summary(summary)
                        except Exception as e:
                            self.console.print(f"[dim yellow]Provenance summary unavailable: {e}[/dim yellow]")

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
    
    async def _preprocess_query_with_clarification(self, raw_query: str) -> str:
        """
        NEW ARCHITECTURE: Pre-process the query through the clarification system.
        This replaces the old dual-responsibility model where both agent and clarification
        system tried to handle questions.
        
        Flow: Raw Query -> Analysis -> [Questions if needed] -> Enriched Query -> Agent
        """
        try:
            # Step 1: Analyze the query for completeness and expertise
            analysis = await self.clarification_system._analyze_query_with_llm(raw_query)
            
            if analysis is None:
                self.console.print("[yellow]Warning: Query analysis failed, proceeding with original query.[/yellow]")
                return self._create_enriched_query(raw_query, {}, analysis)
            
            self.console.print(f"[dim]Query Analysis: {analysis.expertise_level} level, {analysis.specificity_score:.1%} specificity[/dim]")
            
            # Step 2: Intelligent clarification decision
            potential_questions = self._generate_questions_for_query(raw_query, analysis)
            
            # For expert queries with high specificity, skip clarification if no questions needed
            if analysis.expertise_level == "expert" and analysis.specificity_score > 0.8:
                needs_clarification = len(potential_questions) > 0  # Only ask if we have unanswered questions
            else:
                needs_clarification = len(potential_questions) > 0 and not analysis.should_skip_clarification
            
            if needs_clarification:
                # Step 3a: Use adaptive clarification based on expertise
                if analysis.expertise_level == "novice" and analysis.specificity_score < 0.4:
                    # Educational approach for novice users
                    clarification_answers = await self._handle_novice_clarification(raw_query, potential_questions)
                else:
                    # Direct questions for intermediate/expert users
                    self.console.print("\n[cyan]🔍 I need a few details to provide the best analysis:[/cyan]")
                    clarification_answers = await self._ask_clarification_questions_directly(potential_questions)
                
                # Create enriched query with clarification context
                return self._create_enriched_query(raw_query, clarification_answers, analysis)
            
            else:
                # Step 3b: Use smart auto-configuration for expert queries
                # Generate template questions for context, but extract answers from the query itself
                template_questions = self._generate_template_questions_for_context(raw_query, analysis)
                smart_assumptions = self._extract_info_from_expert_query(raw_query, template_questions)
                
                # Show auto-configuration
                self._show_smart_auto_configuration(smart_assumptions, analysis)
                
                # Create enriched query with assumptions
                return self._create_enriched_query(raw_query, smart_assumptions, analysis)
                
        except Exception as e:
            self.console.print(f"[red]Error in query preprocessing: {e}[/red]")
            return raw_query  # Fallback to original query
    
    def _generate_questions_for_query(self, query: str, analysis) -> List[workspace_tools.Question]:
        """Generate appropriate clarification questions based on query analysis, but only for missing information."""
        questions = []
        query_lower = query.lower()
        
        # SMART FILTERING: Only ask questions if information is NOT already provided
        
        # Thermoelectric-specific questions
        if "thermoelectric" in query_lower or "zt" in query_lower:
            # Temperature range - only ask if not specified
            if not self._has_temperature_info(query):
                questions.append(workspace_tools.Question(
                    id="temperature_range",
                    text="What temperature range is most important for your application?",
                    options=["Room temperature (<400K)", "Mid-range (400-700K)", "High temperature (>700K)", "Full range (300-1000K)"]
                ))
            
            # ZT target - only ask if not mentioned
            if not self._has_zt_target(query):
                questions.append(workspace_tools.Question(
                    id="target_zt",
                    text="What minimum ZT value are you targeting?",
                    options=["ZT ≥ 0.5 (practical)", "ZT ≥ 1.0 (competitive)", "ZT ≥ 1.5 (high performance)", "ZT ≥ 2.0 (cutting edge)"]
                ))
            
            # Material constraints - only ask if not specified
            if not self._has_material_constraints(query):
                questions.append(workspace_tools.Question(
                    id="material_constraints",
                    text="Are there specific material constraints?",
                    options=["No toxic elements (Pb, Te-free)", "Earth-abundant only", "Air-stable required", "No specific constraints"]
                ))
            
            # Processing method - only ask if not mentioned
            if not self._has_processing_info(query):
                questions.append(workspace_tools.Question(
                    id="processing_method",
                    text="What fabrication method will you use?",
                    options=["Bulk polycrystalline", "Thin film", "Single crystal", "Nanostructured"]
                ))
        
        # Battery-specific questions  
        elif "battery" in query_lower or "cathode" in query_lower or "anode" in query_lower:
            questions.extend([
                workspace_tools.Question(
                    id="battery_type",
                    text="What type of battery system?",
                    options=["Li-ion", "Na-ion", "Mg-ion", "Solid-state", "Other"]
                ),
                workspace_tools.Question(
                    id="key_property",
                    text="What's the most important property?",
                    options=["High capacity", "Long cycle life", "Fast charging", "Safety", "Low cost"]
                )
            ])
        
        # General materials questions
        else:
            questions.extend([
                workspace_tools.Question(
                    id="application_area",
                    text="What's the primary application area?",
                    options=["Energy storage", "Thermoelectrics", "Catalysis", "Electronics", "Structural", "Other"]
                ),
                workspace_tools.Question(
                    id="performance_priority",
                    text="What's most important for this application?",
                    options=["Highest performance", "Cost effectiveness", "Stability/durability", "Ease of synthesis"]
                )
            ])
        
        return questions
    
    def _has_temperature_info(self, query: str) -> bool:
        """Check if temperature information is already provided in the query."""
        temp_indicators = [
            r"\d+\s*[–-]\s*\d+\s*k",  # "500–800 K"
            r"\d+\s*to\s*\d+\s*k",     # "500 to 800 K"
            r"mid.?temperature",        # "mid-temperature"
            r"high.?temperature",       # "high-temperature"
            r"room.?temperature",       # "room temperature"
            r"\d+\s*k",                # "600K"
            r"\d+\s*°c",               # "300°C"
        ]
        
        import re
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in temp_indicators)
    
    def _has_zt_target(self, query: str) -> bool:
        """Check if ZT target information is provided."""
        zt_indicators = [
            r"zt\s*[>≥]\s*\d",         # "ZT > 1"
            r"high\s+zt",              # "high ZT"
            r"zt\s+value",             # "ZT value"
            r"figure\s+of\s+merit",    # "figure of merit"
        ]
        
        import re
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in zt_indicators)
    
    def _has_material_constraints(self, query: str) -> bool:
        """Check if material constraints are mentioned."""
        constraint_indicators = [
            r"avoid.*lead",             # "avoid lead"
            r"avoid.*tellurium",        # "avoid tellurium"
            r"pb.*free",               # "Pb-free"
            r"te.*free",               # "Te-free"
            r"earth.?abundant",        # "earth-abundant"
            r"toxic",                  # "toxic"
            r"supply\s+concern",       # "supply concerns"
            r"stable\s+in\s+air",     # "stable in air"
        ]
        
        import re
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in constraint_indicators)
    
    def _has_processing_info(self, query: str) -> bool:
        """Check if processing/fabrication information is provided."""
        processing_indicators = [
            r"bulk\s+polycrystalline", # "bulk polycrystalline"
            r"sintering",              # "sintering"
            r"hot\s+pressing",         # "hot pressing"
            r"fabrication",            # "fabrication"
            r"processing",             # "processing"
            r"thin\s+film",           # "thin film"
            r"single\s+crystal",      # "single crystal"
        ]
        
        import re
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in processing_indicators)
    
    def _generate_template_questions_for_context(self, query: str, analysis) -> List[workspace_tools.Question]:
        """Generate template questions for context, regardless of whether they're answered in the query."""
        questions = []
        query_lower = query.lower()
        
        # Always generate thermoelectric template questions for context
        if "thermoelectric" in query_lower or "zt" in query_lower:
            questions.extend([
                workspace_tools.Question(
                    id="temperature_range",
                    text="Temperature range",
                    options=["Room temperature (<400K)", "Mid-range (400-700K)", "High temperature (>700K)", "Full range (300-1000K)"]
                ),
                workspace_tools.Question(
                    id="target_zt",
                    text="Target ZT value",
                    options=["ZT ≥ 0.5 (practical)", "ZT ≥ 1.0 (competitive)", "ZT ≥ 1.5 (high performance)", "ZT ≥ 2.0 (cutting edge)"]
                ),
                workspace_tools.Question(
                    id="material_constraints",
                    text="Material constraints",
                    options=["No toxic elements (Pb, Te-free)", "Earth-abundant only", "Air-stable required", "No specific constraints"]
                ),
                workspace_tools.Question(
                    id="processing_method",
                    text="Processing method",
                    options=["Bulk polycrystalline", "Thin film", "Single crystal", "Nanostructured"]
                )
            ])
        
        return questions
    
    def _extract_info_from_expert_query(self, query: str, template_questions: List[workspace_tools.Question]) -> Dict[str, Any]:
        """Extract information directly from expert query text."""
        import re
        query_lower = query.lower()
        extracted_info = {}
        
        # Temperature range extraction
        if "500" in query and "800" in query:
            extracted_info["temperature_range"] = "Mid-range (500-800K) - explicitly specified"
        elif "mid-temperature" in query_lower or "mid temperature" in query_lower:
            extracted_info["temperature_range"] = "Mid-range (400-700K)"
        
        # ZT target extraction
        if "high zt" in query_lower:
            extracted_info["target_zt"] = "High ZT values - explicitly requested"
        
        # Material constraints extraction
        constraints = []
        if "avoid" in query_lower and ("lead" in query_lower or "pb" in query_lower):
            constraints.append("Lead-free")
        if "avoid" in query_lower and ("tellurium" in query_lower or "te" in query_lower):
            constraints.append("Tellurium-free")
        if "earth-abundant" in query_lower or "earth abundant" in query_lower:
            constraints.append("Earth-abundant")
        if "stable in air" in query_lower:
            constraints.append("Air-stable")
        
        if constraints:
            extracted_info["material_constraints"] = ", ".join(constraints) + " - explicitly specified"
        
        # Processing method extraction
        if "bulk polycrystalline" in query_lower:
            extracted_info["processing_method"] = "Bulk polycrystalline - explicitly specified"
        elif "sintering" in query_lower or "hot pressing" in query_lower:
            extracted_info["processing_method"] = "Bulk polycrystalline (sintering/hot pressing)"
        
        # Material class preferences
        material_classes = []
        if "zintl" in query_lower:
            material_classes.append("Zintl phases")
        if "oxide thermoelectric" in query_lower:
            material_classes.append("Oxide thermoelectrics")
        
        if material_classes:
            extracted_info["material_classes"] = ", ".join(material_classes) + " - explicitly mentioned"
        
        # Add isotropy/processability requirements
        if "isotropy" in query_lower or "isotropic" in query_lower:
            extracted_info["structural_requirements"] = "Structurally isotropic - explicitly required"
        
        return extracted_info
    
    async def _ask_clarification_questions_directly(self, questions: List[workspace_tools.Question]) -> Dict[str, Any]:
        """Ask clarification questions with intelligent, flexible response handling."""
        answers = {"_mode": self.mode}
        
        for question in questions:
            if question.options:
                # Show options but accept flexible responses
                options_text = "/".join(question.options)
                self.console.print(f"[bold]{question.text}[/bold] [{options_text}]")
                
                raw_answer = self.console.input("Your choice: ")
                
                # Smart response matching
                matched_answer = self._smart_match_response(raw_answer, question.options, question.id)
                
                if matched_answer:
                    answers[question.id] = matched_answer
                elif self._is_exit_signal(raw_answer):
                    self.console.print("[yellow]Understood - let's proceed with what you've provided.[/yellow]")
                    break
                else:
                    # Accept the custom response and continue
                    self.console.print(f"[green]Got it: {raw_answer}[/green]")
                    answers[question.id] = raw_answer
                    answers[f"{question.id}_custom"] = True
            else:
                answer = Prompt.ask(f"[bold]{question.text}[/bold]")
                if self._is_exit_signal(answer):
                    break
                answers[question.id] = answer
        
        return answers
    
    def _smart_match_response(self, response: str, options: List[str], question_id: str) -> Optional[str]:
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
            "maximise": "maximize", "minimise": "minimize", 
            "centre": "center", "colour": "color",
            "grey": "gray", "sulphur": "sulfur",
            "aluminium": "aluminum", "defence": "defense",
            # Temperature variants
            "mid": "mid-range", "middle": "mid-range", "medium": "mid-range",
            "low": "room temperature", "ambient": "room temperature",
            "high": "high temperature", "elevated": "high temperature",
            # Common abbreviations
            "rm temp": "room temperature", "rt": "room temperature",
            "pb free": "no toxic elements", "lead free": "no toxic elements",
            "te free": "no toxic elements", "tellurium free": "no toxic elements",
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
            if ((response_clean in option_lower and len(response_clean) >= 3) or 
                (option_lower in response_clean and len(option_lower) >= 3)):
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
            }
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
            "quit", "exit", "stop", "cancel", "nevermind", "forget it", 
            "skip", "pass", "none", "n/a", "not applicable", "done"
        ]
        
        response_lower = response.strip().lower()
        return any(signal in response_lower for signal in exit_signals)
    
    def _show_smart_auto_configuration(self, assumptions: Dict[str, Any], analysis):
        """Show the smart auto-configuration panel."""
        assumption_lines = "\n".join(
            f"• {key.replace('_', ' ').title()}: {value}" 
            for key, value in assumptions.items() 
            if not key.startswith('_')
        )
        
        self.console.print(Panel(
            f"[bold green]🚀 Smart Auto-Configuration[/bold green]\n\n"
            f"Based on your {analysis.expertise_level}-level query, I'm proceeding with:\n{assumption_lines}\n\n"
            f"→ Using [bold]{self.mode}[/bold] mode for analysis.\n\n"
            f"[dim]If these assumptions are incorrect, you can provide more details in your next message.[/dim]",
            title="[bold cyan]⚡ High-Confidence Analysis[/bold cyan]",
            border_style="cyan"
        ))
    
    def _create_enriched_query(self, original_query: str, context: Dict[str, Any], analysis) -> str:
        """Create an enriched query with full context for the agent."""
        
        # Build context section
        context_lines = []
        for key, value in context.items():
            if not key.startswith('_') and value:
                context_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        context_section = "\n".join(context_lines) if context_lines else "No additional context provided."
        
        # Create enriched query with clear structure
        enriched_query = f"""ORIGINAL USER REQUEST:
{original_query}

CONTEXT AND CONSTRAINTS:
{context_section}

ANALYSIS MODE: {self.mode}
EXPERTISE LEVEL: {analysis.expertise_level if analysis else 'unknown'}

INSTRUCTIONS: This request has been pre-processed and clarified. You can proceed directly with analysis using the comprehensive_materials_analysis tool. All necessary context has been provided above."""
        
        return enriched_query
    
    async def _novice_battery_exploration(self) -> Dict[str, Any]:
        """Friendly battery materials exploration for novices."""
        self.console.print("\n[bold]Battery materials are fascinating! Let me help you explore.[/bold]\n")
        
        self.console.print("🔋 What interests you most about batteries?")
        self.console.print("[dim]A) How they store energy (🔋 energy storage)[/dim]")
        self.console.print("[dim]B) Making them last longer (🔄 cycle life)[/dim]")
        self.console.print("[dim]C) Charging them faster (⚡ fast charging)[/dim]")
        self.console.print("[dim]D) Making them safer (🛡️ safety)[/dim]")
        self.console.print("[dim]Or just tell me what you're curious about![/dim]")
        
        interest = self.console.input("\nWhat interests you? ")
        
        # Map interest to focus area
        focus_map = {
            "a": "energy_storage", "energy": "energy_storage", "store": "energy_storage",
            "b": "cycle_life", "last": "cycle_life", "durability": "cycle_life",
            "c": "fast_charging", "fast": "fast_charging", "quick": "fast_charging",
            "d": "safety", "safe": "safety", "explosion": "safety"
        }
        
        interest_lower = interest.lower()
        focus = "general"
        for key, value in focus_map.items():
            if key in interest_lower:
                focus = value
                break
        
        return {
            "_mode": self.mode,
            "application_area": "Energy storage",
            "focus_area": focus,
            "user_interest": interest,
            "expertise_approach": "educational"
        }
    
    async def _novice_thermoelectric_exploration(self) -> Dict[str, Any]:
        """Friendly thermoelectric exploration for novices."""
        self.console.print("\n[bold]Thermoelectrics turn heat into electricity - pretty cool![/bold]\n")
        
        self.console.print("🌡️ What's your heat source like?")
        self.console.print("[dim]- Body heat or room temperature (🌡️ mild heat)[/dim]")
        self.console.print("[dim]- Car exhaust or industrial waste (🔥 hot heat)[/dim]")
        self.console.print("[dim]- Just exploring the concept (🔍 learning)[/dim]")
        
        heat_source = self.console.input("\nTell me about your heat source: ")
        
        temp_range = "Mid-range (400-700K)"  # Default
        if "body" in heat_source.lower() or "room" in heat_source.lower():
            temp_range = "Room temperature (<400K)"
        elif "exhaust" in heat_source.lower() or "industrial" in heat_source.lower():
            temp_range = "High temperature (>700K)"
        
        return {
            "_mode": self.mode,
            "application_area": "Thermoelectrics",
            "temperature_range": temp_range,
            "heat_source": heat_source,
            "expertise_approach": "educational"
        }
    
    async def _novice_general_exploration(self) -> Dict[str, Any]:
        """General materials exploration for novices."""
        self.console.print("\n[bold]Materials science is huge! Let's find your area of interest.[/bold]\n")
        
        self.console.print("🧪 What kind of problem are you trying to solve?")
        areas = [
            "🔋 Store energy (batteries, capacitors)",
            "🌡️ Convert heat to electricity (thermoelectrics)", 
            "⚡ Make chemical reactions happen (catalysts)",
            "📱 Electronics and computing (semiconductors)",
            "🏠 Strong, lightweight structures (composites)",
            "🔍 Just exploring and learning"
        ]
        
        for i, area in enumerate(areas, 1):
            self.console.print(f"[dim]{i}. {area}[/dim]")
        
        choice = self.console.input("\nWhat interests you most? (number or description): ")
        
        return {
            "_mode": self.mode,
            "exploration_area": choice,
            "expertise_approach": "educational"
        }

    async def _handle_novice_clarification(self, query: str, questions: List[workspace_tools.Question]) -> Dict[str, Any]:
        """Educational, adaptive approach for novice users."""
        self.console.print("\n[cyan]🌱 Let's explore this together![/cyan]")
        
        # Detect domain from query
        query_lower = query.lower()
        if "battery" in query_lower:
            return await self._novice_battery_exploration()
        elif "thermoelectric" in query_lower:
            return await self._novice_thermoelectric_exploration()
        else:
            return await self._novice_general_exploration()
