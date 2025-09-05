"""
PyMatgen MCP Server for Materials Analysis
Provides tools for space group analysis, phase diagram calculations,
and other materials science computations.
"""

import logging
import json
import gzip
import pickle
import os
import warnings
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import sys

from mcp.server.fastmcp import FastMCP
from pymatgen.core import Structure, Composition
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
from pymatgen.analysis.bond_valence import BVAnalyzer
from pymatgen.analysis.local_env import VoronoiNN
from pymatgen.io.cif import CifParser
import numpy as np

# Enhanced error handling utilities
def make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format."""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.complexfloating):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        try:
            return str(obj)
        except:
            return f"<non-serializable: {type(obj).__name__}>"

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """JSON dumps with automatic serialization fixing."""
    try:
        return json.dumps(obj, **kwargs)
    except (TypeError, ValueError):
        fixed_obj = make_json_serializable(obj)
        return json.dumps(fixed_obj, **kwargs)

def enhance_error_handling(func):
    """Decorator to add comprehensive error handling to PyMatgen functions."""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # Ensure result is JSON serializable
            if isinstance(result, dict):
                result = make_json_serializable(result)
                # Add success metadata if not already present
                if "success" not in result:
                    result["success"] = True
                result["error_handling"] = "enhanced"
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "function": func.__name__,
                "error_handling": "enhanced",
                "error_type": type(e).__name__
            }
    return wrapper

# Suppress warnings
warnings.filterwarnings("ignore", message=".*Pauling electronegativity.*Setting to NaN.*")
warnings.filterwarnings("ignore", message=".*No Pauling electronegativity.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pymatgen")

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize server
mcp = FastMCP("pymatgen-mcp")

# Load pre-computed phase diagram
PPD_PATH = None
PPD_DATA = None

# Try to find the phase diagram file
possible_paths = [
    "/home/ryan/mycrystalyse/CrystaLyse.AI/ppd-mp_all_entries_uncorrected_250409.pkl.gz",
    Path(__file__).parent.parent.parent.parent.parent / "ppd-mp_all_entries_uncorrected_250409.pkl.gz",
    Path.home() / "mycrystalyse/CrystaLyse.AI/ppd-mp_all_entries_uncorrected_250409.pkl.gz"
]

for path in possible_paths:
    if os.path.exists(str(path)):
        PPD_PATH = str(path)
        break

if PPD_PATH:
    try:
        with gzip.open(PPD_PATH, "rb") as f:
            PPD_DATA = pickle.load(f)
        logger.info(f"Loaded phase diagram with {len(PPD_DATA.all_entries)} entries from {PPD_PATH}")
    except Exception as e:
        logger.error(f"Failed to load phase diagram from {PPD_PATH}: {e}")
        PPD_DATA = None
else:
    logger.warning("Phase diagram file not found. Energy above hull calculations will not be available.")


def _parse_structure(structure_input: Union[str, Dict[str, Any]]) -> Structure:
    """
    Parse structure from various input formats.
    
    Args:
        structure_input: CIF string or pymatgen structure dict
        
    Returns:
        pymatgen Structure object
    """
    if isinstance(structure_input, str):
        # Assume it's a CIF string
        from io import StringIO
        parser = CifParser(StringIO(structure_input))
        structure = parser.parse_structures()[0]
    elif isinstance(structure_input, dict):
        # Try to create from dict
        if "lattice" in structure_input:
            structure = Structure.from_dict(structure_input)
        else:
            raise ValueError("Structure dict must contain 'lattice' key")
    else:
        raise ValueError(f"Unsupported structure input type: {type(structure_input)}")
    
    return structure


@mcp.tool()
@enhance_error_handling
def analyze_space_group(
    structure_input: Union[str, Dict[str, Any]],
    symprec: float = 0.1,
    angle_tolerance: float = 5.0
) -> Dict[str, Any]:
    """
    Analyze the space group and symmetry of a crystal structure.
    
    Args:
        structure_input: CIF string or pymatgen structure dict
        symprec: Symmetry precision for distance tolerance (in Angstrom)
        angle_tolerance: Angle tolerance for symmetry finding (in degrees)
        
    Returns:
        Dictionary with space group information and symmetrized structure
    """
    try:
        structure = _parse_structure(structure_input)
        
        # Create SpacegroupAnalyzer
        analyzer = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tolerance)
        
        # Get space group information
        space_group_symbol = analyzer.get_space_group_symbol()
        space_group_number = analyzer.get_space_group_number()
        point_group = analyzer.get_point_group_symbol()
        crystal_system = analyzer.get_crystal_system()
        hall_symbol = analyzer.get_hall()
        
        # Get symmetrized structure
        symmetrized_structure = analyzer.get_symmetrized_structure()
        
        # Get primitive and conventional cells
        primitive_structure = analyzer.get_primitive_standard_structure()
        conventional_structure = analyzer.get_conventional_standard_structure()
        
        # Get symmetry operations
        symmetry_ops = analyzer.get_symmetry_operations()
        
        result = {
            "success": True,
            "space_group": {
                "symbol": space_group_symbol,
                "number": space_group_number,
                "point_group": point_group,
                "crystal_system": crystal_system,
                "hall_symbol": hall_symbol
            },
            "cell_info": {
                "original_formula": structure.composition.reduced_formula,
                "original_num_atoms": len(structure),
                "primitive_formula": primitive_structure.composition.reduced_formula,
                "primitive_num_atoms": len(primitive_structure),
                "conventional_formula": conventional_structure.composition.reduced_formula,
                "conventional_num_atoms": len(conventional_structure),
                "is_primitive": len(structure) == len(primitive_structure)
            },
            "symmetry": {
                "num_symmetry_ops": len(symmetry_ops),
                "wyckoff_positions": symmetrized_structure.wyckoff_symbols,
                "equivalent_sites": [
                    {
                        "element": str(site.species_string),
                        "wyckoff": site.properties.get("wyckoff", ""),
                        "multiplicity": len([s for s in symmetrized_structure if s.species_string == site.species_string 
                                           and s.properties.get("wyckoff", "") == site.properties.get("wyckoff", "")])
                    }
                    for site in symmetrized_structure.sites
                    if site.properties.get("wyckoff", "") not in [s.properties.get("wyckoff", "") 
                                                                  for s in symmetrized_structure.sites[:symmetrized_structure.sites.index(site)]]
                ]
            },
            "lattice_parameters": {
                "a": conventional_structure.lattice.a,
                "b": conventional_structure.lattice.b,
                "c": conventional_structure.lattice.c,
                "alpha": conventional_structure.lattice.alpha,
                "beta": conventional_structure.lattice.beta,
                "gamma": conventional_structure.lattice.gamma,
                "volume": conventional_structure.lattice.volume
            },
            "symmetrized_cif": conventional_structure.to(fmt="cif"),
            "primitive_cif": primitive_structure.to(fmt="cif")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Space group analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
@enhance_error_handling
def calculate_energy_above_hull(
    composition: str,
    energy: float,
    per_atom: bool = True
) -> Dict[str, Any]:
    """
    Calculate the energy above the convex hull for a given composition and energy.
    
    Args:
        composition: Chemical formula (e.g., "Li2O", "NaCl")
        energy: Total energy or energy per atom (in eV)
        per_atom: Whether the provided energy is per atom (default: True)
        
    Returns:
        Dictionary with energy above hull and decomposition information
    """
    try:
        if PPD_DATA is None:
            return {
                "success": False,
                "error": "Phase diagram data not loaded. Cannot calculate energy above hull."
            }
        
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
        
        # Calculate energy above hull with error handling
        try:
            e_above_hull = PPD_DATA.get_e_above_hull(entry, allow_negative=True)
        except Exception as e:
            logger.warning(f"Failed to calculate energy above hull: {e}")
            e_above_hull = float('inf')  # Treat as very unstable
        
        # Get decomposition products with error handling
        try:
            decomp_products = PPD_DATA.get_decomposition(comp)
        except Exception as e:
            logger.warning(f"Failed to get decomposition products: {e}")
            decomp_products = {}
        
        # Find stable phases at this composition with error handling
        stable_entries = []
        try:
            for e in PPD_DATA.stable_entries:
                if e.composition.reduced_composition == comp.reduced_composition:
                    stable_entries.append({
                        "formula": e.composition.reduced_formula,
                        "energy_per_atom": e.energy_per_atom,
                        "entry_id": getattr(e, "entry_id", "unknown")
                    })
        except Exception as e:
            logger.warning(f"Failed to find stable phases: {e}")
            stable_entries = []
        
        result = {
            "success": True,
            "composition": composition,
            "energy_per_atom": energy_per_atom if per_atom else energy / comp.num_atoms,
            "energy_above_hull": e_above_hull,
            "stability": {
                "is_stable": e_above_hull <= 0,  
                "is_metastable": 0 < e_above_hull <= 0.2,  # 1-50 meV/atom
                "is_unstable": e_above_hull > 0.2
            },
            "decomposition": [
                {
                    "formula": phase.composition.reduced_formula,
                    "fraction": float(amount),
                    "energy_per_atom": phase.energy_per_atom
                }
                for phase, amount in decomp_products.items()
            ],
            "stable_phases_at_composition": stable_entries,
            "competing_phases": len(decomp_products),
            "phase_diagram_info": {
                "total_entries": len(PPD_DATA.all_entries),
                "stable_entries": len(PPD_DATA.stable_entries),
                "chemical_system": "-".join(sorted(set(el.symbol for el in comp.elements)))
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Energy above hull calculation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "composition": composition
        }


@mcp.tool()
@enhance_error_handling
def analyze_coordination(
    structure_input: Union[str, Dict[str, Any]],
    site_index: Optional[int] = None
) -> Dict[str, Any]:
    """
    Analyze coordination environment of sites in a structure.
    
    Args:
        structure_input: CIF string or pymatgen structure dict
        site_index: Specific site index to analyze (None = all sites)
        
    Returns:
        Dictionary with coordination analysis results
    """
    try:
        structure = _parse_structure(structure_input)
        
        # Initialize Voronoi nearest neighbor analyzer
        voronoi_nn = VoronoiNN()
        
        # Analyze sites
        if site_index is not None:
            sites_to_analyze = [site_index]
        else:
            sites_to_analyze = range(len(structure))
        
        coordination_data = []
        
        for idx in sites_to_analyze:
            site = structure[idx]
            
            # Get coordination info using VoronoiNN
            nn_info = voronoi_nn.get_nn_info(structure, idx)
            cn = len(nn_info)
            
            # Get coordinated sites from nn_info
            coordinated_sites = [info['site'] for info in nn_info]
            
            # Calculate bond lengths
            bond_lengths = []
            coordinating_elements = {}
            
            for coord_site in coordinated_sites:
                distance = site.distance(coord_site)
                bond_lengths.append(distance)
                
                element = coord_site.specie.symbol
                if element not in coordinating_elements:
                    coordinating_elements[element] = []
                coordinating_elements[element].append(distance)
            
            # Calculate average bond lengths by element
            avg_bond_lengths = {
                elem: np.mean(distances) 
                for elem, distances in coordinating_elements.items()
            }
            
            coordination_data.append({
                "site_index": idx,
                "element": site.specie.symbol,
                "fractional_coords": site.frac_coords.tolist(),
                "coordination_number": cn,
                "bond_lengths": {
                    "min": min(bond_lengths) if bond_lengths else 0,
                    "max": max(bond_lengths) if bond_lengths else 0,
                    "mean": np.mean(bond_lengths) if bond_lengths else 0,
                    "by_element": avg_bond_lengths
                },
                "coordinating_elements": list(coordinating_elements.keys()),
                "geometry": _guess_coordination_geometry(cn)
            })
        
        # Calculate statistics
        all_cns = [d["coordination_number"] for d in coordination_data]
        unique_elements = list(set(site.specie.symbol for site in structure))
        
        result = {
            "success": True,
            "formula": structure.composition.reduced_formula,
            "num_sites": len(structure),
            "sites_analyzed": len(coordination_data),
            "coordination_data": coordination_data,
            "statistics": {
                "average_coordination": np.mean(all_cns) if all_cns else 0,
                "coordination_numbers": list(set(all_cns)),
                "elements": unique_elements
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Coordination analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
@enhance_error_handling
def validate_oxidation_states(
    structure_input: Union[str, Dict[str, Any]],
    oxidation_states: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Validate oxidation states using bond valence analysis.
    
    Args:
        structure_input: CIF string or pymatgen structure dict
        oxidation_states: Optional dict of element: oxidation_state
        
    Returns:
        Dictionary with bond valence analysis results
    """
    try:
        structure = _parse_structure(structure_input)
        
        # Add oxidation states if provided
        if oxidation_states:
            structure.add_oxidation_state_by_element(oxidation_states)
        
        # Try to guess oxidation states if not provided
        if not any(hasattr(site.specie, "oxi_state") for site in structure):
            try:
                structure.add_oxidation_state_by_guess()
                guessed = True
            except Exception:
                return {
                    "success": False,
                    "error": "Could not determine oxidation states. Please provide them explicitly."
                }
        else:
            guessed = False
        
        # Perform bond valence analysis
        bv_analyzer = BVAnalyzer()
        
        try:
            bv_sum = bv_analyzer.get_valences(structure)
            is_valid = bv_analyzer.get_oxi_state_decorated_structure(structure) is not None
        except Exception as e:
            logger.warning(f"BV analysis warning: {e}")
            bv_sum = None
            is_valid = False
        
        # Extract results
        site_results = []
        for i, site in enumerate(structure):
            ox_state = getattr(site.specie, "oxi_state", None)
            bv_value = bv_sum[i] if bv_sum is not None else None
            
            site_results.append({
                "site_index": i,
                "element": site.specie.element.symbol,
                "assigned_oxidation_state": ox_state,
                "bond_valence_sum": bv_value,
                "difference": abs(ox_state - bv_value) if (ox_state and bv_value) else None,
                "is_reasonable": abs(ox_state - bv_value) < 0.5 if (ox_state and bv_value) else None
            })
        
        # Calculate statistics
        reasonable_sites = [s for s in site_results if s["is_reasonable"]]
        unreasonable_sites = [s for s in site_results if s["is_reasonable"] is False]
        
        result = {
            "success": True,
            "formula": structure.composition.reduced_formula,
            "oxidation_states_guessed": guessed,
            "structure_is_valid": is_valid,
            "site_analysis": site_results,
            "summary": {
                "total_sites": len(site_results),
                "reasonable_sites": len(reasonable_sites),
                "unreasonable_sites": len(unreasonable_sites),
                "validity_percentage": (len(reasonable_sites) / len(site_results) * 100) if site_results else 0
            },
            "oxidation_state_summary": {
                elem: ox_state 
                for elem, ox_state in (oxidation_states or {}).items()
            } if oxidation_states else {
                site.specie.element.symbol: getattr(site.specie, "oxi_state", None)
                for site in structure
                if hasattr(site.specie, "oxi_state")
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Oxidation state validation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


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


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check health of PyMatgen MCP server."""
    return {
        "server": "pymatgen-mcp",
        "status": "healthy",
        "pymatgen_version": "2023.x",  # Would need to import pymatgen.__version__
        "tools_available": [
            "analyze_space_group",
            "calculate_energy_above_hull",
            "analyze_coordination",
            "validate_oxidation_states"
        ],
        "phase_diagram_loaded": PPD_DATA is not None,
        "phase_diagram_entries": len(PPD_DATA.all_entries) if PPD_DATA else 0
    }


def main():
    """Main entry point for pymatgen-mcp-server."""
    logger.info("Starting PyMatgen MCP Server")
    logger.info(f"Phase diagram loaded: {PPD_DATA is not None}")
    if PPD_DATA:
        logger.info(f"Phase diagram contains {len(PPD_DATA.all_entries)} entries")
    mcp.run()

if __name__ == "__main__":
    main()