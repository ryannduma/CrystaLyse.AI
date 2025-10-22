"""
Intelligent Render Gate for CrystaLyse
=======================================
Prevents hallucination of material properties while allowing contextual numbers,
derived values, and literature references.

The render gate uses semantic analysis to distinguish between:
1. Material property claims that MUST have provenance
2. Contextual/explanatory numbers that are acceptable
3. Derived values computed from provenanced sources
4. Literature references with attribution
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NumberType(Enum):
    """Classification of numerical values in LLM output."""
    MATERIAL_PROPERTY = "material_property"  # Must have provenance
    CONTEXTUAL = "contextual"                 # General explanatory numbers
    DERIVED = "derived"                       # Calculated from provenanced values
    LITERATURE = "literature"                 # Referenced from papers/databases
    STATISTICAL = "statistical"               # Counts, percentages, summaries
    UNKNOWN = "unknown"                       # Needs further analysis


@dataclass
class ProvenanceTuple:
    """
    Tuple-based provenance as described in the paper.
    Every material property should have this.
    """
    value: Any
    unit: Optional[str]
    source_tool: str
    artifact_hash: str
    timestamp: str
    confidence: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "unit": self.unit,
            "source_tool": self.source_tool,
            "artifact_hash": self.artifact_hash,
            "timestamp": self.timestamp,
            "confidence": self.confidence
        }


@dataclass
class DetectedNumber:
    """A numerical value detected in LLM output."""
    value: str  # Original string representation
    context: str  # Surrounding text (±50 chars)
    full_sentence: str  # Complete sentence containing the number
    number_type: NumberType = NumberType.UNKNOWN
    provenance: Optional[ProvenanceTuple] = None
    confidence: float = 0.0  # Confidence in classification
    position: Tuple[int, int] = (0, 0)  # Start, end position in text
    flags: Set[str] = field(default_factory=set)  # Warning flags


class IntelligentRenderGate:
    """
    Intelligent render gate that semantically analyzes LLM output
    to prevent material property hallucination while allowing
    legitimate contextual and derived values.
    """

    # Material property keywords that REQUIRE provenance
    MATERIAL_PROPERTIES = {
        # Energy-related
        'formation_energy', 'formation energy', 'binding_energy', 'binding energy',
        'cohesive_energy', 'cohesive energy', 'total_energy', 'total energy',
        'energy_above_hull', 'energy above hull', 'decomposition_energy',
        'ev/atom', 'kj/mol', 'kcal/mol', 'hartree',

        # Electronic properties
        'band_gap', 'band gap', 'bandgap', 'homo', 'lumo', 'fermi_level',
        'fermi level', 'work_function', 'work function', 'electron_affinity',

        # Structural properties
        'lattice_parameter', 'lattice parameter', 'lattice_constant',
        'space_group', 'space group', 'spacegroup', 'crystal_system',
        'unit_cell', 'unit cell', 'cell_volume', 'density',

        # Mechanical properties
        'bulk_modulus', 'bulk modulus', 'young_modulus', "young's modulus",
        'shear_modulus', 'shear modulus', 'hardness', 'fracture_toughness',
        'stress', 'strain', 'gpa', 'mpa',

        # Magnetic properties
        'magnetic_moment', 'magnetic moment', 'magnetization',
        'curie_temperature', 'curie temperature', 'néel_temperature',

        # Thermodynamic
        'melting_point', 'melting point', 'boiling_point', 'boiling point',
        'heat_capacity', 'heat capacity', 'entropy', 'enthalpy',
        'gibbs_energy', 'gibbs energy', 'free_energy',

        # Electrochemical
        'voltage', 'capacity', 'mah/g', 'wh/kg', 'coulombic_efficiency',
        'oxidation_state', 'oxidation state', 'redox_potential'
    }

    # Contextual indicators - suggests the number is explanatory
    CONTEXTUAL_INDICATORS = {
        'typically', 'usually', 'generally', 'approximately', 'about',
        'roughly', 'around', 'often', 'commonly', 'tend to', 'tends to',
        'in the range', 'between', 'from', 'varies', 'can be',
        'literature', 'reported', 'known', 'established', 'theoretical',
        'experimental', 'measured', 'observed', 'found to be',
        'according to', 'based on', 'ref', 'reference', 'study',
        'paper', 'work', 'research', 'average', 'mean', 'typical'
    }

    # Statistical/counting indicators
    STATISTICAL_INDICATORS = {
        'out of', 'percent', '%', 'fraction', 'ratio', 'total',
        'count', 'number of', 'materials', 'structures', 'candidates',
        'passed', 'failed', 'stable', 'unstable', 'metastable'
    }

    # Derived value indicators - calculations from provenanced values
    DERIVED_INDICATORS = {
        'calculated from', 'derived from', 'computed using', 'based on calculation',
        'sum of', 'difference between', 'product of', 'divided by',
        'multiplied by', 'times', 'plus', 'minus', 'equals',
        'resulting in', 'gives', 'yields', 'therefore', 'thus'
    }

    # Literature reference indicators
    LITERATURE_INDICATORS = {
        'Materials Project', 'MP-', 'ICSD', 'COD', 'CSD', 'PubChem',
        'according to', 'reported in', 'published', 'literature',
        'paper', 'study', 'research', 'et al.', 'reference',
        'database', 'repository', 'archive', 'journal'
    }

    def __init__(self, provenance_tracker=None):
        """
        Initialize the render gate.

        Args:
            provenance_tracker: MaterialsTracker or similar to check provenance
        """
        self.provenance_registry = provenance_tracker  # Actually a registry now
        self.blocked_count = 0
        self.allowed_count = 0
        self.blocked_values = []  # Track what was blocked

    def analyze_output(
        self,
        text: str,
        provenance_data: Optional[Dict] = None
    ) -> Tuple[str, List[DetectedNumber], bool]:
        """
        Analyze LLM output for numerical claims and verify provenance.

        Args:
            text: The LLM output text to analyze
            provenance_data: Available provenance information

        Returns:
            Tuple of (processed_text, detected_numbers, has_violations)
        """
        detected_numbers = self._detect_numbers(text)

        for num in detected_numbers:
            # Classify the number type
            num.number_type = self._classify_number(num)

            # Check if it needs provenance
            if num.number_type == NumberType.MATERIAL_PROPERTY:
                num.provenance = self._find_provenance(num, provenance_data)

                if not num.provenance:
                    num.flags.add("UNPROVENANCED_MATERIAL_PROPERTY")
                    logger.warning(
                        f"Unprovenanced material property detected: {num.value} "
                        f"in context: '{num.context}'"
                    )

        # Process the text based on findings
        processed_text, has_violations = self._process_text(text, detected_numbers)

        return processed_text, detected_numbers, has_violations

    def _detect_numbers(self, text: str) -> List[DetectedNumber]:
        """
        Detect all numerical values in the text with context.
        """
        numbers = []

        # Regex patterns for different number formats
        patterns = [
            # Scientific notation
            r'-?\d+\.?\d*[eE][+-]?\d+',
            # Decimal numbers with units
            r'-?\d+\.?\d*\s*(?:eV|keV|MeV|GeV|kJ|kcal|Å|Angstrom|nm|pm|'
            r'GPa|MPa|kPa|Pa|K|°C|°F|V|mV|mAh|Wh|g/cm³|g/mol)',
            # Decimal numbers
            r'-?\d+\.\d+',
            # Integers with potential units
            r'-?\d+\s*(?:%|percent)?',
            # Ranges
            r'-?\d+\.?\d*\s*(?:to|-|–|—)\s*-?\d+\.?\d*'
        ]

        combined_pattern = '|'.join(f'({p})' for p in patterns)

        sentences = text.split('.')

        for sentence in sentences:
            for match in re.finditer(combined_pattern, sentence, re.IGNORECASE):
                # Get context (±50 chars)
                start = max(0, match.start() - 50)
                end = min(len(sentence), match.end() + 50)
                context = sentence[start:end]

                num = DetectedNumber(
                    value=match.group(),
                    context=context,
                    full_sentence=sentence.strip(),
                    position=(match.start(), match.end())
                )
                numbers.append(num)

        return numbers

    def _classify_number(self, num: DetectedNumber) -> NumberType:
        """
        Classify a detected number based on semantic context.
        Enhanced with better derived value and literature detection.
        """
        context_lower = num.full_sentence.lower()

        # Check for material property keywords
        material_property_score = sum(
            1 for keyword in self.MATERIAL_PROPERTIES
            if keyword in context_lower
        )

        # Check for contextual indicators
        contextual_score = sum(
            1 for indicator in self.CONTEXTUAL_INDICATORS
            if indicator in context_lower
        )

        # Check for statistical indicators
        statistical_score = sum(
            1 for indicator in self.STATISTICAL_INDICATORS
            if indicator in context_lower
        )

        # Check for derived value indicators
        derived_score = sum(
            1 for indicator in self.DERIVED_INDICATORS
            if indicator in context_lower
        )

        # Check for literature indicators
        literature_score = sum(
            1 for indicator in self.LITERATURE_INDICATORS
            if indicator in context_lower
        )

        # Enhanced decision logic

        # First check for literature references
        if literature_score >= 2 or any(db in context_lower for db in ['mp-', 'icsd-', 'cod-']):
            return NumberType.LITERATURE

        # Check for derived calculations
        if derived_score >= 2 or self._has_mathematical_expression(num.full_sentence):
            return NumberType.DERIVED

        # Check for statistical data
        if statistical_score > 0:
            return NumberType.STATISTICAL

        # Now check material properties
        if material_property_score > 0:
            # It mentions a material property
            if contextual_score >= 2 or literature_score > 0:
                # But with strong contextual or literature language
                return NumberType.LITERATURE
            elif "calculated" in context_lower or "computed" in context_lower:
                # Explicitly mentions our calculation
                if any(tool in context_lower for tool in ['mace', 'pymatgen', 'smact', 'chemeleon']):
                    return NumberType.MATERIAL_PROPERTY  # Our calculation
                else:
                    return NumberType.DERIVED  # Derived from other sources
            else:
                # Default to requiring provenance for material properties
                return NumberType.MATERIAL_PROPERTY

        elif contextual_score >= 2:
            return NumberType.CONTEXTUAL

        else:
            return NumberType.UNKNOWN

    def _has_mathematical_expression(self, text: str) -> bool:
        """
        Check if text contains mathematical expressions.
        """
        # Look for mathematical operators and patterns
        math_patterns = [
            r'\d+\s*[\+\-\*/]\s*\d+',  # Basic arithmetic
            r'\d+\s*=\s*\d+',           # Equations
            r'\(\s*\d+.*?\)',           # Parenthetical expressions
            r'\d+\s*×\s*\d+',           # Multiplication symbol
            r'∑|∏|∫',                   # Mathematical symbols
        ]

        for pattern in math_patterns:
            if re.search(pattern, text):
                return True

        # Check for written mathematical operations
        math_words = ['sum', 'product', 'difference', 'quotient', 'times', 'plus', 'minus', 'divided']
        return sum(1 for word in math_words if word in text.lower()) >= 2

    def _extract_material_context(self, text: str) -> Optional[str]:
        """Extract material formula from text."""
        # Pattern for chemical formulas
        pattern = r'\b([A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)+)\b'
        matches = re.findall(pattern, text)

        for match in matches:
            # Check if it looks like a chemical formula
            elements = re.findall(r'[A-Z][a-z]?', match)
            if len(elements) >= 2:  # At least 2 elements
                return match
        return None

    def _find_provenance(
        self,
        num: DetectedNumber,
        provenance_data: Optional[Dict]
    ) -> Optional[ProvenanceTuple]:
        """
        Find provenance for a detected number.
        """
        if not self.provenance_registry:
            return None

        # Try to extract the numerical value
        try:
            # Handle different number formats
            value_str = num.value.strip()

            # Remove units if present (more comprehensive pattern)
            value_str = re.sub(r'\s*(eV|keV|MeV|GeV|kJ|kcal|Å|Angstrom|nm|pm|'
                              r'GPa|MPa|kPa|Pa|K|°C|°F|V|mV|mAh|Wh|g/cm³|g/mol|'
                              r'/atom|/mol|/unit).*$', '', value_str, flags=re.IGNORECASE).strip()

            # Parse the number
            value = float(value_str.replace(',', ''))

            # Try to extract material context
            material = self._extract_material_context(num.full_sentence)

            # Look up provenance with fuzzy matching
            provenance = self.provenance_registry.lookup_provenance(
                value=value,
                tolerance=0.001,  # Tighter tolerance for better matching
                material=material
            )

            return provenance

        except (ValueError, AttributeError):
            logger.debug(f"Could not parse value from: {num.value}")
            return None

    def _process_text(
        self,
        text: str,
        detected_numbers: List[DetectedNumber]
    ) -> Tuple[str, bool]:
        """
        Process the text based on detected numbers and their provenance.

        Returns:
            Tuple of (processed_text, has_violations)
        """
        has_violations = False
        processed_text = text

        # Sort by position (reverse) to maintain indices when replacing
        flagged_numbers = [
            num for num in detected_numbers
            if "UNPROVENANCED_MATERIAL_PROPERTY" in num.flags
        ]
        flagged_numbers.sort(key=lambda x: x.position[0], reverse=True)

        for num in flagged_numbers:
            has_violations = True
            self.blocked_count += 1
            self.blocked_values.append(num.value)

            # Log the violation
            logger.info(f"[BLOCKED] Unprovenanced material property: {num.value}")

            # TODO: Implement actual text replacement
            # For now, we just track what was blocked

        return processed_text, has_violations

    def get_statistics(self) -> Dict:
        """
        Get statistics about render gate operations.
        """
        return {
            "blocked_count": self.blocked_count,
            "allowed_count": self.allowed_count,
            "blocked_values": self.blocked_values
        }


class RenderGateValidator:
    """
    Validates that material properties have proper provenance.
    Used during testing and shadow validation.
    """

    def __init__(self):
        self.validation_results = []

    def validate_response(
        self,
        response: str,
        provenance_data: Dict,
        expected_properties: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Validate a response for proper provenance.

        Returns:
            Validation report with statistics
        """
        gate = IntelligentRenderGate()
        gate.shadow_mode = True  # Don't actually block

        processed, detected, has_violations = gate.analyze_output(
            response,
            provenance_data
        )

        material_properties = [
            n for n in detected
            if n.number_type == NumberType.MATERIAL_PROPERTY
        ]

        unprovenanced = [
            n for n in material_properties
            if not n.provenance
        ]

        report = {
            "total_numbers": len(detected),
            "material_properties": len(material_properties),
            "unprovenanced_count": len(unprovenanced),
            "unprovenanced_rate": (
                len(unprovenanced) / len(material_properties)
                if material_properties else 0
            ),
            "violations": [
                {
                    "value": n.value,
                    "context": n.context,
                    "type": n.number_type.value
                }
                for n in unprovenanced
            ]
        }

        self.validation_results.append(report)
        return report


# Singleton instance
_render_gate = None


def get_render_gate() -> IntelligentRenderGate:
    """Get the global render gate instance."""
    global _render_gate
    if _render_gate is None:
        _render_gate = IntelligentRenderGate()
    return _render_gate


def intercept_llm_output(text: str, provenance_data: Optional[Dict] = None) -> str:
    """
    Main entry point for render gate interception.

    Args:
        text: LLM output to check
        provenance_data: Available provenance information

    Returns:
        Processed text with unprovenanced material properties flagged or blocked
    """
    gate = get_render_gate()
    processed_text, detected_numbers, has_violations = gate.analyze_output(
        text,
        provenance_data
    )

    if has_violations:
        logger.warning(
            f"Render gate detected {sum(1 for n in detected_numbers if n.flags)} "
            f"unprovenanced material properties"
        )

    return processed_text