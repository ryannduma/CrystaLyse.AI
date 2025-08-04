"""Creative Chemistry MCP Server integrating Chemeleon and MACE (no SMACT for faster exploration)"""

import logging
import json
import copy
from typing import Dict, Any
import sys
import os
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from ase.io import write as ase_write
from ase import Atoms
import numpy as np
from datetime import datetime

# Add parent directories to path for importing existing tools
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root / "oldmcpservers" / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "mace-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "crystalyse"))


logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

try:
    from converters import convert_cif_to_mace_input
    CONVERTER_AVAILABLE = True
    logger.info("CIF to MACE converter loaded successfully")
except ImportError as e:
    logger.warning(f"CIF to MACE converter not available: {e}")
    CONVERTER_AVAILABLE = False

# --- Session Management Functions (from unified server) ---
def _create_session_directory(composition: str, mode: str) -> Path:
    """Create session-based directory structure for organizing output files."""
    try:
        # Create session timestamp
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        
        # Create session directory
        project_root_path = Path(__file__).parent.parent.parent.parent.parent
        output_dir = project_root_path / "all-runtime-output" / session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created session directory: {output_dir}")
        return output_dir
        
    except Exception as e:
        logger.error(f"Failed to create session directory: {e}")
        # Fallback to old structure
        project_root_path = Path(__file__).parent.parent.parent.parent.parent
        output_dir = project_root_path / "all-runtime-output"
        output_dir.mkdir(exist_ok=True)
        return output_dir

def _update_session_metadata(session_dir: Path, composition: str, mode: str, files_generated: list):
    """Update session metadata file with analysis information."""
    try:
        metadata_file = session_dir / "session_info.json"
        
        # Load existing metadata or create new
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "session_id": session_dir.name,
                "start_time": datetime.now().isoformat(),
                "mode_history": [],
                "compounds_analyzed": [],
                "files_generated": []
            }
        
        # Update metadata
        if mode not in metadata["mode_history"]:
            metadata["mode_history"].append(mode)
        
        if composition not in metadata["compounds_analyzed"]:
            metadata["compounds_analyzed"].append(composition)
        
        # Add new files
        for file_info in files_generated:
            if file_info not in metadata["files_generated"]:
                metadata["files_generated"].append(file_info)
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Updated session metadata: {metadata_file}")
        
    except Exception as e:
        logger.error(f"Failed to update session metadata: {e}")

def save_cif_file(cif_content: str, filename: str, session_dir: Path) -> Path:
    """Save CIF content to a file in the session directory."""
    try:
        cif_path = session_dir / filename
        with open(cif_path, 'w') as f:
            f.write(cif_content)
        logger.info(f"Saved CIF file: {cif_path}")
        return cif_path
    except Exception as e:
        logger.error(f"Failed to save CIF file {filename}: {e}")
        raise

# --- JSON Serialization Helper ---
def make_json_serializable(obj):
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
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        try:
            return str(obj)
        except:
            return f"<non-serializable: {type(obj).__name__}>"

def safe_json_dumps(data, **kwargs) -> str:
    """Safe JSON dumps that automatically handles problematic types."""
    try:
        return json.dumps(data, **kwargs)
    except TypeError as e:
        if "not JSON serializable" in str(e):
            logger.debug("Applying JSON serialization fixes...")
            fixed_data = make_json_serializable(data)
            return json.dumps(fixed_data, **kwargs)
        else:
            raise

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
        relax_structure,
        extract_descriptors_robust,
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
                except Exception:
                    # Try direct eval as a fallback (careful with security)
                    import ast
                    return ast.literal_eval(decoded)
            elif isinstance(field_value, str):
                logger.warning(f"{field_name} field is string - attempting to parse")
                try:
                    return json.loads(field_value)
                except Exception:
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

# ===== COMPREHENSIVE MATERIALS ANALYSIS (Creative Mode) =====

@mcp.tool()
async def comprehensive_materials_analysis(
    compositions: list[str],
    mode: str = "creative",
    structures_per_composition: int = 3,
    calculate_energies_flag: bool = True,
    temperature_range: str = "ambient",
    applications: str = "general"
) -> dict[str, Any]:
    """
    Comprehensive materials analysis for creative mode - fast exploration without SMACT validation.
    
    This is the main entry point that matches the unified server interface but uses the
    creative discovery pipeline internally (no SMACT validation, no hull calculations).
    
    Args:
        compositions: List of chemical formulas to analyze
        mode: Analysis mode (should be "creative" for this server)
        structures_per_composition: Number of structures to generate per composition
        calculate_energies_flag: Whether to calculate formation energies with MACE
        temperature_range: Temperature considerations (informational only)
        applications: Target applications (informational only)
        
    Returns:
        Comprehensive analysis results with structure generation and energy calculations
    """
    logger.info(f"comprehensive_materials_analysis called with mode='{mode}' for {len(compositions)} compositions")
    
    # Validate mode parameter
    if mode != "creative":
        logger.warning(f"Mode '{mode}' passed to creative server - should be 'creative'")
    
    # Call the creative discovery pipeline with the same parameters
    results = await creative_discovery_pipeline(
        compositions=compositions,
        structures_per_composition=structures_per_composition,
        calculate_energies_flag=calculate_energies_flag
    )
    
    # Add mode and analysis metadata to match unified server format
    if isinstance(results, dict):
        results["analysis_mode"] = "creative"
        results["server_type"] = "chemistry-creative"
        results["temperature_range"] = temperature_range
        results["target_applications"] = applications
        
        # Update summary to include creative-specific info
        if "summary" in results:
            results["summary"]["analysis_mode"] = "creative"
            results["summary"]["validation_tools"] = {
                "smact": False,  # Never used in creative mode
                "hull_calculations": False,  # Not available in creative mode
                "pymatgen_analysis": True,  # Used for structure processing
                "mace_energies": calculate_energies_flag and MACE_AVAILABLE
            }
            results["summary"]["speed_optimizations"] = [
                "No SMACT composition validation",
                "No energy above hull calculations", 
                "Fast structure generation with Chemeleon",
                "Automatic visualization generation"
            ]
    
    logger.info(f"Creative comprehensive analysis complete: {len(results.get('most_stable_cifs', {}))} structures analyzed")
    return results

# ===== CREATIVE DISCOVERY PIPELINE =====

@mcp.tool()
async def creative_discovery_pipeline(
    compositions: list[str],
    structures_per_composition: int = 3,
    calculate_energies_flag: bool = True
) -> dict[str, Any]:
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
        logger.info(f"Calculating energies for {len(results['generated_structures'])} structures...")
        
        composition_energies = {}
        
        for comp_data in results["generated_structures"]:
            comp = comp_data["composition"]
            structures = comp_data["structures"]
            
            for i, struct in enumerate(structures):
                struct_id = struct.get("id", f"{comp}_struct_{i+1}")
                try:
                    # --- Pymatgen Bridge Implementation ---
                    if "cif" not in struct or not isinstance(struct["cif"], str):
                        raise ValueError("Structure dictionary is missing a valid 'cif' entry.")

                    mace_input_dict = convert_cif_to_mace_input(struct["cif"])

                    # Call calculate_formation_energy with the standardized dict
                    energy_result_str = calculate_formation_energy(mace_input_dict.get("mace_input"))
                    energy_result = json.loads(energy_result_str)
                    
                    if energy_result and energy_result.get("status") == "completed" and "formation_energy_per_atom" in energy_result:
                        energy_per_atom = energy_result["formation_energy_per_atom"]
                        
                        if comp not in composition_energies:
                            composition_energies[comp] = []
                        
                        composition_energies[comp].append({
                            "structure_id": struct_id,
                            "energy_per_atom": energy_per_atom,
                            "structure_data": copy.deepcopy(struct),
                        })
                        
                        results["energy_calculations"].append({
                            "composition": comp,
                            "structure_id": struct_id,
                            "formation_energy": energy_per_atom,
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
    
    # AUTOMATICALLY SAVE CIF FILES FOR ALL GENERATED STRUCTURES
    if results["most_stable_cifs"]:
        logger.info(f"Saving CIF files for {len(results['most_stable_cifs'])} compositions...")
        
        for comp, cif_data in results["most_stable_cifs"].items():
            cif_content = cif_data["cif"]
            
            try:
                # Create session directory for organized output
                session_dir = _create_session_directory(comp, "creative")
                
                # Save CIF file
                cif_filename = f"{comp.replace(' ', '_')}_creative.cif"
                cif_path = save_cif_file(cif_content, cif_filename, session_dir)
                cif_data["cif_file_path"] = str(cif_path)
                
                logger.info(f"✅ Saved CIF file for {comp}: {cif_path}")
                
                # Update session metadata with CIF file only
                files_generated = [
                    {"type": "cif", "path": str(cif_path), "composition": comp}
                ]
                _update_session_metadata(session_dir, comp, "creative", files_generated)
                
            except Exception as e:
                logger.error(f"❌ Failed to save CIF file for {comp}: {e}")
                cif_data["cif_file_error"] = str(e)
    
    # Generate summary
    total_structures = sum(len(comp_data["structures"]) for comp_data in results["generated_structures"])
    successful_energies = len(results["energy_calculations"])
    
    results["summary"] = {
        "compositions_explored": len(compositions),
        "structures_generated": total_structures,
        "energies_calculated": successful_energies,
        "most_stable_found": len(results["most_stable_cifs"]),
        "cif_files_saved": len([cif for cif in results["most_stable_cifs"].values() if "cif_file_path" in cif]),
        "pipeline_mode": "creative (fast exploration)",
        "tools_used": {
            "chemeleon": CHEMELEON_AVAILABLE,
            "mace": MACE_AVAILABLE and calculate_energies_flag,
            "smact": False  # Never used in creative mode
        }
    }
    
    logger.info(f"Creative pipeline complete: {len(results['most_stable_cifs'])} stable structures found")
    
    # Convert results to JSON-serializable format
    serializable_results = make_json_serializable(results)
    
    return serializable_results

# ===== DIRECT TOOL ACCESS =====

# Expose Chemeleon tools directly
if CHEMELEON_AVAILABLE:
    @mcp.tool()
    def generate_structures(
        composition: str, 
        num_samples: int = 3,
        min_atoms: int = 20,
        max_formula_units: int = 4
    ) -> str:
        """
        Generate crystal structures for a composition using Chemeleon.
        
        Args:
            composition: Chemical formula (e.g., "NaCl", "Li2O")
            num_samples: Number of structures to generate per formula unit
            min_atoms: Minimum number of atoms in the unit cell (will create supercell if needed)
            max_formula_units: Maximum formula units to explore (e.g., 3 means try M₁X₁, M₂X₂, M₃X₃)
            
        Returns:
            JSON string with generated structures at various stoichiometries
        """
        try:
            # Import supercell function if available
            from converters import create_supercell_cif
            supercell_available = True
        except ImportError:
            logger.warning("Supercell converter not available")
            supercell_available = False
            
        try:
            from pymatgen.core import Composition
            
            # Parse base composition to get element ratio
            base_comp = Composition(composition)
            reduced_comp = base_comp.reduced_composition
            
            # Get the base elements and their ratios
            elements = list(reduced_comp.keys())
            base_amounts = [reduced_comp[el] for el in elements]
            
            all_structures = []
            formulas_generated = []
            
            # Generate structures for different formula units
            for n_units in range(1, max_formula_units + 1):
                # Create formula with n formula units
                amounts = [int(amt * n_units) for amt in base_amounts]
                
                # Create the scaled formula string
                scaled_formula = ""
                for el, amt in zip(elements, amounts):
                    if amt == 1:
                        scaled_formula += str(el)
                    else:
                        scaled_formula += f"{el}{amt}"
                
                logger.info(f"Generating {num_samples} structures for {scaled_formula} ({n_units} formula units)")
                
                try:
                    # Generate structures for this stoichiometry
                    result_json = generate_crystal_csp(scaled_formula, num_samples=num_samples, output_format="both")
                    result = json.loads(result_json)
                    
                    if result.get("success", False):
                        structures = result.get("structures", [])
                        
                        # Add metadata about formula units
                        for struct in structures:
                            struct["formula_units"] = n_units
                            struct["base_formula"] = composition
                            struct["scaled_formula"] = scaled_formula
                        
                        all_structures.extend(structures)
                        formulas_generated.append(scaled_formula)
                    else:
                        logger.warning(f"Failed to generate structures for {scaled_formula}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error generating structures for {scaled_formula}: {e}")
                    continue
            
            # Process all structures and apply intelligent supercell generation only when necessary
            enhanced_structures = []
            
            for structure in all_structures:
                # Use atom_count from filtering if available, otherwise fallback to structure parsing
                num_atoms = structure.get("atom_count", len(structure.get("structure", {}).get("atom_types", [])))
                structure["original_atoms"] = num_atoms
                structure["supercell_created"] = False
                
                # Smart supercell decision: only for genuinely undersized structures
                if num_atoms < min_atoms and num_atoms >= 1 and supercell_available:  # Avoid degenerate cases
                    # Calculate reasonable supercell dimensions with caps
                    max_final_atoms = min_atoms * 2  # Smaller cap for creative mode (faster)
                    multiplier = max(1, int((min_atoms / num_atoms) ** (1/3)))
                    
                    # Safety checks before creating supercell
                    predicted_atoms = multiplier**3 * num_atoms
                    if predicted_atoms > max_final_atoms:
                        # Recalculate with linear scaling instead
                        multiplier = min(max_final_atoms // num_atoms, 2)  # Cap at 2x for creative mode
                        predicted_atoms = multiplier**3 * num_atoms
                    
                    # Only create supercell if it's actually beneficial and reasonable
                    if multiplier > 1 and predicted_atoms <= max_final_atoms:
                        supercell_matrix = [[multiplier, 0, 0], [0, multiplier, 0], [0, 0, multiplier]]
                        
                        logger.info(f"FALLBACK: Creating {multiplier}x{multiplier}x{multiplier} supercell for {structure['scaled_formula']} "
                                  f"(original: {num_atoms} atoms → target: {predicted_atoms} atoms)")
                        
                        # Create supercell if CIF is available
                        if "cif" in structure:
                            try:
                                supercell_result = create_supercell_cif(structure["cif"], supercell_matrix)
                                
                                if supercell_result.get("success", False):
                                    # Validate the supercell result
                                    final_atoms = supercell_result.get("supercell_atoms", predicted_atoms)
                                    
                                    # Additional sanity checks
                                    if final_atoms >= min_atoms and final_atoms <= max_final_atoms:
                                        structure["supercell_created"] = True
                                        structure["supercell_matrix"] = supercell_matrix
                                        structure["cif"] = supercell_result["cif_string"]
                                        structure["supercell_atoms"] = final_atoms
                                        
                                        # Convert supercell CIF to dict format
                                        from pymatgen.core import Structure
                                        try:
                                            supercell_struct = Structure.from_str(supercell_result["cif_string"], fmt="cif")
                                            structure["structure"] = {
                                                "atom_types": [site.specie.Z for site in supercell_struct],
                                                "cart_coords": supercell_struct.cart_coords.tolist(),
                                                "frac_coords": supercell_struct.frac_coords.tolist(),
                                                "lattice": supercell_struct.lattice.matrix.tolist(),
                                                "num_atoms": len(supercell_struct)
                                            }
                                            logger.info(f"✅ Successfully created and validated supercell: {final_atoms} atoms")
                                        except Exception as e:
                                            logger.warning(f"Could not convert supercell to dict format: {e}")
                                            structure["supercell_created"] = False  # Revert on failure
                                    else:
                                        logger.warning(f"Supercell validation failed: {final_atoms} atoms not in range [{min_atoms}, {max_final_atoms}]")
                                else:
                                    logger.warning(f"Supercell creation failed for {structure['scaled_formula']}: {supercell_result.get('error', 'Unknown error')}")
                            except Exception as e:
                                logger.error(f"Supercell generation error: {e}")
                    else:
                        logger.info(f"Skipping supercell for {structure['scaled_formula']}: multiplier={multiplier}, predicted_atoms={predicted_atoms} (not beneficial)")
                elif num_atoms >= min_atoms:
                    logger.info(f"✅ Structure {structure['scaled_formula']} has sufficient atoms ({num_atoms} >= {min_atoms}), no supercell needed")
                else:
                    logger.warning(f"⚠️ Degenerate structure {structure['scaled_formula']} with {num_atoms} atoms, skipping supercell")
                
                enhanced_structures.append(structure)
            
            # Group structures by formula units for better organization
            structures_by_units = {}
            for struct in enhanced_structures:
                n_units = struct["formula_units"]
                if n_units not in structures_by_units:
                    structures_by_units[n_units] = []
                structures_by_units[n_units].append(struct)
            
            return json.dumps({
                "success": True,
                "base_composition": composition,
                "formulas_generated": formulas_generated,
                "total_structures": len(enhanced_structures),
                "structures": enhanced_structures,
                "structures_by_formula_units": structures_by_units,
                "generation_summary": {
                    f"{n}_formula_units": len(structs) 
                    for n, structs in structures_by_units.items()
                },
                "min_atoms_requested": min_atoms,
                "max_formula_units": max_formula_units
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error in enhanced structure generation: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "composition": composition
            }, indent=2)
    
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



# Add visualization function after existing tools
@mcp.tool()
def create_structure_visualization(
    cif_content: str,
    formula: str,
    title: str = "Crystal Structure"
) -> str:
    """Create fast 3Dmol.js visualization for creative mode structures."""
    try:
        # Use dedicated runtime output directory
        project_root = Path(__file__).parent.parent.parent.parent.parent
        working_dir = str(project_root / "all-runtime-output")
        
        # Import and use visualization tools
        from visualization_mcp.tools import create_creative_visualization
        return create_creative_visualization(cif_content, formula, working_dir, title)
        
    except Exception as e:
        return json.dumps({
            "type": "visualization",
            "status": "error",
            "error": f"Creative visualization failed: {str(e)}"
        })

# ===== SERVER STARTUP =====

if __name__ == "__main__":
    logger.info("Starting Chemistry Creative MCP Server")
    logger.info(f"Available tools: Chemeleon={CHEMELEON_AVAILABLE}, MACE={MACE_AVAILABLE}")
    mcp.run()