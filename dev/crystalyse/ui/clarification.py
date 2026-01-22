"""Simplified Clarification System for CrystaLyse V2.

This module handles clarification of ambiguous queries by asking
domain-specific questions. It does NOT:
- Detect or recommend modes (user controls via --rigorous flag)
- Score user expertise
- Load or trigger skills

It ONLY identifies missing parameters and asks clarifying questions.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

logger = logging.getLogger(__name__)


@dataclass
class ClarificationQuestion:
    """A single clarification question."""

    id: str
    text: str
    options: list[str] | None = None
    default: str | None = None
    required: bool = False


@dataclass
class ClarificationResult:
    """Result of the clarification process."""

    answers: dict[str, Any]
    skipped: bool = False
    method: str = "interactive"


class ClarificationSystem:
    """Ask clarifying questions when query is ambiguous.

    This is a simple system that:
    1. Checks if query has enough information
    2. Asks domain-specific questions if needed
    3. Returns the answers

    No mode detection. No expertise scoring. Just clarification.
    """

    def __init__(self, console: Console | None = None):
        """Initialize the clarification system.

        Args:
            console: Rich console for output (creates one if not provided)
        """
        self.console = console or Console()

        # Domain-specific question templates
        self.question_templates = self._init_question_templates()

    def _init_question_templates(self) -> dict[str, ClarificationQuestion]:
        """Initialize the question templates."""
        return {
            "battery_type": ClarificationQuestion(
                id="battery_type",
                text="What type of battery are you interested in?",
                options=["Li-ion", "Na-ion", "Mg-ion", "Solid-state", "Any"],
                default="Li-ion",
            ),
            "electrode": ClarificationQuestion(
                id="electrode",
                text="Which component are you focusing on?",
                options=["Cathode", "Anode", "Electrolyte", "Any"],
                default="Cathode",
            ),
            "target_property": ClarificationQuestion(
                id="target_property",
                text="What property should be optimized?",
                options=[
                    "High capacity",
                    "High voltage",
                    "Long cycle life",
                    "Fast charging",
                    "Low cost",
                ],
                default="High capacity",
            ),
            "elements_include": ClarificationQuestion(
                id="elements_include",
                text="Any specific elements to include? (comma-separated, or 'none')",
                options=None,
                default="none",
            ),
            "elements_exclude": ClarificationQuestion(
                id="elements_exclude",
                text="Any elements to avoid? (e.g., Pb, Co, or 'none')",
                options=None,
                default="none",
            ),
            "temperature_range": ClarificationQuestion(
                id="temperature_range",
                text="Target operating temperature?",
                options=["Room temperature", "Low (<500K)", "Mid (500-800K)", "High (>800K)"],
                default="Room temperature",
            ),
            "stability_priority": ClarificationQuestion(
                id="stability_priority",
                text="How important is thermodynamic stability?",
                options=["Critical", "Important", "Nice to have", "Not important"],
                default="Important",
            ),
            "formula": ClarificationQuestion(
                id="formula",
                text="Do you have a specific formula in mind? (or 'explore')",
                options=None,
                default="explore",
            ),
        }

    def needs_clarification(self, query: str) -> bool:
        """Check if a query needs clarification.

        A query needs clarification if:
        - It's very short (< 5 words)
        - It lacks specific constraints
        - It's purely exploratory

        Args:
            query: The user's query

        Returns:
            True if clarification would be helpful
        """
        query_lower = query.lower()
        word_count = len(query.split())

        # Very short queries need clarification
        if word_count < 5:
            return True

        # Check for specificity indicators
        specific_patterns = [
            r"[A-Z][a-z]?\d?",  # Chemical formula elements
            r"\d+\.\d+",  # Decimal numbers
            r"eV|GPa|mAh|Wh/kg",  # Units
            r"spinel|olivine|layered|perovskite",  # Structure types
            r"LiFePO4|NMC|LCO|NCA",  # Common material names
        ]

        specificity_score = sum(1 for pattern in specific_patterns if re.search(pattern, query))

        # If query has specific information, skip clarification
        if specificity_score >= 2:
            return False

        # Exploratory queries need clarification
        exploratory_keywords = ["find", "suggest", "recommend", "explore", "discover", "what"]
        if any(kw in query_lower for kw in exploratory_keywords):
            return True

        return False

    def get_questions(self, query: str) -> list[ClarificationQuestion]:
        """Get relevant clarification questions for a query.

        Args:
            query: The user's query

        Returns:
            List of relevant questions to ask
        """
        query_lower = query.lower()
        questions = []

        # Battery-related queries
        if any(
            kw in query_lower
            for kw in ["battery", "cathode", "anode", "electrode", "li-ion", "na-ion"]
        ):
            if "cathode" not in query_lower and "anode" not in query_lower:
                questions.append(self.question_templates["electrode"])
            if "li" not in query_lower and "na" not in query_lower:
                questions.append(self.question_templates["battery_type"])
            questions.append(self.question_templates["target_property"])

        # Thermoelectric queries
        elif any(kw in query_lower for kw in ["thermoelectric", "seebeck", "zt"]):
            questions.append(self.question_templates["temperature_range"])
            questions.append(self.question_templates["stability_priority"])

        # General materials queries
        elif any(kw in query_lower for kw in ["material", "compound", "structure"]):
            questions.append(self.question_templates["elements_include"])
            questions.append(self.question_templates["elements_exclude"])
            questions.append(self.question_templates["stability_priority"])

        # Composition-related
        elif any(kw in query_lower for kw in ["composition", "formula", "valid"]):
            questions.append(self.question_templates["formula"])

        # Default: ask about elements and stability
        if not questions:
            questions.append(self.question_templates["elements_include"])
            questions.append(self.question_templates["stability_priority"])

        return questions

    def ask_questions(self, questions: list[ClarificationQuestion]) -> ClarificationResult:
        """Ask the clarification questions interactively.

        Args:
            questions: List of questions to ask

        Returns:
            ClarificationResult with answers
        """
        if not questions:
            return ClarificationResult(answers={}, skipped=True, method="no_questions")

        self.console.print(
            Panel(
                "I need a bit more information to help you effectively.",
                title="[bold cyan]Quick Clarification[/bold cyan]",
                border_style="cyan",
            )
        )

        answers = {}

        for question in questions:
            if question.options:
                # Multiple choice question
                answer = Prompt.ask(
                    f"[bold]{question.text}[/bold]",
                    choices=question.options,
                    default=question.default or question.options[0],
                )
            else:
                # Free-text question
                answer = Prompt.ask(
                    f"[bold]{question.text}[/bold]",
                    default=question.default or "",
                )

            answers[question.id] = answer

        return ClarificationResult(
            answers=answers,
            skipped=False,
            method="interactive",
        )

    def clarify(self, query: str) -> ClarificationResult:
        """Main entry point: check if clarification needed and ask questions.

        Args:
            query: The user's query

        Returns:
            ClarificationResult with answers (may be empty if no clarification needed)
        """
        if not self.needs_clarification(query):
            logger.info("Query is specific enough, skipping clarification")
            return ClarificationResult(answers={}, skipped=True, method="skipped")

        questions = self.get_questions(query)
        return self.ask_questions(questions)

    def apply_defaults(self, query: str) -> dict[str, Any]:
        """Generate default answers without asking the user.

        Useful for non-interactive mode.

        Args:
            query: The user's query

        Returns:
            Dictionary of default answers
        """
        questions = self.get_questions(query)
        return {q.id: q.default or (q.options[0] if q.options else "") for q in questions}


def clarify_query(query: str, console: Console | None = None) -> ClarificationResult:
    """Convenience function to clarify a query.

    Args:
        query: The user's query
        console: Optional Rich console

    Returns:
        ClarificationResult
    """
    system = ClarificationSystem(console)
    return system.clarify(query)
