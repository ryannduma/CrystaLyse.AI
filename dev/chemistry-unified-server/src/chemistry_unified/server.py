"""
Unified Chemistry MCP Server
Integrates all chemistry tools with clean modular architecture.

Tools: SMACT, Chemeleon, MACE, PyMatgen, Visualization
Features: Dopant Prediction, Advanced Screening, Stress/Strain, Foundation Models

All tools use clean imports without sys.path manipulation.
Total Tools: 20 MCP endpoints
"""

import logging
import json
from typing import List, Dict, Any, Union, Optional
import numpy as np
import re
import warnings
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from datetime import datetime

# Suppress e3nn warning about TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD
# This warning appears when MACE loads e3nn components
warnings.filterwarnings('ignore', category=UserWarning, module='e3nn',
                       message='.*TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD.*')

# CLEAN IMPORTS - No sys.path manipulation!
from crystalyse.tools.smact import (
    SMACTValidator,
    SMACTCalculator,
    SMACTDopantPredictor,
    SMACTScreener
)
from crystalyse.tools.chemeleon import ChemeleonPredictor
from crystalyse.tools.mace import (
    MACECalculator,
    MACEStressCalculator,
    MACEFoundationModels
)
from crystalyse.tools.pymatgen import PyMatgenAnalyzer, PhaseDiagramAnalyzer
from crystalyse.tools.visualization import CrystaLyseVisualizer
from crystalyse.tools.models import (
    ValidationResult,
    PredictionResult,
    EnergyResult,
    StabilityResult,
    BandGapResult,
    SpaceGroupResult,
    EnergyAboveHullResult,
    VisualizationResult,
    DopantPredictionResult,
    CompositionValidityResult,
    MLRepresentationResult,
    CompositionFilterResult,
    StressResult,
    EOSResult,
    FoundationModelListResult
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore", message=".*Pauling electronegativity.*")

# Initialize FastMCP server
mcp = FastMCP("Chemistry Unified")

# Initialize tool instances
smact_validator = SMACTValidator()
smact_calculator = SMACTCalculator()
chemeleon_predictor = ChemeleonPredictor()
mace_calculator = MACECalculator()
pymatgen_analyzer = PyMatgenAnalyzer()
phase_diagram_analyzer = PhaseDiagramAnalyzer()
visualizer = CrystaLyseVisualizer()

# --- Core Utility Functions ---

def make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format."""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        try:
            return str(obj)
        except:
            return f"<non-serializable: {type(obj).__name__}>"


# ===================================================================
# SMACT TOOLS - Now using modular implementation
# ===================================================================

@mcp.tool(description="Check if a chemical formula is valid - Use this FIRST before any other analysis to ensure the composition makes chemical sense")
def validate_composition(
    composition: str,
    use_pauling_test: bool = True,
    include_alloys: bool = True,
    oxidation_states_set: str = "icsd24"
) -> ValidationResult:
    """
    Validate chemical composition with structured output.

    Use this tool FIRST before attempting any other analysis. It checks:
    - Charge neutrality
    - Pauling electronegativity rules
    - Valid oxidation state combinations

    Args:
        composition: Chemical formula (e.g., "LiFePO4", "CaTiO3")
        use_pauling_test: Whether to apply Pauling electronegativity test
        include_alloys: Consider pure metals valid automatically
        oxidation_states_set: Which oxidation states to use

    Returns:
        Structured ValidationResult with full type information
    """
    logger.info(f"Validating composition: {composition}")
    result = smact_validator.validate_composition(
        composition,
        use_pauling_test=use_pauling_test,
        include_alloys=include_alloys,
        oxidation_states_set=oxidation_states_set
    )
    return result


@mcp.tool(description="Comprehensive stability analysis using SMACT")
def analyze_stability(
    composition: str,
    check_electronegativity: bool = True,
    electronegativity_threshold: float = 0.5
) -> StabilityResult:
    """
    Comprehensive stability analysis with robust electronegativity handling.

    Args:
        composition: Chemical formula (e.g., "LiFePO4", "CaTiO3")
        check_electronegativity: Whether to analyze electronegativity differences
        electronegativity_threshold: Minimum difference for ionic character

    Returns:
        Structured stability analysis result
    """
    logger.info(f"Analyzing stability: {composition}")
    result = smact_validator.analyze_stability(
        composition,
        check_electronegativity=check_electronegativity,
        electronegativity_threshold=electronegativity_threshold
    )
    return result


@mcp.tool(description="Predict band gap using Harrison's approach")
def predict_band_gap(composition: str) -> BandGapResult:
    """
    Predict band gap with robust electronegativity handling.

    Args:
        composition: Chemical formula

    Returns:
        Structured band gap prediction result
    """
    logger.info(f"Predicting band gap: {composition}")
    result = smact_calculator.predict_band_gap(composition)
    return result


# ===================================================================
# CHEMELEON TOOLS - Now using modular implementation
# ===================================================================

@mcp.tool(description="Generate crystal structure for a composition - Use AFTER validation to predict the most likely crystal structure and space group")
async def generate_crystal_csp(
    formulas: Union[str, List[str]],
    num_samples: int = 1,
    prefer_gpu: bool = True
) -> PredictionResult:
    """
    Generate crystal structures using Chemeleon CSP.

    Args:
        formulas: Chemical formula(s) to generate structures for
        num_samples: Number of structures to generate per formula
        prefer_gpu: If True, use GPU if available

    Returns:
        Structured prediction result with generated structures
    """
    if isinstance(formulas, str):
        formulas_list = [formulas]
    else:
        formulas_list = formulas

    logger.info(f"Generating structures for: {formulas_list}")

    # For simplicity, process first formula
    formula = formulas_list[0]
    result = await chemeleon_predictor.predict_structure(
        formula=formula,
        num_samples=num_samples,
        prefer_gpu=prefer_gpu
    )

    return result


# ===================================================================
# MACE TOOLS - Now using modular implementation
# ===================================================================

@mcp.tool(description="Calculate formation energy using MACE")
async def calculate_formation_energy(
    structure_dict: Dict[str, Any],
    model_type: str = "mace_mp",
    size: str = "medium"
) -> EnergyResult:
    """
    Calculate formation energy of a crystal from its constituent elements.

    Args:
        structure_dict: Crystal structure in dictionary format
        model_type: MACE model type to use
        size: Model size for foundation models

    Returns:
        Structured energy calculation result
    """
    logger.info(f"Calculating formation energy for structure")
    result = await mace_calculator.calculate_formation_energy(structure_dict)
    return result


@mcp.tool(description="Relax crystal structure to minimize energy")
async def relax_structure(
    structure_dict: Dict[str, Any],
    fmax: float = 0.01,
    steps: int = 500,
    optimizer: str = "BFGS"
) -> dict:
    """
    Relax structure to local energy minimum using MACE forces.

    Args:
        structure_dict: Initial crystal structure
        fmax: Maximum force convergence criterion (eV/Å)
        steps: Maximum optimization steps
        optimizer: Optimization algorithm ('BFGS', 'FIRE', 'LBFGS')

    Returns:
        Relaxation result with optimized structure
    """
    logger.info(f"Relaxing structure with {optimizer}")
    result = await mace_calculator.relax_structure(
        structure=structure_dict,
        fmax=fmax,
        steps=steps,
        optimizer=optimizer
    )
    return result.dict()


# ===================================================================
# PYMATGEN TOOLS - Now using modular implementation
# ===================================================================

@mcp.tool(description="Analyze space group and symmetry of crystal structure")
def analyze_space_group(
    structure_input: Union[str, Dict[str, Any]],
    symprec: float = 0.1,
    angle_tolerance: float = 5.0
) -> SpaceGroupResult:
    """
    Analyze space group and crystallographic symmetry.

    Args:
        structure_input: CIF string or structure dictionary
        symprec: Symmetry precision for space group detection
        angle_tolerance: Angle tolerance for symmetry operations

    Returns:
        Structured space group analysis result
    """
    logger.info(f"Analyzing space group")
    result = pymatgen_analyzer.analyze_space_group(
        structure_input=structure_input,
        symprec=symprec,
        angle_tolerance=angle_tolerance
    )
    return result


@mcp.tool(description="Calculate energy above hull for thermodynamic stability")
def calculate_energy_above_hull(
    composition: str,
    energy_per_atom: Optional[float] = None
) -> EnergyAboveHullResult:
    """
    Calculate energy above hull using Materials Project phase diagram.

    Args:
        composition: Chemical formula (e.g., "LiFePO4")
        energy_per_atom: Optional calculated energy per atom (eV/atom)

    Returns:
        Structured energy above hull result with stability assessment
    """
    logger.info(f"Calculating energy above hull for: {composition}")
    result = phase_diagram_analyzer.calculate_energy_above_hull(
        composition=composition,
        energy_per_atom=energy_per_atom
    )
    return result


@mcp.tool(description="Analyze coordination environment of atoms")
def analyze_coordination(
    structure_input: Union[str, Dict[str, Any]],
    method: str = "voronoi"
) -> dict:
    """
    Analyze coordination environment using Voronoi nearest neighbors.

    Args:
        structure_input: CIF string or structure dictionary
        method: Coordination analysis method (default: voronoi)

    Returns:
        Coordination analysis result
    """
    logger.info(f"Analyzing coordination environment")
    result = pymatgen_analyzer.analyze_coordination(
        structure_input=structure_input,
        method=method
    )
    return result.dict()


@mcp.tool(description="Validate oxidation states using bond valence analysis")
def validate_oxidation_states(
    structure_input: Union[str, Dict[str, Any]]
) -> dict:
    """
    Validate oxidation states using bond valence sum analysis.

    Args:
        structure_input: CIF string or structure dictionary

    Returns:
        Oxidation state validation result
    """
    logger.info(f"Validating oxidation states")
    result = pymatgen_analyzer.validate_oxidation_states(
        structure_input=structure_input
    )
    return result.dict()


# ===================================================================
# VISUALIZATION TOOLS - Now using modular implementation
# ===================================================================

@mcp.tool(description="Save crystal structure as CIF file")
def save_cif_file(
    cif_content: str,
    formula: str,
    output_dir: str,
    title: str = "Crystal Structure"
) -> VisualizationResult:
    """
    Save CIF file to output directory with caching.

    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save CIF file
        title: Title for the structure

    Returns:
        Structured visualization result
    """
    logger.info(f"Saving CIF file for {formula}")
    result = visualizer.save_cif_file(
        cif_content=cif_content,
        formula=formula,
        output_dir=output_dir,
        title=title
    )
    return result


@mcp.tool(description="Create comprehensive analysis suite directory")
def create_analysis_suite(
    cif_content: str,
    formula: str,
    output_dir: str,
    title: str = "Crystal Structure Analysis",
    color_scheme: str = "vesta"
) -> VisualizationResult:
    """
    Create analysis directory (full visualization via pymatviz server).

    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save analysis files
        title: Title for the analysis
        color_scheme: Color scheme for visualization

    Returns:
        Structured visualization result
    """
    logger.info(f"Creating analysis suite for {formula}")
    result = visualizer.create_analysis_suite(
        cif_content=cif_content,
        formula=formula,
        output_dir=output_dir,
        title=title,
        color_scheme=color_scheme
    )
    return result


# ===================================================================
# SMACT ADVANCED SCREENING - Phase 1.5
# ===================================================================

@mcp.tool(description="Fast SMACT validity check with metallicity and alloy support")
def smact_validate_fast(
    composition: str,
    use_pauling_test: bool = True,
    include_alloys: bool = True,
    check_metallicity: bool = False,
    metallicity_threshold: float = 0.7,
    oxidation_states_set: str = "icsd24"
) -> CompositionValidityResult:
    """
    Fast SMACT validity check for compositions.

    Args:
        composition: Chemical formula (e.g., "LiFePO4")
        use_pauling_test: Apply Pauling electronegativity test
        include_alloys: Consider pure metals valid automatically
        check_metallicity: Consider high metallicity compositions valid
        metallicity_threshold: Threshold for metallicity validity (0-1)
        oxidation_states_set: Oxidation state dataset ('icsd24', 'smact14', etc.)

    Returns:
        Structured validity result
    """
    logger.info(f"Fast SMACT validation for: {composition}")
    result = SMACTScreener.validate_composition(
        composition=composition,
        use_pauling_test=use_pauling_test,
        include_alloys=include_alloys,
        check_metallicity=check_metallicity,
        metallicity_threshold=metallicity_threshold,
        oxidation_states_set=oxidation_states_set
    )
    return result


@mcp.tool(description="Generate ML-compatible composition vector (103 elements)")
def generate_ml_representation(
    composition: str
) -> MLRepresentationResult:
    """
    Generate 103-element ML vector for a composition.

    The vector represents elemental composition normalized to sum to 1.
    Useful for machine learning models.

    Args:
        composition: Chemical formula (e.g., "Li2O")

    Returns:
        Structured ML representation with 103-element vector
    """
    logger.info(f"Generating ML representation for: {composition}")
    result = SMACTScreener.generate_ml_representation(
        composition=composition
    )
    return result


@mcp.tool(description="Filter and enumerate valid compositions for elements")
def filter_compositions(
    elements: List[str],
    threshold: int = 8,
    oxidation_states_set: str = "icsd24"
) -> CompositionFilterResult:
    """
    Generate all valid compositions for a set of elements.

    Args:
        elements: List of element symbols (e.g., ["Li", "Fe", "P", "O"])
        threshold: Maximum stoichiometry coefficient
        oxidation_states_set: Oxidation state dataset to use

    Returns:
        Structured result with all valid compositions
    """
    logger.info(f"Filtering compositions for: {elements}")
    result = SMACTScreener.filter_compositions(
        elements=elements,
        threshold=threshold,
        oxidation_states_set=oxidation_states_set
    )
    return result


# ===================================================================
# SMACT DOPANT PREDICTION - Phase 1.5
# ===================================================================

@mcp.tool(description="Predict n-type and p-type dopants for materials")
def predict_dopants(
    species: List[str],
    composition: str,
    num_dopants: int = 5,
    embedding: str = "skipspecies"
) -> DopantPredictionResult:
    """
    Predict dopants for semiconductor design and property tuning.

    Args:
        species: List of species with oxidation states (e.g., ["Li+", "Fe3+", "O2-"])
        composition: Chemical formula for reference
        num_dopants: Number of dopant suggestions per category
        embedding: Embedding method ('skipspecies', 'M3GNet-MP-2023.11.1-oxi-Eform',
                   'M3GNet-MP-2023.11.1-oxi-band_gap')

    Returns:
        Structured dopant predictions with n-type/p-type suggestions
    """
    logger.info(f"Predicting dopants for: {composition}")
    result = SMACTDopantPredictor.predict_dopants(
        species=species,
        composition=composition,
        num_dopants=num_dopants,
        embedding=embedding
    )
    return result


# ===================================================================
# MACE STRESS/STRAIN - Phase 1.5
# ===================================================================

@mcp.tool(description="Calculate stress tensor for mechanical property prediction")
def calculate_stress(
    structure: Dict[str, Any],
    model_type: str = "mace_mp",
    size: str = "medium",
    device: str = "auto"
) -> StressResult:
    """
    Calculate full stress tensor and derived mechanical properties.

    Args:
        structure: Structure dictionary with numbers, positions, cell
        model_type: MACE model type ('mace_mp', 'mace_off', or path)
        size: Model size ('small', 'medium', 'large', 'medium-mpa-0', etc.)
        device: Compute device ('auto', 'cpu', 'cuda')

    Returns:
        Stress tensor, pressure, von Mises stress, max shear stress
    """
    logger.info(f"Calculating stress tensor")
    result = MACEStressCalculator.calculate_stress(
        structure=structure,
        model_type=model_type,
        size=size,
        device=device
    )
    return result


@mcp.tool(description="Fit equation of state for bulk modulus calculation")
def fit_equation_of_state(
    structure: Dict[str, Any],
    eos_type: str = "birchmurnaghan",
    strain_range: float = 0.05,
    n_points: int = 7,
    model_type: str = "mace_mp",
    size: str = "medium"
) -> EOSResult:
    """
    Fit equation of state by calculating energy at multiple volumes.

    Args:
        structure: Structure dictionary
        eos_type: EOS type ('birchmurnaghan', 'murnaghan', 'vinet')
        strain_range: Strain range (+/-)
        n_points: Number of volume points
        model_type: MACE model type
        size: Model size

    Returns:
        EOS fitting result with bulk modulus and equilibrium properties
    """
    logger.info(f"Fitting equation of state ({eos_type})")
    result = MACEStressCalculator.fit_equation_of_state(
        structure=structure,
        eos_type=eos_type,
        strain_range=strain_range,
        n_points=n_points,
        model_type=model_type,
        size=size
    )
    return result


# ===================================================================
# MACE FOUNDATION MODELS - Phase 1.5
# ===================================================================

@mcp.tool(description="List available MACE foundation models")
def list_foundation_models() -> FoundationModelListResult:
    """
    List all available MACE foundation models with metadata.

    Returns:
        Structured list of models with descriptions, training data, licenses
    """
    logger.info("Listing available MACE foundation models")
    result = MACEFoundationModels.list_models()
    return result


# ===================================================================
# SERVER INFO
# ===================================================================

@mcp.tool(description="Get information about the unified server")
def get_server_info() -> Dict[str, Any]:
    """
    Get information about available tools and server status.

    Returns:
        Server information and capabilities
    """
    return {
        "server_name": "Chemistry Unified",
        "version": "2.0.0",
        "architecture": "modular",
        "path_manipulation": False,
        "structured_output": True,
        "error_handling": True,
        "total_tools": 20,
        "tool_categories": {
            "smact": {
                "enabled": True,
                "tools": [
                    "validate_composition",
                    "analyze_stability",
                    "predict_band_gap",
                    "smact_validate_fast",
                    "generate_ml_representation",
                    "filter_compositions",
                    "predict_dopants"
                ]
            },
            "chemeleon": {
                "enabled": True,
                "tools": ["generate_crystal_csp"]
            },
            "mace": {
                "enabled": True,
                "tools": [
                    "calculate_formation_energy",
                    "relax_structure",
                    "calculate_stress",
                    "fit_equation_of_state",
                    "list_foundation_models"
                ]
            },
            "pymatgen": {
                "enabled": True,
                "tools": [
                    "analyze_space_group",
                    "calculate_energy_above_hull",
                    "analyze_coordination",
                    "validate_oxidation_states"
                ]
            },
            "visualization": {
                "enabled": True,
                "tools": ["save_cif_file", "create_analysis_suite"]
            }
        },
        "capabilities": {
            "smact_validation": True,
            "smact_dopant_prediction": True,
            "smact_advanced_screening": True,
            "chemeleon_prediction": True,
            "mace_energy": True,
            "mace_relaxation": True,
            "mace_stress": True,
            "mace_eos": True,
            "mace_foundation_models": True,
            "pymatgen_analysis": True,
            "visualization": True
        },
        "phase_1_5_features": [
            "Dopant prediction (n-type/p-type)",
            "Fast SMACT screening with metallicity",
            "ML representation generation",
            "Composition filtering",
            "Stress tensor calculations",
            "Equation of state fitting",
            "Foundation model support (8 pre-trained models)"
        ],
        "improvements": [
            "No sys.path manipulation",
            "Pydantic structured output",
            "Comprehensive error handling",
            "Modular architecture",
            "Type-safe interfaces",
            "All 5 tool categories + advanced features integrated"
        ]
    }


if __name__ == "__main__":
    # Run the server
    mcp.run()
