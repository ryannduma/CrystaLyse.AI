"""Skill Registry - Index for matching queries to skills.

This module provides skill matching based on:
1. Explicit skill mentions ($skill-name or skill-name)
2. Description-based matching (fuzzy matching on task descriptions)
"""

import logging
import re
from dataclasses import dataclass

from .loader import SkillLoader, SkillMetadata

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """A matched skill with confidence score."""

    skill: SkillMetadata
    score: float  # 0.0 to 1.0
    match_type: str  # "explicit", "keyword", "semantic"
    matched_terms: list[str]


class SkillRegistry:
    """Registry for matching queries to skills.

    Supports three matching modes:
    1. Explicit: $skill-name or mention by name
    2. Keyword: Match keywords in skill description
    3. Semantic: (Future) Use embeddings for semantic matching
    """

    # Pattern for explicit skill invocation ($skill-name)
    EXPLICIT_PATTERN = re.compile(r"\$([a-z][a-z0-9-]*)", re.IGNORECASE)

    # Common materials science keywords for matching
    MATERIALS_KEYWORDS = {
        "smact-validation": [
            "validate",
            "composition",
            "oxidation",
            "charge",
            "balanced",
            "smact",
            "electronegativity",
            "synthesizable",
            "feasible",
            "formula",
            "plausible",
            "check validity",
        ],
        "chemeleon-prediction": [
            "predict",
            "structure",
            "crystal",
            "csp",
            "dng",
            "generate",
            "chemeleon",
            "de novo",
            "new material",
            "discover",
        ],
        "mace-calculation": [
            "energy",
            "relax",
            "optimize",
            "mace",
            "formation",
            "forces",
            "calculate",
            "dft",
            "mlip",
            "interatomic",
        ],
        "phase-diagram": [
            "phase",
            "diagram",
            "hull",
            "stability",
            "decomposition",
            "competing",
            "thermodynamic",
            "convex hull",
            "ehull",
        ],
        "visualization": [
            "visualize",
            "plot",
            "display",
            "3d",
            "structure",
            "render",
            "cif",
            "image",
            "show",
        ],
    }

    def __init__(self, loader: SkillLoader | None = None):
        """Initialize the registry.

        Args:
            loader: SkillLoader instance (creates one if not provided)
        """
        self.loader = loader or SkillLoader()
        self._skills: list[SkillMetadata] = []
        self._loaded = False

    def load(self) -> None:
        """Load all skills into the registry."""
        outcome = self.loader.load_skills()
        self._skills = outcome.skills
        self._loaded = True

        if outcome.errors:
            for error in outcome.errors:
                logger.warning(f"Skill load error: {error}")

        logger.info(f"Registry loaded {len(self._skills)} skills")

    def ensure_loaded(self) -> None:
        """Ensure skills are loaded."""
        if not self._loaded:
            self.load()

    def match_query(self, query: str, threshold: float = 0.3) -> list[SkillMatch]:
        """Match a query to relevant skills.

        Args:
            query: User query or task description
            threshold: Minimum score to include (0.0 to 1.0)

        Returns:
            List of SkillMatch objects, sorted by score descending
        """
        self.ensure_loaded()
        matches = []

        # Check for explicit skill mentions
        explicit_mentions = self.EXPLICIT_PATTERN.findall(query)
        for mention in explicit_mentions:
            skill = self._find_skill_by_name(mention)
            if skill:
                matches.append(
                    SkillMatch(
                        skill=skill, score=1.0, match_type="explicit", matched_terms=[f"${mention}"]
                    )
                )

        # Check for name mentions (without $)
        query_lower = query.lower()
        for skill in self._skills:
            # Skip if already matched explicitly
            if any(m.skill.name == skill.name for m in matches):
                continue

            # Check for name mention
            if skill.name.lower() in query_lower:
                matches.append(
                    SkillMatch(
                        skill=skill, score=0.9, match_type="explicit", matched_terms=[skill.name]
                    )
                )
                continue

            # Keyword matching
            score, matched_terms = self._keyword_match(skill, query_lower)
            if score >= threshold:
                matches.append(
                    SkillMatch(
                        skill=skill, score=score, match_type="keyword", matched_terms=matched_terms
                    )
                )

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches

    def _find_skill_by_name(self, name: str) -> SkillMetadata | None:
        """Find a skill by name (case-insensitive)."""
        name_lower = name.lower()
        for skill in self._skills:
            if skill.name.lower() == name_lower:
                return skill
        return None

    def _keyword_match(self, skill: SkillMetadata, query_lower: str) -> tuple[float, list[str]]:
        """Match a skill against query using keywords.

        Returns:
            Tuple of (score, matched_terms)
        """
        matched_terms = []

        # Get skill-specific keywords or fall back to description words
        keywords = self.MATERIALS_KEYWORDS.get(
            skill.name, self._extract_keywords(skill.description)
        )

        # Count matches
        for keyword in keywords:
            if keyword.lower() in query_lower:
                matched_terms.append(keyword)

        if not matched_terms:
            return 0.0, []

        # Score based on percentage of keywords matched and total matches
        score = min(1.0, len(matched_terms) / max(3, len(keywords) * 0.3))

        return score, matched_terms

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text (simple tokenization)."""
        # Remove common words and split
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "ought",
            "used",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "and",
            "but",
            "if",
            "or",
            "because",
            "as",
            "until",
            "while",
            "this",
            "that",
            "these",
            "those",
            "use",
            "user",
        }

        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        return [w for w in words if w not in stopwords]

    def get_skills_summary(self) -> str:
        """Get a summary of all skills for agent context.

        This is the minimal context that's always included.
        """
        self.ensure_loaded()

        lines = []
        for skill in self._skills:
            # One line per skill: name, description, path
            path_str = str(skill.path).replace("\\", "/")
            lines.append(f"- {skill.name}: {skill.description} (file: {path_str})")

        return "\n".join(lines)

    def get_skill_names(self) -> list[str]:
        """Get list of all skill names."""
        self.ensure_loaded()
        return [s.name for s in self._skills]
