"""PyMatgen analysis tools - space group, coordination, oxidation states."""
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import logging
import numpy as np

from pymatgen.core import Structure, Composition
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.analysis.bond_valence import BVAnalyzer
from pymatgen.analysis.local_env import VoronoiNN
from pymatgen.io.cif import CifParser

logger = logging.getLogger(__name__)


class SpaceGroupResult(BaseModel):
    """Space group analysis result."""
    success: bool = True
    space_group_symbol: str
    space_group_number: int
    point_group: str
    crystal_system: str
    hall_symbol: str
    original_formula: str
    original_num_atoms: int
    primitive_formula: str
    primitive_num_atoms: int
    num_symmetry_ops: int
    lattice_a: float
    lattice_b: float
    lattice_c: float
    lattice_alpha: float
    lattice_beta: float
    lattice_gamma: float
    volume: float
    symmetrized_cif: Optional[str] = None
    primitive_cif: Optional[str] = None
    error: Optional[str] = None


class CoordinationResult(BaseModel):
    """Coordination analysis result."""
    success: bool = True
    formula: str
    num_sites: int
    sites_analyzed: int
    average_coordination: float
    coordination_data: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class OxidationStateResult(BaseModel):
    """Oxidation state validation result."""
    success: bool = True
    formula: str
    oxidation_states_guessed: bool
    structure_is_valid: bool
    site_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    validity_percentage: float
    error: Optional[str] = None


def _parse_structure(structure_input: Union[str, Dict[str, Any]]) -> Structure:
    """Parse structure from various input formats."""
    if isinstance(structure_input, str):
        from io import StringIO
        parser = CifParser(StringIO(structure_input))
        structure = parser.parse_structures()[0]
    elif isinstance(structure_input, dict):
        # Check for PyMatGen format (has 'lattice' and 'sites')
        if "lattice" in structure_input and "sites" in structure_input:
            structure = Structure.from_dict(structure_input)
        # Check for ASE/Chemeleon format (has 'cell', 'positions', 'numbers' or 'symbols')
        elif "cell" in structure_input and "positions" in structure_input:
            # Convert from ASE/Chemeleon format to PyMatGen Structure
            from pymatgen.core import Lattice

            cell = structure_input["cell"]
            positions = structure_input["positions"]

            # Get atomic numbers or symbols
            if "numbers" in structure_input:
                species = structure_input["numbers"]
            elif "symbols" in structure_input:
                species = structure_input["symbols"]
            else:
                raise ValueError("Structure dict must contain either 'numbers' or 'symbols'")

            # Create PyMatGen lattice and structure
            lattice = Lattice(cell)
            structure = Structure(
                lattice=lattice,
                species=species,
                coords=positions,
                coords_are_cartesian=True
            )
        else:
            raise ValueError(
                "Structure dict must contain either:\n"
                "  - 'lattice' and 'sites' keys (PyMatGen format), or\n"
                "  - 'cell', 'positions', and 'numbers'/'symbols' keys (ASE/Chemeleon format)"
            )
    else:
        raise ValueError(f"Unsupported structure input type: {type(structure_input)}")
    return structure


def _guess_coordination_geometry(cn: int) -> str:
    """Guess coordination geometry from coordination number."""
    geometries = {
        2: "linear",
        3: "trigonal planar",
        4: "tetrahedral or square planar",
        5: "trigonal bipyramidal or square pyramidal",
        6: "octahedral",
        7: "pentagonal bipyramidal or capped octahedral",
        8: "cubic or square antiprismatic",
        9: "tricapped trigonal prismatic",
        12: "cuboctahedral or anticuboctahedral"
    }
    return geometries.get(cn, f"{cn}-coordinate")


class PyMatgenAnalyzer:
    """PyMatgen structure analysis tools."""

    @staticmethod
    def analyze_space_group(
        structure_input: Union[str, Dict[str, Any]],
        symprec: float = 0.1,
        angle_tolerance: float = 5.0
    ) -> SpaceGroupResult:
        """
        Analyze the space group and symmetry of a crystal structure.

        Args:
            structure_input: CIF string or pymatgen structure dict
            symprec: Symmetry precision for distance tolerance (in Angstrom)
            angle_tolerance: Angle tolerance for symmetry finding (in degrees)

        Returns:
            Structured space group analysis result
        """
        try:
            structure = _parse_structure(structure_input)

            analyzer = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tolerance)

            space_group_symbol = analyzer.get_space_group_symbol()
            space_group_number = analyzer.get_space_group_number()
            point_group = analyzer.get_point_group_symbol()
            crystal_system = analyzer.get_crystal_system()
            hall_symbol = analyzer.get_hall()

            primitive_structure = analyzer.get_primitive_standard_structure()
            conventional_structure = analyzer.get_conventional_standard_structure()
            symmetry_ops = analyzer.get_symmetry_operations()

            return SpaceGroupResult(
                success=True,
                space_group_symbol=space_group_symbol,
                space_group_number=space_group_number,
                point_group=point_group,
                crystal_system=crystal_system,
                hall_symbol=hall_symbol,
                original_formula=structure.composition.reduced_formula,
                original_num_atoms=len(structure),
                primitive_formula=primitive_structure.composition.reduced_formula,
                primitive_num_atoms=len(primitive_structure),
                num_symmetry_ops=len(symmetry_ops),
                lattice_a=conventional_structure.lattice.a,
                lattice_b=conventional_structure.lattice.b,
                lattice_c=conventional_structure.lattice.c,
                lattice_alpha=conventional_structure.lattice.alpha,
                lattice_beta=conventional_structure.lattice.beta,
                lattice_gamma=conventional_structure.lattice.gamma,
                volume=conventional_structure.lattice.volume,
                symmetrized_cif=conventional_structure.to(fmt="cif"),
                primitive_cif=primitive_structure.to(fmt="cif")
            )

        except Exception as e:
            logger.error(f"Space group analysis failed: {e}")
            return SpaceGroupResult(
                success=False,
                space_group_symbol="P1",
                space_group_number=1,
                point_group="1",
                crystal_system="triclinic",
                hall_symbol="P 1",
                original_formula="unknown",
                original_num_atoms=0,
                primitive_formula="unknown",
                primitive_num_atoms=0,
                num_symmetry_ops=0,
                lattice_a=0.0,
                lattice_b=0.0,
                lattice_c=0.0,
                lattice_alpha=0.0,
                lattice_beta=0.0,
                lattice_gamma=0.0,
                volume=0.0,
                error=str(e)
            )

    @staticmethod
    def analyze_coordination(
        structure_input: Union[str, Dict[str, Any]],
        site_index: Optional[int] = None
    ) -> CoordinationResult:
        """
        Analyze coordination environment of sites in a structure.

        Args:
            structure_input: CIF string or pymatgen structure dict
            site_index: Specific site index to analyze (None = all sites)

        Returns:
            Structured coordination analysis result
        """
        try:
            structure = _parse_structure(structure_input)
            voronoi_nn = VoronoiNN()

            if site_index is not None:
                sites_to_analyze = [site_index]
            else:
                sites_to_analyze = range(len(structure))

            coordination_data = []

            for idx in sites_to_analyze:
                site = structure[idx]
                nn_info = voronoi_nn.get_nn_info(structure, idx)
                cn = len(nn_info)

                coordinated_sites = [info['site'] for info in nn_info]
                bond_lengths = []
                coordinating_elements = {}

                for coord_site in coordinated_sites:
                    distance = site.distance(coord_site)
                    bond_lengths.append(distance)

                    element = coord_site.specie.symbol
                    if element not in coordinating_elements:
                        coordinating_elements[element] = []
                    coordinating_elements[element].append(distance)

                avg_bond_lengths = {
                    elem: float(np.mean(distances))
                    for elem, distances in coordinating_elements.items()
                }

                coordination_data.append({
                    "site_index": idx,
                    "element": site.specie.symbol,
                    "fractional_coords": site.frac_coords.tolist(),
                    "coordination_number": cn,
                    "bond_lengths": {
                        "min": float(min(bond_lengths)) if bond_lengths else 0,
                        "max": float(max(bond_lengths)) if bond_lengths else 0,
                        "mean": float(np.mean(bond_lengths)) if bond_lengths else 0,
                        "by_element": avg_bond_lengths
                    },
                    "coordinating_elements": list(coordinating_elements.keys()),
                    "geometry": _guess_coordination_geometry(cn)
                })

            all_cns = [d["coordination_number"] for d in coordination_data]

            return CoordinationResult(
                success=True,
                formula=structure.composition.reduced_formula,
                num_sites=len(structure),
                sites_analyzed=len(coordination_data),
                average_coordination=float(np.mean(all_cns)) if all_cns else 0.0,
                coordination_data=coordination_data
            )

        except Exception as e:
            logger.error(f"Coordination analysis failed: {e}")
            return CoordinationResult(
                success=False,
                formula="unknown",
                num_sites=0,
                sites_analyzed=0,
                average_coordination=0.0,
                error=str(e)
            )

    @staticmethod
    def validate_oxidation_states(
        structure_input: Union[str, Dict[str, Any]],
        oxidation_states: Optional[Dict[str, float]] = None
    ) -> OxidationStateResult:
        """
        Validate oxidation states using bond valence analysis.

        Args:
            structure_input: CIF string or pymatgen structure dict
            oxidation_states: Optional dict of element: oxidation_state

        Returns:
            Structured oxidation state validation result
        """
        try:
            structure = _parse_structure(structure_input)

            if oxidation_states:
                structure.add_oxidation_state_by_element(oxidation_states)

            if not any(hasattr(site.specie, "oxi_state") for site in structure):
                try:
                    structure.add_oxidation_state_by_guess()
                    guessed = True
                except Exception:
                    return OxidationStateResult(
                        success=False,
                        formula=structure.composition.reduced_formula,
                        oxidation_states_guessed=False,
                        structure_is_valid=False,
                        validity_percentage=0.0,
                        error="Could not determine oxidation states"
                    )
            else:
                guessed = False

            bv_analyzer = BVAnalyzer()

            try:
                bv_sum = bv_analyzer.get_valences(structure)
                is_valid = bv_analyzer.get_oxi_state_decorated_structure(structure) is not None
            except Exception as e:
                logger.warning(f"BV analysis warning: {e}")
                bv_sum = None
                is_valid = False

            site_results = []
            for i, site in enumerate(structure):
                ox_state = getattr(site.specie, "oxi_state", None)
                bv_value = bv_sum[i] if bv_sum is not None else None

                site_results.append({
                    "site_index": i,
                    "element": site.specie.element.symbol,
                    "assigned_oxidation_state": ox_state,
                    "bond_valence_sum": float(bv_value) if bv_value else None,
                    "difference": float(abs(ox_state - bv_value)) if (ox_state and bv_value) else None,
                    "is_reasonable": abs(ox_state - bv_value) < 0.5 if (ox_state and bv_value) else None
                })

            reasonable_sites = [s for s in site_results if s["is_reasonable"]]
            validity = (len(reasonable_sites) / len(site_results) * 100) if site_results else 0.0

            return OxidationStateResult(
                success=True,
                formula=structure.composition.reduced_formula,
                oxidation_states_guessed=guessed,
                structure_is_valid=is_valid,
                site_analysis=site_results,
                validity_percentage=validity
            )

        except Exception as e:
            logger.error(f"Oxidation state validation failed: {e}")
            return OxidationStateResult(
                success=False,
                formula="unknown",
                oxidation_states_guessed=False,
                structure_is_valid=False,
                validity_percentage=0.0,
                error=str(e)
            )
