"""
Integrated Clarification System for Crystalyse

Combines query analysis, expertise detection, and adaptive clarification
into a unified, intelligent interface. This system transforms clarification
from a blocking step into an intelligent discovery process that adapts to
varying user expertise levels.
"""

import json
import logging
import os
import re
from datetime import datetime
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Query analysis logic integrated directly into this class
from ..workspace.workspace_tools import ClarificationRequest, QueryAnalysis, Question
from .dynamic_mode_adapter import DynamicModeAdapter
from .user_preference_memory import UserInteractionRecord, UserPreferenceMemory

logger = logging.getLogger(__name__)


# ----------------------- Pydantic Models -----------------------
class ExpertiseLevel(str, Enum):
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class SuggestedMode(str, Enum):
    CREATIVE = "creative"
    ADAPTIVE = "adaptive"
    RIGOROUS = "rigorous"


class QueryAnalysisResponse(BaseModel):
    expertise_level: ExpertiseLevel
    specificity_score: float
    domain_confidence: float
    technical_terms: list[str]
    should_skip_clarification: bool
    suggested_mode: SuggestedMode
    reasoning: str


class IntegratedClarificationSystem:
    """
    Unified system combining clarification with mode selection.

    Features:
    - Expertise-adaptive clarification (Novice, Intermediate, Expert)
    - Confidence-based triggering of questions
    - Integrated mode selection based on user interaction
    """

    def __init__(
        self,
        console: Console,
        openai_client: AsyncOpenAI | None = None,
        user_id: str = "default",
        current_mode: str | None = None,
    ):
        self.console = console
        self.openai_client = openai_client or AsyncOpenAI()
        self.user_id = user_id
        self.current_mode = current_mode  # Store the explicitly set mode

        # Initialize learning and adaptation systems
        self.preference_memory = UserPreferenceMemory()
        self.mode_adapter = DynamicModeAdapter()

        # Initialize query analysis patterns
        self._init_query_analysis_patterns()

        self.clarification_strategies = {
            "assumption_confirmation": self._confirm_assumptions,
            "guided_discovery": self._guide_discovery,
            "focused_questions": self._focused_questions,
        }

    async def analyze_and_clarify(
        self, query: str, request: ClarificationRequest, current_mode: str | None = None
    ) -> dict[str, Any]:
        """
        Analyzes the query, determines the best clarification strategy, and executes it.
        Includes confidence-based skipping for high-confidence expert queries.

        Args:
            query: The user's initial query.
            request: The clarification request with questions to be answered.

        Returns:
            A dictionary with the clarified answers and mode selection metadata.
        """
        # 1. Analyze the query using LLM-based analysis
        analysis = await self._analyze_query_with_llm(query)

        if analysis is None:
            logger.error("Query analysis failed, cannot proceed with clarification")
            # Return a default response indicating failure
            return {
                "answers": {},
                "mode": "adaptive",
                "confidence": 0.0,
                "strategy": "fallback",
                "error": "Query analysis failed",
            }

        logger.info(
            f"Query analysis: expertise={analysis.expertise_level}, specificity={analysis.specificity_score:.2f}, domain_confidence={analysis.domain_confidence:.2f}"
        )

        # 2. Get personalized strategy based on user history
        personalized_strategy = self.preference_memory.get_personalized_strategy(
            self.user_id, analysis
        )

        logger.info(f"Personalized strategy: {personalized_strategy}")

        # 3. Check if we can skip clarification (considering personalization)
        if await self._should_skip_clarification(analysis, request) or personalized_strategy.get(
            "skip_clarification", False
        ):
            return await self._handle_high_confidence_skip(
                query, request, analysis, personalized_strategy, current_mode
            )

        # 4. Select the best clarification strategy (considering personalization)
        strategy_name = personalized_strategy.get(
            "clarification_method", self._select_clarification_strategy(analysis)
        )

        # Ensure the strategy exists, fallback to focused_questions if not
        if strategy_name not in self.clarification_strategies:
            strategy_name = "focused_questions"

        strategy_func = self.clarification_strategies[strategy_name]

        logger.info(
            f"Selected clarification strategy: {strategy_name} for expertise: {analysis.expertise_level}"
        )

        # 5. Execute the chosen strategy
        start_time = datetime.now()
        clarified_answers = await strategy_func(request, analysis)

        # 6. Determine mode from the full clarification response (considering personalization)
        if "_mode" not in clarified_answers:
            # Respect explicitly set mode first
            if current_mode:
                clarified_answers["_mode"] = current_mode
            else:
                # Use personalized initial mode or determine from responses
                preferred_mode = personalized_strategy.get("initial_mode")
                if preferred_mode:
                    clarified_answers["_mode"] = preferred_mode
                else:
                    clarified_answers["_mode"] = await self._determine_mode_from_responses(
                        clarified_answers, analysis
                    )

        # 7. Record the interaction for learning
        interaction_time = (datetime.now() - start_time).total_seconds()
        self._record_interaction_for_learning(
            query, analysis, strategy_name, clarified_answers, interaction_time
        )

        return clarified_answers

    def _select_clarification_strategy(self, analysis: QueryAnalysisResponse | None) -> str:
        """Choose clarification approach based on user analysis."""
        if analysis is None:
            return "focused_questions"  # Safe default

        if (
            analysis.expertise_level == "expert"
            and analysis.specificity_score > 0.8
            and analysis.domain_confidence > 0.7
        ):
            return "assumption_confirmation"
        elif analysis.expertise_level == "novice":
            return "guided_discovery"
        elif analysis.expertise_level == "intermediate":
            return "focused_questions"
        elif analysis.specificity_score < 0.3:
            # Very low specificity queries default to guided discovery
            return "guided_discovery"
        else:
            return "focused_questions"

    # Expertise-Adaptive Clarification Strategies

    async def _confirm_assumptions(
        self, request: ClarificationRequest, analysis: QueryAnalysisResponse | None
    ) -> dict[str, Any]:
        """Minimal interruption for expert users by confirming smart assumptions."""
        assumptions = await self._generate_smart_assumptions(request.questions, analysis)
        suggested_mode = (
            analysis.suggested_mode.value if analysis and analysis.suggested_mode else "adaptive"
        )

        assumption_lines = "\n".join(
            f"• {q.text}: {assumptions.get(q.id, '[Not specified]')}" for q in request.questions
        )

        self.console.print(
            Panel(
                f"Based on your query, I'm assuming:\n{assumption_lines}"
                f"\n\n→ Proceeding with [bold]{suggested_mode}[/bold] mode for {analysis.expertise_level}-level analysis.",
                title="[bold green]✅ Smart Assumptions[/bold green]",
                border_style="green",
            )
        )

        confirm = Prompt.ask(
            "Proceed with these assumptions?", choices=["yes", "no", "adjust"], default="yes"
        )

        if confirm == "yes":
            return {
                **assumptions,
                "_mode": suggested_mode,
                "_confidence": 0.9,
                "_method": "assumption_confirmation",
                "_user_type": analysis.expertise_level,
            }
        elif confirm == "adjust":
            self.console.print("[yellow]Let's refine the details...[/yellow]")
            return await self._focused_questions(request, analysis)
        else:
            self.console.print("[cyan]Let's start from the beginning to get it right...[/cyan]")
            return await self._guide_discovery(request, analysis)

    async def _guide_discovery(
        self, request: ClarificationRequest, analysis: QueryAnalysisResponse | None
    ) -> dict[str, Any]:
        """Educational, progressive disclosure for novice users."""
        self.console.print(
            Panel(
                "I can help you find the perfect materials! Let's explore your needs step by step.",
                title="[bold cyan]🔎 Discovery Mode[/bold cyan]",
                border_style="cyan",
            )
        )

        approach_preference = Prompt.ask(
            "\n[bold]What's most important to you right now?[/bold]",
            choices=["explore", "validate", "specific"],
            default="explore",
        )

        mode_map = {
            "explore": ("creative", "I'll focus on creative exploration and novel possibilities."),
            "validate": ("rigorous", "I'll prioritise thorough validation and proven approaches."),
            "specific": ("adaptive", "I'll balance exploration with practical validation."),
        }
        mode, explanation = mode_map[approach_preference]
        self.console.print(f"[dim]{explanation}[/dim]\n")

        answers = {
            "_mode": mode,
            "_method": "guided_discovery",
            "_user_type": analysis.expertise_level,
        }

        for question in request.questions:
            self.console.print(f"[bold]{question.text}[/bold]")
            context = self._get_educational_context(question)
            if context:
                self.console.print(f"[dim]{context}[/dim]")

            if question.options:
                simplified_options = self._simplify_options_for_novice(question.options)
                answer = Prompt.ask(
                    "Your choice", choices=simplified_options, default=simplified_options[0]
                )
                answers[question.id] = answer
            else:
                guidance = self._get_input_guidance(question)
                if guidance:
                    self.console.print(f"[dim]Tip: {guidance}[/dim]")
                answer = Prompt.ask("Your answer", default="")
                answers[question.id] = answer

        # Mode emerges from all answers, not just approach preference
        final_mode = await self._determine_mode_from_responses(answers, analysis)
        answers["_mode"] = final_mode

        return answers

    async def _focused_questions(
        self, request: ClarificationRequest, analysis: QueryAnalysisResponse | None
    ) -> dict[str, Any]:
        """Efficient, targeted questions for intermediate users with flexible response handling."""
        self.console.print(
            Panel(
                "I need a few key details to provide the most relevant results.",
                title="[bold yellow]🎯 Quick Clarification[/bold yellow]",
                border_style="yellow",
            )
        )

        likely_answers = self._generate_likely_answers(request.questions, analysis)
        answers = {
            "_mode": "adaptive",
            "_method": "focused_questions",
            "_user_type": analysis.expertise_level,
        }

        for question in request.questions:
            if question.options:
                likely_answer = likely_answers.get(question.id)
                default_answer = (
                    likely_answer if likely_answer in question.options else question.options[0]
                )

                # Show options but don't enforce rigid validation
                options_text = "/".join(question.options)
                prompt_text = f"[bold]{question.text}[/bold] [{options_text}] ({default_answer})"

                raw_answer = Prompt.ask(prompt_text)
                if not raw_answer:  # User pressed enter
                    raw_answer = default_answer

                # Smart response matching
                matched_answer = self._smart_response_matching(
                    raw_answer, question.options, question.id
                )
                if matched_answer:
                    answers[question.id] = matched_answer
                else:
                    # User wants something different - let them guide the conversation
                    self.console.print(f"[yellow]Understood: {raw_answer}[/yellow]")
                    answers[question.id] = raw_answer
                    answers[f"{question.id}_custom"] = True
            else:
                answer = Prompt.ask(
                    f"[bold]{question.text}[/bold]", default=likely_answers.get(question.id, "")
                )
                answers[question.id] = answer

        return answers

    def _smart_response_matching(
        self, response: str, options: list[str], question_id: str
    ) -> str | None:
        """Intelligent response matching with fuzzy logic and context awareness."""
        if not response:
            return None

        response_clean = response.strip().lower()

        # Exit detection
        exit_signals = ["quit", "exit", "stop", "cancel", "nevermind", "forget it", "back", "skip"]
        if any(signal in response_clean for signal in exit_signals):
            return "EXIT_REQUESTED"

        # Direct case-insensitive match
        for option in options:
            if response_clean == option.lower():
                return option

        # Handle common variants
        variants = {
            "maximise": "maximize",
            "minimise": "minimize",
            "centre": "center",
            "colour": "color",
            "grey": "gray",
            "sulphur": "sulfur",
            "aluminium": "aluminum",
            "defence": "defense",
        }

        normalized_response = variants.get(response_clean, response_clean)
        for option in options:
            if normalized_response == option.lower():
                return option

        # Partial matching (smart abbreviations)
        for option in options:
            option_lower = option.lower()
            # Check if response is contained in option or vice versa
            if (response_clean in option_lower and len(response_clean) >= 3) or (
                option_lower in response_clean and len(option_lower) >= 3
            ):
                return option

        # Fuzzy matching for similar concepts
        fuzzy_matches = {
            "battery_type": {
                "fuel cell": None,  # Indicates user wants different domain
                "solar": None,
                "hydrogen": None,
                "li": "Li-ion",
                "lithium": "Li-ion",
                "sodium": "Na-ion",
                "na": "Na-ion",
                "magnesium": "Mg-ion",
                "mg": "Mg-ion",
                "zinc": "Zn-ion",
                "zn": "Zn-ion",
                "solid": "Solid-state",
            },
            "electrode": {
                "fuel cell": None,
                "positive": "Cathode",
                "negative": "Anode",
                "separator": "Separator",
                "electrolyte": "Electrolyte",
            },
            "key_property": {
                "life": "Long cycle life",
                "cycle": "Long cycle life",
                "fast": "Fast charging",
                "quick": "Fast charging",
                "speed": "Fast charging",
                "density": "High energy density",
                "energy": "High energy density",
                "cheap": "Low cost",
                "cost": "Low cost",
                "safe": "High safety",
                "safety": "High safety",
            },
        }

        if question_id in fuzzy_matches:
            for keyword, mapped_option in fuzzy_matches[question_id].items():
                if keyword in response_clean:
                    return mapped_option  # Could be None for domain mismatch

        # If no match found, let the user guide us
        return None

    # Query Analysis Methods

    async def _call_llm_for_query_analysis(self, query: str) -> QueryAnalysisResponse | None:
        """
        Uses the Responses API with native Pydantic integration for guaranteed structured output.
        This eliminates JSON parsing errors by using OpenAI's structured outputs feature.
        """
        # Create dedicated client for reasoning
        mdg_api_key = os.getenv("OPENAI_MDG_API_KEY")
        if mdg_api_key:
            client = AsyncOpenAI(api_key=mdg_api_key)
        else:
            client = self.openai_client

        system_instruction = """You are an expert in materials science query analysis.
Analyze user queries to determine expertise level, specificity, and whether clarification is needed.

**Skip Clarification Rules (expertise-aware):**
- EXPERT query (specificity ≥ 0.7) → should_skip_clarification=true
- INTERMEDIATE query (specificity 0.4-0.7) with clear direction → should_skip_clarification=true
- NOVICE query (specificity < 0.4) → should_skip_clarification=false (educational questions provide value)

Expert Level Indicators:
- "expert": Query contains 2+ of the following: specific material names (e.g. "Na-ion", "LiFePO4"),
  quantitative targets (e.g. "gravimetric capacity", "cell voltage", "ZT>1.5"), performance metrics,
  material properties (e.g. "isotropy", "crystal anisotropy"), processing methods (e.g. "sintering"),
  material classes (e.g. "Zintl phases"), specific constraints (e.g. "earth-abundant", "lead-free")
- "intermediate": Query contains 1-2 technical terms like "battery cathode", "thermal conductivity",
  "semiconductor", or mentions specific applications without detailed constraints
- "novice": General requests like "battery materials", "find materials", "suggest", vague descriptions without technical terminology

Specificity Guidelines:
- High (0.7-1.0): Specific materials mentioned (Na-ion, cathode), quantitative targets (capacity, voltage),
  multiple property specifications, clear application context
- Medium (0.4-0.6): Some constraints mentioned, application specified but lacks quantitative targets
- Low (0.0-0.3): Vague requests ("suggest", "find"), no specific constraints or targets

For NOVICE queries, clarification provides educational value even if query is technically executable.

Domain Confidence:
- High (0.7-1.0): Deep materials science terminology, proper use of technical concepts
- Medium (0.4-0.6): Some materials context, basic technical terms used correctly
- Low (0.0-0.3): General or unclear domain, misuse of technical terms"""

        user_prompt = f'Analyze this materials science query: "{query}"'

        try:
            # Use responses.parse with native Pydantic integration for guaranteed structured output
            response = await client.responses.parse(
                model="gpt-4o-mini",  # Use gpt-4o-mini for structured outputs compatibility
                input=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=QueryAnalysisResponse,
                max_output_tokens=600,
            )

            # Extract the parsed Pydantic object directly
            return response.output_parsed

        except Exception as e:
            logger.warning(f"LLM query analysis failed: {e}")
            return None

    async def _analyze_query_with_llm(self, query: str) -> QueryAnalysisResponse | None:
        """
        Use LLM-based analysis instead of hardcoded patterns.

        This leverages the LLM's comprehensive materials science knowledge
        to accurately detect expertise level and specificity.
        """
        try:
            # Call LLM with structured validation
            llm_analysis = await self._call_llm_for_query_analysis(query)

            if llm_analysis is None:
                logger.warning("LLM analysis failed, no fallback available")
                return None

            logger.info(
                f"LLM analysis successful: {llm_analysis.expertise_level}, specificity={llm_analysis.specificity_score:.2f}"
            )

            # Store LLM recommendations for decision making
            self._llm_skip_recommendation = llm_analysis.should_skip_clarification
            self._llm_suggested_mode = llm_analysis.suggested_mode.value

            # Return the LLM analysis directly (no conversion needed)
            return llm_analysis

        except Exception as e:
            logger.warning(f"LLM query analysis failed: {e}")
            return None

    def _init_query_analysis_patterns(self):
        """Initialize patterns for query analysis."""
        self.expertise_patterns = {
            "expert": [
                r"formation energy",
                r"phonon",
                r"dft",
                r"vasp",
                r"synthesis route",
                r"oxidation state",
                r"space group",
                r"lattice parameter",
                r"band gap",
                r"dos",
                r"bandstructure",
                r"thermodynamic",
                r"kinetic",
                r"crystallographic",
                # Thermoelectric terms
                r"thermoelectric",
                r"zt",
                r"seebeck",
                r"thermal conductivity",
                r"electrical conductivity",
                r"power factor",
                r"figure of merit",
                r"carrier concentration",
                r"mobility",
                # Crystal structure terms
                r"anisotrop",
                r"isotrop",
                r"crystal.*anisotrop",
                r"structural.*isotrop",
                r"polycrystalline",
                r"single.*crystal",
                r"grain.*boundar",
                # Processing terms
                r"sintering",
                r"hot.*press",
                r"densif",
                r"consolidat",
                r"bulk.*process",
                r"powder.*process",
                r"ceramic.*process",
                # Material classes
                r"zintl",
                r"skutterud",
                r"half.*heusler",
                r"chalcogenide",
                r"oxide.*thermoelectric",
                r"clathrate",
                r"perovskite",
                r"layered.*material",
                # Properties and characterization
                r"hall.*effect",
                r"resistivity",
                r"thermal.*diffusivity",
                r"specific.*heat",
                r"phonon.*scattering",
                r"electron.*transport",
                r"dopant",
                r"substitution",
                # Advanced concepts
                r"nanostructur",
                r"quantum.*well",
                r"superlattice",
                r"interfacial.*resist",
                r"phonon.*engineer",
                r"band.*engineer",
                r"defect.*engineer",
                # Battery-specific expert terms
                r"spinel.*struct",
                r"olivine.*struct",
                r"layered.*oxide",
                r"theoretical.*capacity",
                r"operating.*voltage",
                r"vs.*mg",
                r"vs.*li",
                r"electrolyte.*compat",
                r"carbonate.*electrolyte",
                r"mah/g",
                r"wh/kg",
                r"c-rate",
                r"coulombic.*efficiency",
                r"capacity.*retention",
                r"voltage.*fade",
                r"impedance.*growth",
                r"side.*reaction",
                r"sei.*formation",
                # Advanced characterization
                r"xrd.*pattern",
                r"xps.*spectr",
                r"sem.*morphol",
                r"tem.*analys",
                r"nmr.*spectr",
                r"electrochemical.*impedance",
                r"cyclic.*voltamm",
                r"galvanostatic",
                r"potentiostatic",
            ],
            "intermediate": [
                r"structure.*prediction",
                r"stability",
                r"composition",
                r"crystal.*system",
                r"properties",
                r"synthesis",
                r"fabrication",
                r"characterization",
                # Battery intermediate terms
                r"cathode.*material",
                r"anode.*material",
                r"electrolyte",
                r"separator",
                r"li.*ion",
                r"na.*ion",
                r"mg.*ion",
                r"capacity",
                r"voltage",
                r"energy.*density",
                r"cycle.*life",
                r"charging",
                r"discharge",
                r"battery.*type",
                r"cell.*design",
                # Materials intermediate terms
                r"crystal.*structure",
                r"lattice.*parameter",
                r"phase.*transition",
                r"dopant",
                r"substitution",
                r"solid.*solution",
                r"composite",
                r"coating",
                r"surface.*modif",
            ],
            "novice": [
                r"^what.*material",
                r"^find.*material",
                r"^suggest",
                r"^recommend",
                r"^help.*choose",
                r"beginner",
                r"^i.*need.*help",
                r"^can.*you.*help",
                r"^simple.*material",
                r"^basic.*material",
                r"^easy.*to.*make",
                r"^cheap.*material",
                r"^common.*material",
            ],
        }

        self.urgency_patterns = [
            r"quick",
            r"fast",
            r"urgent",
            r"asap",
            r"deadline",
            r"immediately",
            r"need.*soon",
            r"time.*sensitive",
            r"rushing",
            r"hurry",
        ]

        self.complexity_indicators = {
            "safety_critical": [
                r"create.*toxic",
                r"synthesize.*explosive",
                r"nuclear.*material",
                r"radioactive",
                r"highly.*toxic",
                r"dangerous.*synthesis",
            ],
            "novel_chemistry": [r"new.*element", r"unusual.*oxidation", r"unexplored", r"novel"],
            "synthesis_focused": [r"synthesize", r"make", r"prepare", r"fabricate", r"process"],
            "publication_grade": [r"paper", r"publish", r"journal", r"research", r"manuscript"],
            "comparative": [r"compare", r"versus", r"better.*than", r"alternatives"],
            "exploratory": [r"explore", r"discover", r"find", r"what.*if", r"possibilities"],
        }

    def _analyze_query(self, query: str) -> QueryAnalysis:
        """Comprehensive analysis of user query to determine optimal approach."""
        query_lower = query.lower()

        # Detect expertise level
        expertise_level = self._detect_expertise_level(query_lower)

        # Measure specificity
        specificity_score = self._calculate_specificity(query)

        # Check urgency
        urgency_indicators = [
            pattern for pattern in self.urgency_patterns if re.search(pattern, query_lower)
        ]

        # Analyze complexity
        complexity_factors = {}
        for factor, patterns in self.complexity_indicators.items():
            complexity_factors[factor] = any(
                re.search(pattern, query_lower) for pattern in patterns
            )

        # Assess domain confidence
        domain_confidence = self._assess_domain_confidence(query_lower)

        # Determine interaction style
        interaction_style = self._classify_interaction_style(query_lower, complexity_factors)

        return QueryAnalysis(
            expertise_level=expertise_level,
            specificity_score=specificity_score,
            urgency_indicators=urgency_indicators,
            complexity_factors=complexity_factors,
            domain_confidence=domain_confidence,
            interaction_style=interaction_style,
        )

    def _detect_expertise_level(self, query_lower: str) -> str:
        """Detect user expertise level from language patterns."""

        expert_score = sum(
            1 for pattern in self.expertise_patterns["expert"] if re.search(pattern, query_lower)
        )
        intermediate_score = sum(
            1
            for pattern in self.expertise_patterns["intermediate"]
            if re.search(pattern, query_lower)
        )

        if expert_score >= 2:
            return "expert"
        elif intermediate_score >= 1:
            return "intermediate"
        else:
            return "novice"

    def _calculate_specificity(self, query: str) -> float:
        """Calculate how specific vs general the query is."""

        # Specific indicators
        specific_patterns = [
            r"[A-Z][a-z]?[0-9]",  # Chemical formulas like SnSe, LiFePO4
            r"\d+\.\d+",  # Numerical values like 0.8, 1.5
            r"\d+–\d+|(\d+)\s*-\s*(\d+)",  # Temperature ranges like 500–800
            r"eV|GPa|K|°C|mV|μV|S/cm|W/mK",  # Scientific units
            r"exactly|precisely|specific|targeting|requiring",  # Specificity language
            r">\s*\d+|<\s*\d+|≥\s*\d+|≤\s*\d+",  # Comparison operators like >1.5
            r"high-performance|state-of-the-art|cutting-edge",  # Performance descriptors
            r"compared?\s+to|better\s+than|versus|vs\.?",  # Comparative language
            r"operating\s+(at|in|under)|conditions?",  # Operating conditions
            r"avoid(ing)?|exclude|prohibit|constraint",  # Specific constraints
            r"compatible\s+with|suitable\s+for",  # Compatibility requirements
            r"preferr?(ed)?|interest\s+in|focus\s+on",  # Specific preferences
        ]

        # General indicators
        general_patterns = [
            r"what|how|why|which",  # Question words
            r"any|some|better|good",  # Vague qualifiers
            r"suggest|recommend|find",  # Request language
        ]

        specific_count = sum(1 for pattern in specific_patterns if re.search(pattern, query))
        general_count = sum(1 for pattern in general_patterns if re.search(pattern, query.lower()))

        total_words = len(query.split())
        specificity = (specific_count * 2 - general_count) / max(total_words / 10, 1)

        return max(0.0, min(1.0, specificity))

    def _assess_domain_confidence(self, query_lower: str) -> float:
        """Assess how clearly materials science focused the query is."""
        materials_terms = [
            "material",
            "crystal",
            "structure",
            "element",
            "compound",
            "synthesis",
            "properties",
            "electronic",
            "thermal",
            "mechanical",
            "stability",
            "formation",
            "energy",
            "bandgap",
            "conductivity",
            "thermoelectric",
            # Thermoelectric specific terms
            "zt",
            "seebeck",
            "power factor",
            "figure of merit",
            "thermal conductivity",
            "electrical conductivity",
            "carrier",
            "mobility",
            "doping",
            # Crystal/structure terms
            "isotrop",
            "anisotrop",
            "polycrystalline",
            "sintering",
            "processing",
            "fabrication",
            "bulk",
            "grain",
            "phase",
            "lattice",
            # Performance terms
            "performance",
            "efficient",
            "optimize",
            "enhance",
            "improve",
            # Materials classes
            "oxide",
            "chalcogenide",
            "alloy",
            "ceramic",
            "semiconductor",
            # Chemical elements and formulas (broad patterns)
            "pb",
            "te",
            "se",
            "sn",
            "lead",
            "tellurium",
            "selenium",
            "tin",
        ]

        matches = sum(1 for term in materials_terms if term in query_lower)
        # More generous scoring - 3+ terms = high confidence
        return min(1.0, matches / 3.0)  # Normalize to 0-1

    def _classify_interaction_style(
        self, query_lower: str, complexity_factors: dict[str, bool]
    ) -> str:
        """Classify the type of interaction the user wants."""
        if complexity_factors.get("exploratory"):
            return "exploratory"
        elif complexity_factors.get("synthesis_focused"):
            return "synthesis"
        elif any(word in query_lower for word in ["validate", "confirm", "check", "verify"]):
            return "validation"
        else:
            return "exploratory"  # Default

    async def _determine_mode_from_responses(
        self, answers: dict[str, Any], analysis: QueryAnalysisResponse | None
    ) -> str:
        """Analyzes all clarification responses to determine the optimal execution mode."""

        # Extract non-metadata answers
        actual_answers = {k: v for k, v in answers.items() if not k.startswith("_")}

        # Signals from answers that indicate mode preference
        rigorous_signals = 0
        creative_signals = 0

        # Analyze answer patterns
        answers_text = " ".join(str(v) for v in actual_answers.values()).lower()

        # Rigorous mode indicators
        rigorous_keywords = [
            "validate",
            "verify",
            "thorough",
            "accurate",
            "precise",
            "publication",
            "research",
            "rigorous",
            "comprehensive",
        ]
        rigorous_signals += sum(1 for kw in rigorous_keywords if kw in answers_text)

        # Creative mode indicators
        creative_keywords = [
            "explore",
            "discover",
            "quick",
            "fast",
            "novel",
            "innovative",
            "alternatives",
            "possibilities",
        ]
        creative_signals += sum(1 for kw in creative_keywords if kw in answers_text)

        # Factor in the initial analysis
        if analysis and analysis.suggested_mode == "creative":
            creative_signals += 2  # LLM suggests creative mode

        if analysis and analysis.suggested_mode == "rigorous":
            rigorous_signals += 3  # LLM suggests rigorous mode

        if analysis and analysis.expertise_level == "expert" and analysis.specificity_score > 0.8:
            rigorous_signals += 1  # Experts with specific queries often want validation

        # Determine final mode
        if rigorous_signals > creative_signals + 1:
            return "rigorous"
        elif creative_signals > rigorous_signals + 1:
            return "creative"
        else:
            return "adaptive"  # Balanced approach

    # Confidence-Based Clarification Management

    async def _should_skip_clarification(
        self, analysis: QueryAnalysisResponse | None, request: ClarificationRequest
    ) -> bool:
        """
        Determine if clarification can be skipped based on query confidence.
        Uses aggressive skip logic - defaults to skipping unless truly necessary.

        Args:
            analysis: Query analysis results
            request: Clarification request

        Returns:
            True if clarification should be skipped
        """
        # Handle null analysis case
        if analysis is None:
            logger.info("No analysis available - requiring clarification")
            return False

        # Aggressive skip logic for expert queries
        if analysis.expertise_level == "expert" and analysis.specificity_score >= 0.7:
            logger.info(
                f"Skipping clarification: expert query with {analysis.specificity_score:.1%} specificity"
            )
            return True

        # Use LLM's recommendation directly from the structured response
        if analysis.should_skip_clarification:
            logger.info("LLM recommends skipping clarification")
            return True

        # Check for high domain confidence + reasonable specificity
        if analysis.domain_confidence >= 0.7 and analysis.specificity_score >= 0.6:
            logger.info(
                f"Skipping clarification: high domain confidence ({analysis.domain_confidence:.1%}) and specificity ({analysis.specificity_score:.1%})"
            )
            return True

        logger.info(
            f"Requiring clarification: expertise={analysis.expertise_level}, specificity={analysis.specificity_score:.1%}, domain_confidence={analysis.domain_confidence:.1%}"
        )
        return False

    async def _handle_high_confidence_skip(
        self,
        query: str,
        request: ClarificationRequest,
        analysis: QueryAnalysisResponse | None,
        personalized_strategy: dict[str, Any] | None = None,
        current_mode: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle high-confidence queries that skip the clarification process.

        Shows smart assumptions without blocking for user confirmation.
        """
        # Generate assumptions without asking
        assumptions = await self._generate_smart_assumptions(request.questions, analysis)

        # Respect explicitly set mode first
        if current_mode:
            suggested_mode = current_mode
        elif personalized_strategy and personalized_strategy.get("initial_mode"):
            suggested_mode = personalized_strategy["initial_mode"]
        else:
            suggested_mode = self._suggest_initial_mode(analysis)

        # Show assumptions as information, not for confirmation
        assumption_lines = "\n".join(
            f"• {q.text}: {assumptions.get(q.id, '[Auto-detected]')}" for q in request.questions
        )

        self.console.print(
            Panel(
                f"[bold green]🚀 High-Confidence Analysis[/bold green]\n\n"
                f"Based on your expert-level query, I'm proceeding with:\n{assumption_lines}\n\n"
                f"→ Using [bold]{suggested_mode}[/bold] mode with {analysis.expertise_level}-level analysis.\n\n"
                f"[dim]If these assumptions are incorrect, you can adjust them in your next message.[/dim]",
                title="[bold cyan]⚡ Smart Auto-Configuration[/bold cyan]",
                border_style="cyan",
            )
        )

        return {
            **assumptions,
            "_mode": suggested_mode,
            "_confidence": 0.95,
            "_method": "high_confidence_skip",
            "_user_type": analysis.expertise_level,
            "_skip_reason": f"Expert query with {analysis.specificity_score:.1%} specificity",
        }

    def _suggest_initial_mode(self, analysis: QueryAnalysisResponse | None) -> str:
        """
        Suggest initial mode based on query analysis.

        Args:
            analysis: Query analysis results

        Returns:
            Suggested execution mode
        """
        # Use LLM's mode suggestion directly from the analysis
        if analysis and analysis.suggested_mode:
            logger.info(f"Using LLM suggested mode: {analysis.suggested_mode}")
            return analysis.suggested_mode.value

        # Fallback if no analysis available
        logger.info("No analysis available - defaulting to adaptive mode")
        return "adaptive"

    def _record_interaction_for_learning(
        self,
        query: str,
        analysis: QueryAnalysisResponse | None,
        clarification_method: str,
        result: dict[str, Any],
        interaction_time: float,
    ):
        """Record interaction for cross-session learning."""
        try:
            # Extract domain from the query (simplified)
            domain_area = "general"
            if "thermoelectric" in query.lower():
                domain_area = "thermoelectrics"
            elif "battery" in query.lower():
                domain_area = "batteries"
            elif "catalyst" in query.lower():
                domain_area = "catalysis"
            elif "solar" in query.lower() or "photovoltaic" in query.lower():
                domain_area = "photovoltaics"

            # Create interaction record
            interaction = UserInteractionRecord(
                timestamp=datetime.now(),
                query=query,
                expertise_detected=analysis.expertise_level,
                specificity_score=analysis.specificity_score,
                clarification_method=clarification_method,
                chosen_mode=result.get("_mode", "adaptive"),
                adaptations_made=[],  # Will be updated by feedback
                completion_time_seconds=interaction_time,
                user_satisfaction=0.7,  # Default, updated by feedback
                domain_area=domain_area,
            )

            # Record the interaction
            self.preference_memory.learn_from_interaction(self.user_id, interaction)

            logger.debug(
                f"Recorded interaction for learning: {clarification_method} -> {result.get('_mode')}"
            )

        except Exception as e:
            logger.warning(f"Failed to record interaction for learning: {e}")

    def record_user_feedback(self, feedback: str, satisfaction_score: float | None = None):
        """Record user feedback to improve future interactions."""
        try:
            # If satisfaction not provided, infer from feedback
            if satisfaction_score is None:
                feedback_lower = feedback.lower()
                if any(
                    word in feedback_lower for word in ["great", "perfect", "excellent", "good"]
                ):
                    satisfaction_score = 0.9
                elif any(
                    word in feedback_lower for word in ["wrong", "bad", "terrible", "useless"]
                ):
                    satisfaction_score = 0.2
                elif any(word in feedback_lower for word in ["ok", "fine", "decent"]):
                    satisfaction_score = 0.6
                else:
                    satisfaction_score = 0.5

            # Update the satisfaction score
            self.preference_memory.record_user_satisfaction(self.user_id, satisfaction_score)

            # Check for adaptation patterns in feedback
            if "too slow" in feedback.lower() or "faster" in feedback.lower():
                # Update speed preference
                profile = self.preference_memory.get_or_create_profile(self.user_id)
                profile.speed_preference = min(1.0, profile.speed_preference + 0.1)

            logger.debug(f"Recorded user feedback: satisfaction={satisfaction_score:.2f}")

        except Exception as e:
            logger.warning(f"Failed to record user feedback: {e}")

    def get_user_statistics(self) -> dict[str, Any]:
        """Get user learning statistics for debugging/analysis."""
        return self.preference_memory.get_user_statistics(self.user_id)

    # Helper methods for content generation

    async def _generate_smart_assumptions(
        self, questions: list[Question], analysis: QueryAnalysisResponse | None
    ) -> dict[str, Any]:
        """Uses LLM to generate context-aware assumptions based on query analysis."""

        # Create dedicated o3-mini client for reasoning
        mdg_api_key = os.getenv("OPENAI_MDG_API_KEY")
        if mdg_api_key:
            o3_mini_client = AsyncOpenAI(api_key=mdg_api_key)
        else:
            o3_mini_client = self.openai_client

        # Prepare the context for assumption generation
        if analysis:
            context = f"""
        Query Analysis:
        - Expertise Level: {analysis.expertise_level}
        - Specificity Score: {analysis.specificity_score:.2f}
        - Domain Confidence: {analysis.domain_confidence:.2f}
        - Technical Terms: {", ".join(analysis.technical_terms) if analysis.technical_terms else "None"}
        - Suggested Mode: {analysis.suggested_mode}
        - Skip Recommendation: {analysis.should_skip_clarification}
        """
        else:
            context = """
        Query Analysis:
        - No detailed analysis available
        - Using fallback assumptions
        """

        questions_json = [{"id": q.id, "text": q.text, "options": q.options} for q in questions]

        try:
            response = await o3_mini_client.chat.completions.create(
                model="o4-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a materials science expert helping to generate smart assumptions for clarification questions.
                    Based on the query analysis context, generate reasonable default answers that an expert user would likely choose.
                    Focus on scientifically sound, common choices for materials research.
                    Return ONLY a JSON object mapping question IDs to assumed answers.""",
                    },
                    {
                        "role": "user",
                        "content": f"""
                    {context}

                    Questions to generate assumptions for:
                    {json.dumps(questions_json, indent=2)}

                    Generate smart assumptions that match the expertise level and context.
                    For example:
                    - If synthesis_focused, assume practical constraints
                    - If publication_grade, assume rigorous requirements
                    - If exploratory, assume broader ranges
                    """,
                    },
                ],
                temperature=0.3,  # Lower temperature for consistent assumptions
                max_completion_tokens=500,
            )

            assumptions_text = response.choices[0].message.content.strip()

            # Extract JSON
            if "```json" in assumptions_text:
                json_start = assumptions_text.find("```json") + 7
                json_end = assumptions_text.find("```", json_start)
                assumptions_text = assumptions_text[json_start:json_end].strip()

            assumptions = json.loads(assumptions_text)
            logger.info(f"Generated smart assumptions: {assumptions}")
            return assumptions

        except Exception as e:
            logger.warning(f"Failed to generate smart assumptions via LLM: {e}")
            # Fallback to rule-based assumptions
            return self._generate_fallback_assumptions(questions, analysis)

    def _generate_fallback_assumptions(
        self, questions: list[Question], analysis: QueryAnalysisResponse | None
    ) -> dict[str, Any]:
        """Rule-based fallback for assumption generation."""
        assumptions = {}

        for q in questions:
            q_id_lower = q.id.lower()

            # Temperature-related assumptions
            if "temperature" in q_id_lower:
                if analysis and "sintering" in analysis.technical_terms:
                    assumptions[q.id] = "Mid (500–800K)"  # Practical synthesis range
                elif analysis and analysis.expertise_level == "expert":
                    assumptions[q.id] = "High (>800K)"  # Expert often works with high-temp
                else:
                    assumptions[q.id] = "Room temperature"  # Safe default

            # Constraint assumptions
            elif "constraint" in q_id_lower or "toxicity" in q_id_lower:
                if analysis and any(
                    "lead" in term.lower() or "tellurium" in term.lower()
                    for term in analysis.technical_terms
                ):
                    assumptions[q.id] = "Lead-free / Tellurium-free"  # Safety first
                else:
                    assumptions[q.id] = "Earth-abundant"  # Common preference

            # Fabrication assumptions
            elif "fabrication" in q_id_lower or "form" in q_id_lower:
                if analysis and any(
                    "sintering" in term.lower() or "polycrystalline" in term.lower()
                    for term in analysis.technical_terms
                ):
                    assumptions[q.id] = "Bulk polycrystalline"  # Most common
                else:
                    assumptions[q.id] = "No preference"

            # Material class assumptions
            elif "material" in q_id_lower and "class" in q_id_lower:
                if analysis and any(
                    "thermoelectric" in term.lower() for term in analysis.technical_terms
                ):
                    assumptions[q.id] = "Zintl phases"  # Good for thermoelectrics
                else:
                    assumptions[q.id] = "No preference"

            # Default for options
            elif q.options:
                assumptions[q.id] = q.options[0]  # First option as default
            else:
                assumptions[q.id] = ""  # Empty for free text

        return assumptions

    def _get_educational_context(self, question: Question) -> str:
        """Provides helpful context for a question for novice users."""
        # Educational contexts for common question types
        contexts = {
            # Temperature-related questions
            "operating_temperature": "Materials behave differently at different temperatures. High temperatures (>800K) are often needed for catalysis and some energy applications, while room temperature applications are easier to work with.",
            "target_temperature": "Consider your application: room temperature for electronics/sensors, mid-range (500-800K) for thermoelectrics, high temperature (>800K) for catalysis and high-temperature energy storage.",
            "temperature_range": "Temperature affects material stability, performance, and synthesis routes. Choose based on your intended application conditions.",
            # Constraint-related questions
            "elemental_constraints": "Some elements like lead (Pb) and tellurium (Te) are toxic or rare. Earth-abundant elements (Fe, Al, Si, etc.) are cheaper and more sustainable.",
            "toxicity_constraints": "Lead and mercury are highly toxic. Tellurium and selenium are rare and expensive. Consider environmental and health impacts.",
            "cost_constraints": "Precious metals (Pt, Au, Pd) and rare earths (Nd, Dy) are expensive. Earth-abundant elements keep costs down.",
            # Fabrication questions
            "fabrication_method": "Bulk polycrystalline materials are easiest to make and most common. Thin films require special equipment but enable device integration. Nanostructured materials offer unique properties but are harder to synthesize.",
            "processing_route": "Solid-state synthesis is most common but requires high temperatures. Solution methods work at lower temperatures but may limit material choice.",
            "form_factor": "The physical form affects both properties and applications. Powders are versatile, bulk materials are mechanically robust, thin films enable electronics integration.",
            # Material class questions
            "material_class": "Different families have distinct properties: Oxides are stable in air, Zintl phases have interesting electronic properties, Half-Heuslers are good thermoelectrics, Perovskites are versatile for many applications.",
            "structure_type": "Crystal structure determines many properties. Layered structures often have anisotropic properties, cubic structures are more isotropic.",
            # Property questions
            "target_property": "This is the main performance metric you want to optimize. Be specific: electrical conductivity, thermal conductivity, figure of merit (ZT), energy density, etc.",
            "property_range": "Realistic property ranges help focus the search. Check literature values for similar materials as a starting point.",
            # Application questions
            "application_area": "The intended use determines property requirements: batteries need high capacity and stability, thermoelectrics need high ZT, catalysts need activity and selectivity.",
            "performance_target": "Specific performance targets help evaluate success. What improvement over current materials would be meaningful?",
        }

        # Try to match question ID or text to contexts
        q_id_lower = question.id.lower()
        q_text_lower = question.text.lower()

        # Direct ID match
        if q_id_lower in contexts:
            return contexts[q_id_lower]

        # Keyword matching in question text
        for context_key, context_text in contexts.items():
            key_words = context_key.split("_")
            if any(word in q_text_lower for word in key_words):
                return context_text

        # Fallback context
        if "temperature" in q_text_lower:
            return "Temperature is a key factor affecting material stability, synthesis, and performance."
        elif "constraint" in q_text_lower or "element" in q_text_lower:
            return "Consider environmental, cost, and availability constraints when selecting elements."
        elif "fabrication" in q_text_lower or "process" in q_text_lower:
            return "The synthesis method affects material quality, scalability, and cost."
        elif "material" in q_text_lower and "class" in q_text_lower:
            return "Different material families have characteristic properties and applications."

        return ""  # No specific context available

    def _simplify_options_for_novice(self, options: list[str]) -> list[str]:
        """Simplifies technical options for novice users."""
        # Mapping of technical terms to more accessible language
        simplifications = {
            # Temperature options
            "Low (<500K)": "Room temperature (easier to work with)",
            "Mid (500–800K)": "Medium temperature (common for energy applications)",
            "High (>800K)": "High temperature (challenging but powerful)",
            # Constraints
            "Lead-free": "No toxic lead",
            "Tellurium-free": "No rare tellurium",
            "Earth-abundant only": "Common, cheap elements only",
            "No constraints": "Any elements are fine",
            # Fabrication methods
            "Bulk polycrystalline": "Standard solid material (most common)",
            "Thin film": "Ultra-thin coating (for electronics)",
            "Nanostructured": "Nano-scale particles (advanced)",
            "No preference": "Any form is fine",
            # Material classes
            "Half-Heuslers": "Half-Heusler alloys (good for thermoelectrics)",
            "Skutterudites": "Cage-like structures (thermoelectric materials)",
            "Zintl phases": "Complex ionic compounds (interesting electronics)",
            "Oxides": "Oxygen-containing compounds (stable in air)",
            "Tellurides": "Tellurium compounds (high performance but rare)",
            "Perovskites": "Versatile cubic structure (many applications)",
            # Properties
            "High ZT": "High thermoelectric performance",
            "Low thermal conductivity": "Poor heat conduction (good for thermoelectrics)",
            "High electrical conductivity": "Good electrical conduction",
            "High energy density": "Stores lots of energy per weight",
            # General terms
            "Isotropic": "Same properties in all directions",
            "Anisotropic": "Different properties along different directions",
            "Metastable": "Stable but not the most stable form",
            "Thermodynamically stable": "Most stable form under conditions",
        }

        simplified = []
        for option in options:
            if option in simplifications:
                # Show both simplified and original
                simplified.append(f"{simplifications[option]} [{option}]")
            else:
                simplified.append(option)

        return simplified

    def _get_input_guidance(self, question: Question) -> str:
        """Provides guidance for free-text input for novice users."""
        # Detailed guidance for different types of free-text questions
        guidance_map = {
            # Element-related
            "elements_to_include": "List chemical symbols separated by commas, e.g., 'Li, Co, O' for lithium cobalt oxide, or 'Si, Ge' for silicon-germanium alloys.",
            "elements_to_exclude": "List elements to avoid, e.g., 'Pb, Hg' to avoid toxic elements, or 'Pt, Au' to avoid expensive precious metals.",
            "preferred_elements": "Focus on specific elements you want, e.g., 'Fe, Ni' for magnetic materials or 'Na, K' for alkali-based compounds.",
            # Composition-related
            "target_composition": "Describe the desired chemical formula, e.g., 'LiCoO2' for a specific compound or 'transition metal oxide' for a class.",
            "stoichiometry": "Specify element ratios, e.g., '1:1:3' for ABC3 compounds or 'equal amounts of A and B'.",
            # Property-related
            "target_properties": "Describe desired properties in plain language, e.g., 'high electrical conductivity and stable in air' or 'converts heat to electricity efficiently'.",
            "property_values": "Give specific numbers if known, e.g., 'conductivity > 1000 S/cm' or 'bandgap around 1.5 eV', or describe relatively like 'higher than silicon'.",
            "performance_requirements": "Describe what you need the material to do, e.g., 'store energy for 8 hours' or 'work at 600°C without degrading'.",
            # Application-related
            "intended_application": "Describe the use case, e.g., 'solar cell absorber', 'battery cathode', 'catalyst for CO2 reduction', 'thermoelectric generator'.",
            "operating_conditions": "Describe the environment, e.g., 'high temperature and corrosive', 'underwater', 'in space', 'room temperature and humid'.",
            # Synthesis-related
            "synthesis_constraints": "Describe limitations, e.g., 'low temperature processing', 'solution-based methods only', 'scalable to industrial production'.",
            "processing_requirements": "Specify needs, e.g., 'can be made as thin films', 'compatible with silicon processing', 'stable during sintering'.",
            # Structure-related
            "crystal_structure": "Describe structural preferences, e.g., 'layered like graphite', 'cubic structure', 'one-dimensional chains', 'porous framework'.",
            "morphology": "Specify physical form, e.g., 'nanoparticles', 'single crystals', 'porous membrane', 'flexible film'.",
            # General research
            "research_goals": "Describe your objectives, e.g., 'improve upon current lithium-ion batteries', 'find lead-free alternative to PbTe', 'discover new superconductor'.",
            "novelty_level": "Specify innovation desired, e.g., 'known materials with proven properties', 'recent literature compounds', 'completely new predictions'.",
        }

        # Try to match question ID
        q_id_lower = question.id.lower()
        if q_id_lower in guidance_map:
            return guidance_map[q_id_lower]

        # Keyword matching in question text
        q_text_lower = question.text.lower()

        # Check for element-related questions
        if any(word in q_text_lower for word in ["element", "composition", "chemical"]):
            return "List chemical elements using their symbols (e.g., 'Li, Fe, O') or describe the type of chemistry (e.g., 'transition metal oxides')."

        # Check for property questions
        elif any(word in q_text_lower for word in ["property", "performance", "value"]):
            return "Describe the properties you need, either with numbers if known (e.g., 'conductivity > 100 S/cm') or relatively (e.g., 'better than silicon')."

        # Check for application questions
        elif any(word in q_text_lower for word in ["application", "use", "purpose"]):
            return "Describe what you want to use the material for, e.g., 'solar cells', 'battery electrodes', 'catalysis', 'sensors'."

        # Check for synthesis questions
        elif any(word in q_text_lower for word in ["synthesis", "processing", "fabrication"]):
            return "Describe your synthesis capabilities or constraints, e.g., 'low temperature methods', 'solution-based', 'industry-scalable'."

        # Check for structure questions
        elif any(word in q_text_lower for word in ["structure", "crystal", "morphology"]):
            return "Describe the desired structure, e.g., 'layered materials', 'cubic crystals', 'porous framework', 'one-dimensional chains'."

        # Default guidance
        return "Describe what you're looking for in your own words. Be as specific or general as you feel comfortable with."

    def _generate_likely_answers(
        self, questions: list[Question], analysis: QueryAnalysisResponse | None
    ) -> dict[str, Any]:
        """Generates likely answers for intermediate users based on query analysis."""
        # Placeholder: Similar to smart assumptions but for pre-filling answers.
        logger.info("Generating likely answers (placeholder implementation)")
        return self._generate_fallback_assumptions(questions, analysis)
