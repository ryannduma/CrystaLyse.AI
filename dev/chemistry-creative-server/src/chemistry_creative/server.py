"""
Creative Chemistry MCP Server
Fast exploration mode with Chemeleon and MACE (no SMACT for speed).

Tools: Chemeleon, MACE, PyMatgen (no composition validation)
Features: Fast structure prediction, energy calculations, basic visualization
Optimized for rapid exploration of materials space.
"""

import logging
import json
from typing import List, Dict, Any, Optional
import numpy as np
import warnings
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from datetime import datetime
from ase.io import write as ase_write
from ase import Atoms

# Suppress e3nn warning
warnings.filterwarnings('ignore', category=UserWarning, module='e3nn',
                       message='.*TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD.*')

# CLEAN IMPORTS - No sys.path manipulation!
from crystalyse.tools.chemeleon import ChemeleonPredictor
from crystalyse.tools.mace import MACECalculator
from crystalyse.tools.pymatgen import PyMatgenAnalyzer
from crystalyse.tools.models import (
    PredictionResult,
    EnergyResult,
    CrystalStructure
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("chemistry-creative")

# Initialize tool instances
chemeleon_predictor = ChemeleonPredictor()
mace_calculator = MACECalculator()
pymatgen_analyzer = PyMatgenAnalyzer()

logger.info("Chemistry Creative Server initialized with Chemeleon and MACE")


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
            return repr(obj)


def structure_dict_to_cif(structure_dict: Dict[str, Any]) -> str:
    """Convert structure dictionary to CIF format string."""
    try:
        # Extract fields
        numbers = structure_dict['numbers']
        positions = structure_dict['positions']
        cell = structure_dict['cell']
        pbc = structure_dict.get('pbc', [True, True, True])

        # Ensure proper types
        if isinstance(numbers, np.ndarray):
            numbers = numbers.tolist()
        if isinstance(positions, np.ndarray):
            positions = positions.tolist()
        if isinstance(cell, np.ndarray):
            cell = cell.tolist()

        atoms = Atoms(
            numbers=numbers,
            positions=positions,
            cell=cell,
            pbc=pbc
        )

        # Write to temporary file and read back
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.cif', delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        try:
            ase_write(tmp_filename, atoms, format='cif')
            with open(tmp_filename, 'r') as f:
                cif_content = f.read()
            return cif_content
        finally:
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)
    except Exception as e:
        logger.error(f"Error converting structure to CIF: {e}")
        return ""


def _create_session_directory() -> Path:
    """Create session directory for output files."""
    try:
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        output_dir = Path.cwd() / "all-runtime-output" / session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created session directory: {output_dir}")
        return output_dir
    except Exception as e:
        logger.error(f"Failed to create session directory: {e}")
        output_dir = Path.cwd() / "all-runtime-output"
        output_dir.mkdir(exist_ok=True)
        return output_dir


# --- CHEMELEON TOOLS ---

@mcp.tool()
async def generate_crystal_structure(
    formula: str,
    num_samples: int = 3,
    prefer_gpu: bool = True
) -> dict[str, Any]:
    """
    Generate crystal structures using Chemeleon CSP (fast creative mode).

    Args:
        formula: Chemical formula (e.g., "NaCl", "LiCoO2")
        num_samples: Number of structure candidates to generate
        prefer_gpu: Use GPU if available

    Returns:
        Structure prediction results with multiple candidates
    """
    logger.info(f"Generating {num_samples} structures for {formula}")

    try:
        result = await chemeleon_predictor.predict_structure(
            formula=formula,
            num_samples=num_samples,
            prefer_gpu=prefer_gpu
        )

        return make_json_serializable({
            "success": result.success,
            "formula": result.formula,
            "structures": [
                {
                    "formula": s.formula,
                    "cell": s.cell,
                    "positions": s.positions,
                    "numbers": s.numbers,
                    "symbols": s.symbols,
                    "volume": s.volume,
                    "confidence": s.confidence
                }
                for s in result.predicted_structures
            ],
            "computation_time": result.computation_time,
            "method": result.method,
            "checkpoint_used": result.checkpoint_used,
            "error": result.error
        })
    except Exception as e:
        logger.error(f"Chemeleon structure generation failed: {e}")
        return {
            "success": False,
            "formula": formula,
            "structures": [],
            "error": str(e)
        }


# --- MACE TOOLS ---

@mcp.tool()
async def calculate_formation_energy(
    cif_content: str,
    prefer_gpu: bool = True
) -> dict[str, Any]:
    """
    Calculate formation energy using MACE (fast creative mode).

    Args:
        cif_content: Crystal structure in CIF format
        prefer_gpu: Use GPU if available

    Returns:
        Formation energy results
    """
    logger.info("Calculating formation energy with MACE")

    try:
        result = await mace_calculator.calculate_energy(
            cif_content=cif_content,
            prefer_gpu=prefer_gpu
        )

        return make_json_serializable({
            "success": result.success,
            "formula": result.formula,
            "formation_energy_per_atom": result.formation_energy_per_atom,
            "total_energy": result.total_energy,
            "num_atoms": result.num_atoms,
            "uncertainty": result.uncertainty,
            "computation_time": result.computation_time,
            "model_used": result.model_used,
            "error": result.error
        })
    except Exception as e:
        logger.error(f"MACE energy calculation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# --- COMPREHENSIVE CREATIVE DISCOVERY ---

@mcp.tool()
async def creative_discovery_pipeline(
    compositions: list[str],
    structures_per_composition: int = 3,
    calculate_energies: bool = True,
    prefer_gpu: bool = True
) -> dict[str, Any]:
    """
    Fast creative discovery pipeline: Chemeleon structure generation + MACE energies.

    No SMACT validation, no hull calculations - optimized for speed.

    Args:
        compositions: List of chemical formulas
        structures_per_composition: Structures to generate per composition
        calculate_energies: Calculate formation energies with MACE
        prefer_gpu: Use GPU if available

    Returns:
        Discovery results with structures and energies
    """
    logger.info(f"Creative discovery for {len(compositions)} compositions")

    session_dir = _create_session_directory()
    results = {
        "compositions": compositions,
        "mode": "creative",
        "structures": {},
        "energies": {},
        "cif_files": {},
        "summary": {
            "total_compositions": len(compositions),
            "structures_generated": 0,
            "energies_calculated": 0,
            "failed_compositions": []
        }
    }

    for composition in compositions:
        try:
            # Generate structures
            struct_result = await generate_crystal_structure(
                formula=composition,
                num_samples=structures_per_composition,
                prefer_gpu=prefer_gpu
            )

            if struct_result["success"]:
                results["structures"][composition] = struct_result["structures"]
                results["summary"]["structures_generated"] += len(struct_result["structures"])

                # Calculate energies if requested
                if calculate_energies and struct_result["structures"]:
                    composition_energies = []

                    for idx, structure in enumerate(struct_result["structures"]):
                        # Convert to CIF
                        cif_content = structure_dict_to_cif(structure)

                        if cif_content:
                            # Save CIF
                            cif_filename = f"{composition}_structure_{idx}.cif"
                            cif_path = session_dir / cif_filename
                            with open(cif_path, 'w') as f:
                                f.write(cif_content)

                            results["cif_files"][f"{composition}_{idx}"] = str(cif_path)

                            # Calculate energy
                            energy_result = await calculate_formation_energy(
                                cif_content=cif_content,
                                prefer_gpu=prefer_gpu
                            )

                            if energy_result["success"]:
                                composition_energies.append(energy_result)
                                results["summary"]["energies_calculated"] += 1

                    results["energies"][composition] = composition_energies
            else:
                results["summary"]["failed_compositions"].append(composition)

        except Exception as e:
            logger.error(f"Failed to process {composition}: {e}")
            results["summary"]["failed_compositions"].append(composition)

    # Add performance metrics
    results["summary"]["session_directory"] = str(session_dir)
    results["summary"]["optimization_notes"] = [
        "No SMACT composition validation (creative mode)",
        "No energy above hull calculations",
        f"GPU acceleration: {'enabled' if prefer_gpu else 'disabled'}"
    ]

    logger.info(f"Creative discovery complete: {results['summary']['structures_generated']} structures, "
                f"{results['summary']['energies_calculated']} energies")

    return make_json_serializable(results)


# --- COMPREHENSIVE MATERIALS ANALYSIS (Creative Mode Compatible) ---

@mcp.tool()
async def comprehensive_materials_analysis(
    compositions: list[str],
    mode: str = "creative",
    structures_per_composition: int = 3,
    calculate_energies_flag: bool = True,
    temperature_range: str = "ambient",
    applications: str = "general",
    prefer_gpu: bool = True
) -> dict[str, Any]:
    """
    Comprehensive materials analysis for creative mode.

    Compatible with unified server interface but optimized for speed.

    Args:
        compositions: List of chemical formulas
        mode: Analysis mode (should be "creative")
        structures_per_composition: Structures per composition
        calculate_energies_flag: Calculate energies with MACE
        temperature_range: Temperature info (metadata)
        applications: Application info (metadata)
        prefer_gpu: Use GPU if available

    Returns:
        Analysis results matching unified server format
    """
    logger.info(f"Comprehensive creative analysis: {len(compositions)} compositions")

    # Call creative discovery pipeline
    results = await creative_discovery_pipeline(
        compositions=compositions,
        structures_per_composition=structures_per_composition,
        calculate_energies=calculate_energies_flag,
        prefer_gpu=prefer_gpu
    )

    # Add metadata to match unified server format
    results["analysis_mode"] = "creative"
    results["server_type"] = "chemistry-creative"
    results["temperature_range"] = temperature_range
    results["target_applications"] = applications

    return results


def main():
    """Run the creative chemistry MCP server."""
    logger.info("Starting Chemistry Creative Server...")
    logger.info("Optimized for fast exploration with Chemeleon + MACE")
    logger.info("No SMACT validation - creative mode only")
    mcp.run()


if __name__ == "__main__":
    main()
