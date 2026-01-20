"""SMACT calculation tools - extracted from MCP server."""

import numpy as np
from pydantic import BaseModel, Field

from .validators import get_robust_electronegativity


class BandGapResult(BaseModel):
    """Band gap prediction result."""

    formula: str
    band_gap_ev: float | None = None
    band_gap_estimate: str
    method: str
    electronegativity_difference: float | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class ElementInfo(BaseModel):
    """Element information result."""

    symbol: str
    name: str
    atomic_number: int
    atomic_mass: float
    electronegativity: float | None = None
    oxidation_states: dict[str, list[int]] | None = None


class SMACTCalculator:
    """SMACT-based calculations without MCP dependencies."""

    @staticmethod
    def predict_band_gap(composition: str) -> BandGapResult:
        """
        Predict band gap using Harrison's approach with robust electronegativity.

        Args:
            composition: Chemical formula

        Returns:
            Structured band gap prediction result
        """
        try:
            from pymatgen.core import Composition

            comp = Composition(composition)

            elements = list(comp.as_dict().keys())

            # Get electronegativities robustly
            electronegativities = []
            for elem in elements:
                eneg = get_robust_electronegativity(elem, method="pauling")
                if not np.isnan(eneg):
                    electronegativities.append(eneg)

            if len(electronegativities) < 2:
                return BandGapResult(
                    formula=composition,
                    band_gap_estimate="unknown",
                    method="harrison",
                    confidence=0.0,
                )

            # Simple Harrison-based estimate (very approximate)
            eneg_diff = max(electronegativities) - min(electronegativities)

            # Empirical relationship (very rough approximation)
            if eneg_diff > 2.0:
                gap_estimate = "large (>3 eV) - likely insulator"
                confidence = 0.6
            elif eneg_diff > 1.0:
                gap_estimate = "moderate (1-3 eV) - likely semiconductor"
                confidence = 0.7
            else:
                gap_estimate = "small (<1 eV) - likely metal or small gap semiconductor"
                confidence = 0.5

            return BandGapResult(
                formula=composition,
                electronegativity_difference=eneg_diff,
                band_gap_estimate=gap_estimate,
                method="Harrison-inspired electronegativity difference",
                confidence=confidence,
            )

        except Exception:
            return BandGapResult(
                formula=composition, band_gap_estimate="error", method="harrison", confidence=0.0
            )

    @staticmethod
    def get_element_info(symbol: str, include_oxidation_states: bool = True) -> ElementInfo:
        """
        Get detailed properties of a chemical element from SMACT database.

        Args:
            symbol: Chemical symbol (e.g., "Fe", "O", "Li")
            include_oxidation_states: Whether to include oxidation state data

        Returns:
            Structured element information
        """
        try:
            from smact import Element

            elem = Element(symbol)

            ox_states = None
            if include_oxidation_states:
                ox_states = {}
                if hasattr(elem, "oxidation_states_icsd24"):
                    ox_states["icsd24"] = elem.oxidation_states_icsd24
                if hasattr(elem, "oxidation_states_icsd16"):
                    ox_states["icsd16"] = elem.oxidation_states_icsd16
                if hasattr(elem, "oxidation_states_smact14"):
                    ox_states["smact14"] = elem.oxidation_states_smact14
                if hasattr(elem, "oxidation_states_wiki"):
                    ox_states["wiki"] = elem.oxidation_states_wiki

            return ElementInfo(
                symbol=elem.symbol,
                name=elem.name,
                atomic_number=elem.number,
                atomic_mass=elem.mass,
                electronegativity=elem.pauling_eneg,
                oxidation_states=ox_states if ox_states else None,
            )

        except Exception as e:
            raise ValueError(f"Failed to get element info for {symbol}: {e}") from e
