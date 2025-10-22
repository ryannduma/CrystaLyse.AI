"""PyMatgen phase diagram tools - energy above hull calculations."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import gzip
import pickle
import os
from pathlib import Path

from pymatgen.core import Composition
from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram

logger = logging.getLogger(__name__)

# Global phase diagram data
_PPD_DATA: Optional[PhaseDiagram] = None
_PPD_PATH: Optional[str] = None


class EnergyAboveHullResult(BaseModel):
    """Energy above hull calculation result."""
    success: bool = True
    composition: str
    energy_per_atom: float
    energy_above_hull: float
    is_stable: bool
    is_metastable: bool
    is_unstable: bool
    decomposition_products: List[Dict[str, Any]] = Field(default_factory=list)
    competing_phases: int = 0
    error: Optional[str] = None


def _load_phase_diagram() -> Optional[PhaseDiagram]:
    """Load the pre-computed phase diagram."""
    global _PPD_DATA, _PPD_PATH

    if _PPD_DATA is not None:
        return _PPD_DATA

    # Try to find the phase diagram file
    possible_paths = [
        "/home/ryan/mycrystalyse/CrystaLyse.AI/ppd-mp_all_entries_uncorrected_250409.pkl.gz",
        Path(__file__).parent.parent.parent.parent.parent.parent / "ppd-mp_all_entries_uncorrected_250409.pkl.gz",
        Path.home() / "mycrystalyse/CrystaLyse.AI/ppd-mp_all_entries_uncorrected_250409.pkl.gz",
        os.getenv("CRYSTALYSE_PPD_PATH", "")
    ]

    for path in possible_paths:
        path_str = str(path)
        if path_str and os.path.exists(path_str):
            _PPD_PATH = path_str
            break

    if not _PPD_PATH:
        logger.warning("Phase diagram file not found. Energy above hull calculations will not be available.")
        return None

    try:
        with gzip.open(_PPD_PATH, "rb") as f:
            _PPD_DATA = pickle.load(f)
        logger.info(f"Loaded phase diagram with {len(_PPD_DATA.all_entries)} entries from {_PPD_PATH}")
        return _PPD_DATA
    except Exception as e:
        logger.error(f"Failed to load phase diagram from {_PPD_PATH}: {e}")
        return None


class PhaseDiagramAnalyzer:
    """PyMatgen phase diagram analysis tools."""

    def __init__(self):
        """Initialize with phase diagram loading."""
        self.ppd_data = _load_phase_diagram()

    def calculate_energy_above_hull(
        self,
        composition: str,
        energy: float,
        per_atom: bool = True
    ) -> EnergyAboveHullResult:
        """
        Calculate the energy above the convex hull for a given composition and energy.

        Args:
            composition: Chemical formula (e.g., "Li2O", "NaCl")
            energy: Total energy or energy per atom (in eV)
            per_atom: Whether the provided energy is per atom (default: True)

        Returns:
            Structured energy above hull result
        """
        try:
            if self.ppd_data is None:
                return EnergyAboveHullResult(
                    success=False,
                    composition=composition,
                    energy_per_atom=0.0,
                    energy_above_hull=float('inf'),
                    is_stable=False,
                    is_metastable=False,
                    is_unstable=True,
                    error="Phase diagram data not loaded"
                )

            # Parse composition
            comp = Composition(composition)

            # Convert energy to total if needed
            if per_atom:
                total_energy = energy * comp.num_atoms
                energy_per_atom = energy
            else:
                total_energy = energy
                energy_per_atom = energy / comp.num_atoms

            # Create PDEntry
            entry = PDEntry(comp, total_energy)

            # Calculate energy above hull
            try:
                e_above_hull = self.ppd_data.get_e_above_hull(entry, allow_negative=True)
            except Exception as e:
                logger.warning(f"Failed to calculate energy above hull: {e}")
                e_above_hull = float('inf')

            # Get decomposition products
            try:
                decomp_products = self.ppd_data.get_decomposition(comp)
                decomp_list = [
                    {
                        "formula": phase.composition.reduced_formula,
                        "fraction": float(amount),
                        "energy_per_atom": float(phase.energy_per_atom)
                    }
                    for phase, amount in decomp_products.items()
                ]
            except Exception as e:
                logger.warning(f"Failed to get decomposition products: {e}")
                decomp_list = []

            return EnergyAboveHullResult(
                success=True,
                composition=composition,
                energy_per_atom=energy_per_atom,
                energy_above_hull=float(e_above_hull),
                is_stable=e_above_hull <= 0,
                is_metastable=0 < e_above_hull <= 0.2,
                is_unstable=e_above_hull > 0.2,
                decomposition_products=decomp_list,
                competing_phases=len(decomp_list)
            )

        except Exception as e:
            logger.error(f"Energy above hull calculation failed: {e}")
            return EnergyAboveHullResult(
                success=False,
                composition=composition,
                energy_per_atom=0.0,
                energy_above_hull=float('inf'),
                is_stable=False,
                is_metastable=False,
                is_unstable=True,
                error=str(e)
            )

    def is_loaded(self) -> bool:
        """Check if phase diagram is loaded."""
        return self.ppd_data is not None

    def get_num_entries(self) -> int:
        """Get number of entries in phase diagram."""
        if self.ppd_data is None:
            return 0
        return len(self.ppd_data.all_entries)
