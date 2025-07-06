"""Creative Chemistry MCP Server integrating Chemeleon and MACE (no SMACT for faster exploration)"""

import asyncio
import logging
import json
import copy
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add parent directories to path for importing existing tools
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root / "oldmcpservers" / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "mace-mcp-server" / "src"))

from mcp.server.fastmcp import FastMCP
import io
from ase.io import read as ase_read, write as ase_write
from ase import Atoms
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialise creative server
mcp = FastMCP("chemistry-creative")

# Import Chemeleon and MACE tools only (no SMACT for creative mode)
try:
    from chemeleon_mcp.tools import generate_crystal_csp, analyse_structure
    CHEMELEON_AVAILABLE = True
    logger.info("Chemeleon tools loaded successfully")
except ImportError as e:
    logger.warning(f"Chemeleon tools not available: {e}")
    CHEMELEON_AVAILABLE = False

try:
    from mace_mcp.tools import (
        calculate_formation_energy,
        calculate_energy,
        relax_structure,
        suggest_substitutions,
        extract_descriptors_robust,
        adaptive_batch_calculation
    )
    MACE_AVAILABLE = True
    logger.info("MACE tools loaded successfully")
except ImportError as e:
    logger.warning(f"MACE tools not available: {e}")
    MACE_AVAILABLE = False

def structure_dict_to_cif(structure_dict: Dict[str, Any]) -> str:
    """Convert structure dictionary to CIF format string."""
    try:
        # Debug logging to understand the data types
        logger.debug(f"Structure dict keys: {list(structure_dict.keys())}")
        logger.debug(f"Type of numbers: {type(structure_dict.get('numbers'))}")
        logger.debug(f"Type of positions: {type(structure_dict.get('positions'))}")
        logger.debug(f"Type of cell: {type(structure_dict.get('cell'))}")
        
        # Handle potential data type issues
        def convert_field(field_value, field_name):
            """Convert field to proper format, handling various encodings."""
            if isinstance(field_value, (list, np.ndarray)):
                return field_value
            elif isinstance(field_value, bytes):
                logger.warning(f"{field_name} field is bytes - attempting to decode")
                try:
                    # Try JSON decoding
                    decoded = field_value.decode('utf-8')
                    return json.loads(decoded)
                except:
                    # Try direct eval as a fallback (careful with security)
                    import ast
                    return ast.literal_eval(decoded)
            elif isinstance(field_value, str):
                logger.warning(f"{field_name} field is string - attempting to parse")
                try:
                    return json.loads(field_value)
                except:
                    import ast
                    return ast.literal_eval(field_value)
            else:
                raise ValueError(f"Unexpected type for {field_name}: {type(field_value)}")
        
        # Convert fields
        numbers = convert_field(structure_dict['numbers'], 'numbers')
        positions = convert_field(structure_dict['positions'], 'positions')
        cell = convert_field(structure_dict['cell'], 'cell')
        pbc = structure_dict.get('pbc', [True, True, True])
        if not isinstance(pbc, list):
            pbc = convert_field(pbc, 'pbc')
        
        # Ensure numpy arrays are converted to lists for ASE
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
        
        # Use a temporary file instead of StringIO to avoid encoding issues
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cif', delete=False) as tmp_file:
            tmp_filename = tmp_file.name
        
        try:
            # Write to temporary file
            ase_write(tmp_filename, atoms, format='cif')
            
            # Read back the content
            with open(tmp_filename, 'r') as f:
                cif_content = f.read()
            
            return cif_content
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)
    except Exception as e:
        logger.error(f"Error converting structure to CIF: {e}")
        logger.error(f"Structure dict content: {structure_dict}")
        return ""

# ===== CREATIVE DISCOVERY PIPELINE =====

@mcp.tool()
async def creative_discovery_pipeline(
    compositions: List[str],
    structures_per_composition: int = 3,
    calculate_energies_flag: bool = True
) -> Dict[str, Any]:
    """
    Creative pipeline for fast exploration: Chemeleon + MACE (no SMACT validation).
    
    Args:
        compositions: List of chemical formulas
        structures_per_composition: Structures to generate per composition
        calculate_energies_flag: Whether to calculate energies with MACE
        
    Returns:
        Results with structure generation and energy calculations
    """
    results = {
        "generated_structures": [],
        "energy_calculations": [],
        "most_stable_cifs": {},  # For HTML generation
        "summary": {},
        "pipeline_steps": []
    }
    
    logger.info(f"Creative pipeline: exploring {len(compositions)} compositions...")
    
    # Stage 1: Generate structures for all compositions (no validation)
    if CHEMELEON_AVAILABLE:
        logger.info(f"Generating structures for {len(compositions)} compositions...")
        
        for comp in compositions:
            try:
                # Call generate_crystal_csp for each composition (synchronous function)
                result_str = generate_crystal_csp(comp, num_samples=structures_per_composition, output_format="both")
                struct_result = json.loads(result_str)
                
                if struct_result and struct_result.get("success") and "structures" in struct_result:
                    # Validate structure data before storing
                    validated_structures = []
                    for struct in struct_result["structures"]:
                        if "structure" in struct and isinstance(struct["structure"], dict):
                            # Check if the structure dict has the expected fields
                            struct_dict = struct["structure"]
                            if all(key in struct_dict for key in ["numbers", "positions", "cell"]):
                                validated_structures.append(struct)
                            else:
                                logger.warning(f"Structure missing required fields for {comp}")
                        else:
                            logger.warning(f"Invalid structure format for {comp}")
                    
                    if validated_structures:
                        results["generated_structures"].append({
                            "composition": comp,
                            "structures": validated_structures
                        })
                        logger.info(f"Generated {len(validated_structures)} valid structures for {comp}")
                    else:
                        logger.warning(f"No valid structures for {comp} after validation")
                else:
                    error_msg = struct_result.get("error", "Unknown error") if struct_result else "No result"
                    logger.warning(f"No structures generated for {comp}: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Structure generation failed for {comp}: {e}")
                continue
        
        results["pipeline_steps"].append({
            "stage": "structure_generation",
            "input_count": len(compositions),
            "output_count": len(results["generated_structures"])
        })
    else:
        logger.warning("Chemeleon not available - skipping structure generation")
    
    # Stage 2: Calculate energies for all structures
    if calculate_energies_flag and MACE_AVAILABLE and results["generated_structures"]:
        logger.info(f"Calculating energies for structures...")
        composition_energies = {}
        
        for comp_data in results["generated_structures"]:
            comp = comp_data["composition"]
            structures = comp_data["structures"]
            
            for i, struct in enumerate(structures):
                if "structure" in struct:
                    struct_id = struct.get("id", f"{comp}_struct_{i+1}")
                    try:
                        # Call calculate_formation_energy for each structure (synchronous function)
                        energy_result_str = calculate_formation_energy(struct["structure"])
                        energy_result = json.loads(energy_result_str)
                        
                        if energy_result and energy_result.get("success") and "formation_energy" in energy_result:
                            energy_per_atom = energy_result["formation_energy"]
                            
                            # Track this structure's energy
                            if comp not in composition_energies:
                                composition_energies[comp] = []
                            
                            # Deep copy the structure to avoid reference issues
                            composition_energies[comp].append({
                                "structure_id": struct_id,
                                "energy_per_atom": energy_per_atom,
                                "structure_data": copy.deepcopy(struct),
                                "energy_result": energy_result
                            })
                            
                            results["energy_calculations"].append({
                                "composition": comp,
                                "structure_id": struct_id,
                                "formation_energy": energy_per_atom,
                                "calculation_details": energy_result
                            })
                            logger.info(f"Calculated energy for {struct_id}: {energy_per_atom:.4f} eV/atom")
                        else:
                            error_msg = energy_result.get("error", "Unknown error") if energy_result else "No result"
                            logger.warning(f"No energy result for {struct_id}: {error_msg}")
                            
                    except Exception as e:
                        logger.error(f"Energy calculation failed for {struct_id}: {e}")
                        continue
        
        # Find most stable structure for each composition and generate CIFs
        for comp, structures in composition_energies.items():
            if structures:
                # Sort by energy (most negative = most stable)
                most_stable = min(structures, key=lambda x: x["energy_per_atom"])
                
                # Generate CIF for most stable structure
                struct_data = most_stable["structure_data"]
                if "structure" in struct_data:
                    # Ensure we have the actual structure dict
                    structure_to_convert = struct_data["structure"]
                    
                    # Check if structure is a string (JSON) and parse it
                    if isinstance(structure_to_convert, str):
                        logger.warning(f"Structure for {comp} is a string, parsing as JSON")
                        try:
                            structure_to_convert = json.loads(structure_to_convert)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse structure JSON for {comp}: {e}")
                            continue
                    
                    cif_content = structure_dict_to_cif(structure_to_convert)
                    if cif_content:
                        results["most_stable_cifs"][comp] = {
                            "cif": cif_content,
                            "energy_per_atom": most_stable["energy_per_atom"],
                            "structure_id": most_stable["structure_id"]
                        }
        
        results["pipeline_steps"].append({
            "stage": "energy_calculation",
            "input_count": len(results["energy_calculations"]),
            "output_count": len(results["most_stable_cifs"])
        })
    else:
        if not MACE_AVAILABLE:
            logger.warning("MACE not available - skipping energy calculations")
        elif not calculate_energies_flag:
            logger.info("Energy calculations disabled by flag")
    
    # Generate CIFs for all structures even if energy calculations failed
    if results["generated_structures"] and not results["most_stable_cifs"]:
        logger.info("Energy calculations failed - generating CIFs for all structures")
        for comp_data in results["generated_structures"]:
            comp = comp_data["composition"]
            structures = comp_data["structures"]
            
            # Just take the first structure as a fallback
            if structures and "structure" in structures[0]:
                struct = structures[0]
                struct_id = struct.get("id", f"{comp}_struct_1")
                
                # Ensure we have the actual structure dict
                structure_to_convert = struct["structure"]
                
                # Check if structure is a string (JSON) and parse it
                if isinstance(structure_to_convert, str):
                    logger.warning(f"Fallback structure for {comp} is a string, parsing as JSON")
                    try:
                        structure_to_convert = json.loads(structure_to_convert)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse fallback structure JSON for {comp}: {e}")
                        continue
                
                cif_content = structure_dict_to_cif(structure_to_convert)
                if cif_content:
                    results["most_stable_cifs"][comp] = {
                        "cif": cif_content,
                        "energy_per_atom": None,  # No energy available
                        "structure_id": struct_id,
                        "note": "CIF generated without energy ranking"
                    }
    
    # Generate summary
    total_structures = sum(len(comp_data["structures"]) for comp_data in results["generated_structures"])
    successful_energies = len(results["energy_calculations"])
    
    results["summary"] = {
        "compositions_explored": len(compositions),
        "structures_generated": total_structures,
        "energies_calculated": successful_energies,
        "most_stable_found": len(results["most_stable_cifs"]),
        "pipeline_mode": "creative (fast exploration)",
        "tools_used": {
            "chemeleon": CHEMELEON_AVAILABLE,
            "mace": MACE_AVAILABLE and calculate_energies_flag,
            "smact": False  # Never used in creative mode
        }
    }
    
    logger.info(f"Creative pipeline complete: {len(results['most_stable_cifs'])} stable structures found")
    return results

# ===== DIRECT TOOL ACCESS =====

# Expose Chemeleon tools directly
if CHEMELEON_AVAILABLE:
    @mcp.tool()
    def generate_structures(composition: str, num_samples: int = 3) -> str:
        """Generate crystal structures for a composition using Chemeleon."""
        return generate_crystal_csp(composition, num_samples=num_samples)
    
    @mcp.tool()
    def analyse_crystal_structure(structure: Dict[str, Any]) -> str:
        """Analyse a crystal structure using Chemeleon."""
        return analyse_structure(structure)

# Expose MACE tools directly
if MACE_AVAILABLE:
    @mcp.tool()
    def calculate_energy_mace(structure: Dict[str, Any]) -> str:
        """Calculate formation energy using MACE."""
        return calculate_formation_energy(structure)
    
    @mcp.tool()
    async def optimise_structure(structure: Dict[str, Any]) -> Dict[str, Any]:
        """Optimise structure geometry using MACE."""
        return await relax_structure(structure)
    
    @mcp.tool()
    async def calculate_descriptors(structure: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate structure descriptors using MACE."""
        return await extract_descriptors_robust(structure)

# ===== SERVER STARTUP =====

if __name__ == "__main__":
    logger.info("Starting Chemistry Creative MCP Server")
    logger.info(f"Available tools: Chemeleon={CHEMELEON_AVAILABLE}, MACE={MACE_AVAILABLE}")
    mcp.run()