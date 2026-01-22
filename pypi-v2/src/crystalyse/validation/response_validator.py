"""
Comprehensive response validation system for CrystaLyse agent.

This module provides tools to validate that computational responses contain
actual tool outputs rather than hallucinated results.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """Types of validation violations."""

    HALLUCINATION = "hallucination"  # Computational results without tool calls
    NUMERICAL_FABRICATION = "numerical_fabrication"  # Specific numbers without computation
    TOOL_SIMULATION = "tool_simulation"  # Simulating tool outputs
    CONFIDENCE_FABRICATION = "confidence_fabrication"  # Fake confidence scores


@dataclass
class ValidationViolation:
    """Details about a validation violation."""

    type: ViolationType
    severity: str  # "critical", "warning", "info"
    pattern: str
    description: str
    suggested_fix: str


class ComputationalResultDetector:
    """Detect patterns that indicate computational results in text."""

    def __init__(self):
        self.patterns = {
            # Formation energies and energies
            "formation_energy": [
                r"formation energy:?\s*-?\d+\.\d+\s*ev",
                r"energy:?\s*-?\d+\.\d+\s*ev(?:/atom)?",
                r"stability:?\s*-?\d+\.\d+\s*ev",
                r"hull distance:?\s*\d+\.\d+\s*ev",
            ],
            # SMACT validation results
            "smact_validation": [
                r"smact.*valid(?:ation)?.*(?:valid|pass|✅)",
                r"valid(?:ation)?.*confidence.*\d+\.?\d*",
                r"confidence.*score.*\d+\.?\d*",
                r"charge.?balanced?.*composition",
                r"oxidation.*state.*valid",
            ],
            # Crystal structure information
            "crystal_structure": [
                r"space group:?\s*[A-Za-z0-9/-]+",
                r"crystal system:?\s*[A-Za-z]+",
                r"lattice parameters?:?\s*a\s*=\s*\d+",
                r"unit cell.*volume.*\d+",
                r"symmetry.*[A-Za-z0-9/-]+",
            ],
            # Chemeleon-specific outputs
            "structure_generation": [
                r"structure.*generated.*chemeleon",
                r"cif.*format.*structure",
                r"polymorph.*predicted",
                r"diffusion.*model.*structure",
            ],
            # MACE-specific outputs
            "energy_calculation": [
                r"mace.*calculated.*energy",
                r"forces.*calculated",
                r"uncertainty.*eV",
                r"committee.*models",
            ],
            # General computational claims
            "computational_claims": [
                r"calculated using",
                r"computed with",
                r"predicted by",
                r"analysis shows",
                r"results indicate",
            ],
        }

    def detect_computational_content(self, text: str) -> dict[str, list[str]]:
        """Detect computational content patterns in text."""
        detected = {}
        text_lower = text.lower()

        for category, pattern_list in self.patterns.items():
            matches = []
            for pattern in pattern_list:
                found = re.findall(pattern, text_lower)
                matches.extend(found)

            if matches:
                detected[category] = matches

        return detected


class HallucinationValidator:
    """Main validator for detecting hallucinated computational results."""

    def __init__(self):
        self.detector = ComputationalResultDetector()
        self.forbidden_phrases = [
            # Direct tool simulation
            "smact validation:",
            "mace calculation:",
            "chemeleon prediction:",
            # Fake confidence indicators
            "confidence: 0.",
            "confidence score: 0.",
            "reliability: ",
            # Typical value claims
            "typically around",
            "usually stable",
            "generally valid",
            "commonly found",
            # Simulation phrases
            "validation result:",
            "calculation result:",
            "prediction result:",
        ]

    def validate_response(
        self, query: str, response: str, tool_calls: list[Any], requires_computation: bool = None
    ) -> tuple[bool, list[ValidationViolation]]:
        """
        Validate a response for computational integrity.

        Returns:
            (is_valid, violations)
        """
        violations = []

        # Skip validation for non-computational queries
        if not requires_computation and not self._likely_computational(query):
            return True, []

        # Detect computational content in response
        computational_content = self.detector.detect_computational_content(response)

        # Check if response contains computational results
        has_computational_results = bool(computational_content)

        # Check if tools were actually called
        tools_called = len(tool_calls) > 0

        # Critical violation: computational results without tool calls
        if has_computational_results and not tools_called:
            violations.append(
                ValidationViolation(
                    type=ViolationType.HALLUCINATION,
                    severity="critical",
                    pattern="computational_results_without_tools",
                    description=f"Response contains computational results but no tools were called. Found: {list(computational_content.keys())}",
                    suggested_fix="Retry query with tool_choice='required' or add explicit tool calling instructions",
                )
            )

        # Check for forbidden phrases
        response_lower = response.lower()
        for phrase in self.forbidden_phrases:
            if phrase in response_lower:
                violations.append(
                    ValidationViolation(
                        type=ViolationType.TOOL_SIMULATION,
                        severity="critical",
                        pattern=f"forbidden_phrase: {phrase}",
                        description=f"Response contains forbidden phrase that simulates tool output: '{phrase}'",
                        suggested_fix="Remove simulated tool outputs and use actual tool calls",
                    )
                )

        # Check for specific numerical fabrication patterns
        numerical_violations = self._check_numerical_fabrication(response, tools_called)
        violations.extend(numerical_violations)

        # Check for confidence score fabrication
        confidence_violations = self._check_confidence_fabrication(response, tools_called)
        violations.extend(confidence_violations)

        is_valid = not any(v.severity == "critical" for v in violations)

        return is_valid, violations

    def _likely_computational(self, query: str) -> bool:
        """Check if query likely requires computation even if not explicitly flagged."""
        computational_indicators = [
            "validate",
            "check",
            "calculate",
            "energy",
            "stable",
            "structure",
            "formation",
            "synthesis",
            "properties",
            "analysis",
        ]

        query_lower = query.lower()
        return any(indicator in query_lower for indicator in computational_indicators)

    def _check_numerical_fabrication(
        self, response: str, tools_called: bool
    ) -> list[ValidationViolation]:
        """Check for specific numerical values that should come from tools."""
        violations = []

        if tools_called:
            return violations  # Numbers are OK if tools were called

        # Pattern for formation energies
        energy_pattern = r"-?\d+\.\d+\s*ev"
        energy_matches = re.findall(energy_pattern, response.lower())

        if energy_matches:
            violations.append(
                ValidationViolation(
                    type=ViolationType.NUMERICAL_FABRICATION,
                    severity="critical",
                    pattern="energy_values_without_tools",
                    description=f"Energy values found without tool calls: {energy_matches}",
                    suggested_fix="Use MACE tools to calculate actual energy values",
                )
            )

        # Pattern for confidence scores
        confidence_pattern = r"confidence.*?(\d+\.?\d*)(?:%|\s|$)"
        confidence_matches = re.findall(confidence_pattern, response.lower())

        if confidence_matches:
            violations.append(
                ValidationViolation(
                    type=ViolationType.CONFIDENCE_FABRICATION,
                    severity="critical",
                    pattern="confidence_scores_without_tools",
                    description=f"Confidence scores found without tool calls: {confidence_matches}",
                    suggested_fix="Use SMACT tools to get actual confidence scores",
                )
            )

        return violations

    def _check_confidence_fabrication(
        self, response: str, tools_called: bool
    ) -> list[ValidationViolation]:
        """Check for fabricated confidence scores and validation results."""
        violations = []

        if tools_called:
            return violations

        # Specific patterns that indicate SMACT-style outputs
        smact_patterns = [
            r"confidence.*0\.\d+",
            r"validity.*pass",
            r"valid.*composition",
            r"charge.*balanced",
        ]

        response_lower = response.lower()
        for pattern in smact_patterns:
            if re.search(pattern, response_lower):
                violations.append(
                    ValidationViolation(
                        type=ViolationType.TOOL_SIMULATION,
                        severity="critical",
                        pattern=f"smact_simulation: {pattern}",
                        description="Response simulates SMACT validation output without tool call",
                        suggested_fix="Use actual SMACT validation tools",
                    )
                )

        return violations


class ResponseSanitizer:
    """Clean responses that contain violations."""

    def sanitize_response(self, response: str, violations: list[ValidationViolation]) -> str:
        """Remove or flag problematic content in response."""
        sanitized = response

        # For critical violations, replace with error message
        critical_violations = [v for v in violations if v.severity == "critical"]

        if critical_violations:
            error_msg = """
I apologize, but I cannot provide computational results without actually running the calculations.

To properly answer your query, I need to use the actual computational tools:
- SMACT for composition validation
- Chemeleon for structure prediction
- MACE for energy calculations

Let me retry with the proper computational tools...
"""
            return error_msg.strip()

        # For warnings, add disclaimers
        warning_violations = [v for v in violations if v.severity == "warning"]
        if warning_violations:
            disclaimer = "\n\n⚠️ Note: Some results in this response may need verification with computational tools."
            sanitized += disclaimer

        return sanitized


def create_response_validator() -> HallucinationValidator:
    """Factory function to create a configured response validator."""
    return HallucinationValidator()


# Convenience function for easy integration
def validate_computational_response(
    query: str, response: str, tool_calls: list[Any], requires_computation: bool = None
) -> tuple[bool, str, list[ValidationViolation]]:
    """
    Validate a computational response and return sanitized version.

    Returns:
        (is_valid, sanitized_response, violations)
    """
    validator = create_response_validator()
    sanitizer = ResponseSanitizer()

    is_valid, violations = validator.validate_response(
        query, response, tool_calls, requires_computation
    )

    if not is_valid:
        sanitized_response = sanitizer.sanitize_response(response, violations)
    else:
        sanitized_response = response

    return is_valid, sanitized_response, violations
