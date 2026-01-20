"""SMACT validation tools - extracted from MCP server.

This module provides core SMACT validation functionality without MCP dependencies.
Pure Python functions that can be imported and used by any part of the system.
"""

import warnings
from typing import Any

import numpy as np

# Import SMACT libraries
from pydantic import BaseModel, Field
from smact import Element
from smact.screening import smact_validity as smact_validity_check

# Import error handling
from ..errors import ValidationError as ToolValidationError
from ..errors import with_retry

# Suppress electronegativity warnings
warnings.filterwarnings("ignore", message=".*Pauling electronegativity.*Setting to NaN.*")
warnings.filterwarnings("ignore", message=".*No Pauling electronegativity.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pymatgen")

# Check for optional metallicity support
try:
    from smact.metallicity import metallicity_score

    METALLICITY_AVAILABLE = True
except ImportError:
    METALLICITY_AVAILABLE = False


class ValidationResult(BaseModel):
    """Structured validation result."""

    valid: bool
    formula: str
    oxidation_states: dict[str, float] | None = None
    charge_balanced: bool = Field(default=False)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class StabilityResult(BaseModel):
    """Stability analysis result."""

    formula: str
    stable: bool
    smact_valid: bool
    electronegativity_difference: float | None = None
    bonding_character: str | None = None
    metallicity_score: float | None = None
    stability_prediction: str


def get_robust_electronegativity(
    element_symbol: str, method: str = "pauling", fallback_noble_gas: bool = True
) -> float:
    """
    Get electronegativity with robust fallback methods for noble gases.

    Args:
        element_symbol: Chemical symbol (e.g., "He", "Ne", "Ar")
        method: Electronegativity scale ("pauling", "mulliken", "allred_rochow")
        fallback_noble_gas: Use reasonable estimates for noble gases

    Returns:
        Electronegativity value or NaN if not available
    """
    try:
        elem = Element(element_symbol)

        # Try requested method first
        if method == "pauling" and elem.pauling_eneg is not None:
            return float(elem.pauling_eneg)
        elif (
            method == "mulliken"
            and hasattr(elem, "mulliken_eneg")
            and elem.mulliken_eneg is not None
        ):
            return float(elem.mulliken_eneg)
        elif (
            method == "allred_rochow"
            and hasattr(elem, "allred_rochow_eneg")
            and elem.allred_rochow_eneg is not None
        ):
            return float(elem.allred_rochow_eneg)

        # Fallback to other available methods
        if elem.pauling_eneg is not None:
            return float(elem.pauling_eneg)
        if hasattr(elem, "eig") and elem.eig is not None:
            return float(elem.eig)  # Allen scale

        # Noble gas fallbacks (reasonable estimates based on ionization potential)
        if fallback_noble_gas:
            noble_gas_eneg = {
                "He": 4.16,  # Very high - reluctant to form bonds
                "Ne": 4.79,  # Highest of all elements
                "Ar": 3.24,  # Moderate
                "Kr": 2.97,  # Slightly lower
                "Xe": 2.58,  # Can form some compounds
                "Rn": 2.2,  # Lowest, most reactive noble gas
            }
            if element_symbol in noble_gas_eneg:
                return noble_gas_eneg[element_symbol]

        # If all else fails
        return np.nan

    except Exception:
        return np.nan


class SMACTValidator:
    """Core SMACT validation logic without MCP dependencies."""

    @staticmethod
    def validate_composition(
        formula: str,
        use_pauling_test: bool = True,
        include_alloys: bool = True,
        oxidation_states_set: str = "icsd24",
    ) -> ValidationResult:
        """
        Validate a chemical composition using SMACT rules.

        Args:
            formula: Chemical formula to validate
            use_pauling_test: Whether to apply Pauling electronegativity test
            include_alloys: Consider pure metals valid automatically
            oxidation_states_set: Which oxidation states to use

        Returns:
            Structured validation result
        """
        try:
            from pymatgen.core import Composition

            comp = Composition(formula)

            # Perform SMACT validation
            is_valid = smact_validity_check(
                comp,
                use_pauling_test=use_pauling_test,
                include_alloys=include_alloys,
                oxidation_states_set=oxidation_states_set,
            )

            # Get oxidation states if possible
            oxidation_states = {}
            try:
                for element in comp.elements:
                    elem = Element(element.symbol)
                    if elem.oxidation_states:
                        oxidation_states[element.symbol] = elem.oxidation_states[0]
            except Exception:
                pass

            return ValidationResult(
                valid=is_valid,
                formula=formula,
                oxidation_states=oxidation_states if oxidation_states else None,
                charge_balanced=is_valid,
                message="Valid composition" if is_valid else "Invalid composition",
                metadata={
                    "method": "smact_validity",
                    "pauling_test": use_pauling_test,
                    "oxidation_states_set": oxidation_states_set,
                },
            )

        except Exception as e:
            return ValidationResult(
                valid=False,
                formula=formula,
                errors=[str(e)],
                message=f"Validation failed: {str(e)}",
            )

    @staticmethod
    def analyze_stability(
        composition: str,
        check_electronegativity: bool = True,
        electronegativity_threshold: float = 0.5,
    ) -> StabilityResult:
        """
        Comprehensive stability analysis using enhanced SMACT methods.

        Args:
            composition: Chemical formula
            check_electronegativity: Whether to check electronegativity differences
            electronegativity_threshold: Minimum difference for ionic bonding

        Returns:
            Structured stability analysis result
        """
        try:
            from pymatgen.core import Composition

            comp = Composition(composition)

            # Basic SMACT validity
            is_valid = smact_validity_check(comp, use_pauling_test=True, include_alloys=True)

            # Electronegativity analysis with robust handling
            eneg_diff = None
            bonding_char = None

            if check_electronegativity:
                elements = list(comp.as_dict().keys())
                electronegativities = []

                for elem in elements:
                    eneg = get_robust_electronegativity(elem, method="pauling")
                    electronegativities.append(eneg)

                # Filter out NaN values for analysis
                valid_enegs = [e for e in electronegativities if not np.isnan(e)]

                if len(valid_enegs) >= 2:
                    eneg_diff = max(valid_enegs) - min(valid_enegs)
                    bonding_char = (
                        "ionic" if eneg_diff > electronegativity_threshold else "covalent"
                    )

            # Metallicity check if available
            met_score = None
            if METALLICITY_AVAILABLE:
                try:
                    met_score = metallicity_score(comp)
                except Exception:
                    pass

            return StabilityResult(
                formula=composition,
                stable=is_valid,
                smact_valid=is_valid,
                electronegativity_difference=eneg_diff,
                bonding_character=bonding_char,
                metallicity_score=met_score,
                stability_prediction="stable" if is_valid else "potentially unstable",
            )

        except Exception:
            return StabilityResult(
                formula=composition,
                stable=False,
                smact_valid=False,
                stability_prediction="analysis_failed",
            )

    @with_retry(
        max_attempts=3,
        recoverable_exceptions=(ToolValidationError,),
        fallback_result=lambda: ValidationResult(
            valid=False,
            formula="unknown",
            errors=["Validation service unavailable"],
            message="Could not validate - assuming invalid for safety",
        ),
    )
    async def validate_composition_async(
        self,
        formula: str,
        use_pauling_test: bool = True,
        include_alloys: bool = True,
        oxidation_states_set: str = "icsd24",
    ) -> ValidationResult:
        """Async validation with retry logic."""
        try:
            # Attempt validation
            result = self.validate_composition(
                formula, use_pauling_test, include_alloys, oxidation_states_set
            )

            if result.errors:
                # Check if error is recoverable
                if "timeout" in str(result.errors).lower():
                    raise ToolValidationError(
                        "Validation timeout", recoverable=True, fallback=result
                    )

            return result

        except ImportError as e:
            # Missing dependency - non-recoverable
            raise ToolValidationError(
                f"Required package not available: {e}",
                recoverable=False,
                fallback=ValidationResult(
                    valid=False,
                    formula=formula,
                    errors=[str(e)],
                    message="Validation unavailable - missing dependencies",
                ),
            ) from e
