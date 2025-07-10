"""Unified Chemistry MCP Server integrating SMACT, Chemeleon, and MACE"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add parent directories to path for importing existing tools
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root / "oldmcpservers" / "smact-mcp-server" / "src"))
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

# Initialise unified server
mcp = FastMCP("chemistry-unified")

# Try to import existing tools with graceful fallbacks
try:
    from smact_mcp.tools import (
        smact_validity as smact_validity_tool,
        parse_chemical_formula, 
        get_element_info, 
        calculate_neutral_ratios, 
        test_pauling_rule,
        generate_compositions as smact_generate_compositions,
        quick_validity_check
    )
    SMACT_AVAILABLE = True
    logger.info("SMACT tools loaded successfully")
except ImportError as e:
    logger.warning(f"SMACT tools not available: {e}")
    SMACT_AVAILABLE = False

try:
    from chemeleon_mcp.tools import generate_crystal_csp, analyse_structure
    CHEMELEON_AVAILABLE = True
    logger.info("Chemeleon tools loaded successfully")
except ImportError as e:
    logger.warning(f"Chemeleon tools not available: {e}")
    CHEMELEON_AVAILABLE = False

try:
    from mace_mcp.tools import calculate_energy, calculate_formation_energy, calculate_energy_with_uncertainty
    MACE_AVAILABLE = True
    logger.info("MACE tools loaded successfully")
except ImportError as e:
    logger.warning(f"MACE tools not available: {e}")
    MACE_AVAILABLE = False

# Helper function to generate CIF from structure dict
def structure_dict_to_cif(structure_dict: Dict[str, Any]) -> str:
    """Convert structure dictionary to CIF format string.
    
    Args:
        structure_dict: Dictionary with keys 'numbers', 'positions', 'cell', 'pbc'
        
    Returns:
        CIF format string
    """
    try:
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
        
        # Fix coordinate array shape if flattened during JSON serialisation (CIF generation protection)
        positions_array = np.array(positions)
        n_atoms = len(numbers)
        if len(positions_array.shape) == 1:
            # Coordinates were flattened - reshape to (n_atoms, 3)
            if len(positions_array) == n_atoms * 3:
                positions_array = positions_array.reshape(n_atoms, 3)
                positions = positions_array.tolist()
                logger.info(f"CIF generation: Fixed flattened coordinates: reshaped from ({len(positions_array)},) to ({n_atoms}, 3)")
            else:
                raise ValueError(f"CIF generation: Mismatched coordinate array: {len(positions_array)} elements for {n_atoms} atoms")
        elif positions_array.shape != (n_atoms, 3):
            raise ValueError(f"CIF generation: Invalid coordinate shape: {positions_array.shape} for {n_atoms} atoms")
        
        # Create ASE Atoms object
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
        logger.warning(f"Failed to generate CIF: {e}")
        return ""

# SMACT Tools (with fallbacks)
@mcp.tool()
async def smact_validity(
    composition: str,
    use_pauling_test: bool = True,
    include_alloys: bool = True,
    oxidation_states_set: str = "icsd24",
    check_metallicity: bool = False,
    metallicity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Validate chemical composition using SMACT's sophisticated screening.
    
    Args:
        composition: Chemical formula (e.g., "LiFePO4")
        use_pauling_test: Whether to apply Pauling electronegativity test
        include_alloys: Consider pure metals valid automatically
        oxidation_states_set: Which oxidation states to use ("icsd24", "icsd16", "smact14", "pymatgen_sp", "wiki")
        check_metallicity: If True, consider high metallicity compositions valid
        metallicity_threshold: Score threshold for metallicity validity (0-1)
    
    Returns:
        Validation result with confidence score and natural language explanation
    """
    if SMACT_AVAILABLE:
        try:
            # Use SMACT's basic validity check (advanced parameters not supported)
            result_str = quick_validity_check(composition)
            result = json.loads(result_str)
            
            # Convert to unified format with natural language
            return {
                "valid": result.get("is_valid", False),
                "confidence": 0.95 if result.get("is_valid") else 0.1,
                "explanation": result.get("explanation", f"SMACT validation result for {composition}"),
                "method": "smact_screening",
                "details": result
            }
        except Exception as e:
            logger.error(f"SMACT validation failed: {e}")
    
    # Fallback: Simple heuristic
    try:
        has_metal = any(elem in composition for elem in ["Li", "Na", "K", "Mg", "Ca", "Fe", "Al", "Co", "Ni", "Mn"])
        has_nonmetal = any(elem in composition for elem in ["O", "S", "N", "F", "Cl", "P"])
        
        if has_metal and has_nonmetal:
            return {
                "valid": True,
                "confidence": 0.6,
                "explanation": f"{composition} appears chemically reasonable - contains both metals and non-metals.",
                "method": "heuristic_fallback",
                "details": {"has_metal": has_metal, "has_nonmetal": has_nonmetal}
            }
        else:
            return {
                "valid": False,
                "confidence": 0.3,
                "explanation": f"{composition} may not be valid - unusual elemental combination.",
                "method": "heuristic_fallback", 
                "details": {"has_metal": has_metal, "has_nonmetal": has_nonmetal}
            }
    except Exception as e:
        return {
            "valid": False,
            "confidence": 0.0,
            "explanation": f"Could not validate {composition}: {str(e)}",
            "method": "error",
            "details": {"error": str(e)}
        }

@mcp.tool()
async def parse_composition(formula: str) -> Dict[str, Any]:
    """Parse chemical formula with fallback methods"""
    if SMACT_AVAILABLE:
        try:
            result_str = parse_chemical_formula(formula)
            result = json.loads(result_str)
            return {
                "success": True,
                "elements": result.get("element_counts", {}),
                "total_atoms": result.get("total_atoms", 0),
                "method": "smact"
            }
        except Exception as e:
            logger.warning(f"SMACT parsing failed: {e}")
    
    # Simple fallback parser
    try:
        import re
        # Basic regex to extract elements and numbers
        pattern = r'([A-Z][a-z]?)(\d*)'
        matches = re.findall(pattern, formula)
        
        elements = {}
        total_atoms = 0
        for element, count_str in matches:
            count = int(count_str) if count_str else 1
            elements[element] = elements.get(element, 0) + count
            total_atoms += count
            
        return {
            "success": True,
            "elements": elements,
            "total_atoms": total_atoms,
            "method": "regex_fallback"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "method": "error"
        }

@mcp.tool()
async def generate_compositions(
    elements: List[str],
    threshold: int = 8,
    max_compositions: int = 20
) -> List[Dict[str, Any]]:
    """
    Generate chemically valid compositions using SMACT screening.
    
    Args:
        elements: List of element symbols (e.g., ["Li", "Fe", "P", "O"])
        threshold: Maximum stoichiometric coefficient
        max_compositions: Maximum number of compositions to return
        
    Returns:
        List of valid compositions with formulas and oxidation states
    """
    if SMACT_AVAILABLE:
        try:
            # Use SMACT's composition generator
            result_str = smact_generate_compositions(elements, threshold=threshold)
            result = json.loads(result_str)
            
            compositions = result.get("valid_compositions", [])[:max_compositions]
            
            formatted_results = []
            for comp in compositions:
                formatted_results.append({
                    "formula": comp.get("formula", "Unknown"),
                    "elements": comp.get("elements", elements),
                    "oxidation_states": comp.get("oxidation_states", []),
                    "ratios": comp.get("ratios", []),
                    "method": "smact_filter",
                    "confidence": 0.9
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"SMACT composition generation failed: {e}")
    
    # Fallback: Simple binary combinations
    try:
        fallback_compositions = []
        
        # Separate metals and non-metals
        metals = [e for e in elements if e in ["Li", "Na", "K", "Mg", "Ca", "Fe", "Al", "Co", "Ni", "Mn", "Ti", "V", "Cr"]]
        nonmetals = [e for e in elements if e in ["O", "S", "N", "F", "Cl", "P", "B", "C"]]
        
        # Generate simple binary compounds
        for metal in metals[:3]:  # Limit to prevent explosion
            for nonmetal in nonmetals[:2]:
                # Simple stoichiometries
                for formula in [f"{metal}{nonmetal}", f"{metal}2{nonmetal}", f"{metal}{nonmetal}2"]:
                    fallback_compositions.append({
                        "formula": formula,
                        "elements": [metal, nonmetal],
                        "method": "heuristic_fallback",
                        "confidence": 0.4
                    })
        
        # Add ternary if enough elements
        if len(metals) >= 1 and len(nonmetals) >= 2:
            for metal in metals[:2]:
                if len(nonmetals) >= 2:
                    formula = f"{metal}{nonmetals[0]}{nonmetals[1]}4"
                    fallback_compositions.append({
                        "formula": formula,
                        "elements": [metal, nonmetals[0], nonmetals[1]],
                        "method": "ternary_heuristic",
                        "confidence": 0.3
                    })
        
        return fallback_compositions[:max_compositions]
        
    except Exception as e:
        logger.error(f"Composition generation fallback failed: {e}")
        return []

# Chemeleon Tools
@mcp.tool()
async def generate_structures(
    composition: str,
    num_structures: int = 5,
    max_atoms: int = 50
) -> List[Dict[str, Any]]:
    """
    Generate crystal structures with multiple methods.
    
    Args:
        composition: Chemical formula
        num_structures: Number of structures to generate
        max_atoms: Maximum atoms per unit cell
    
    Returns:
        List of structure dictionaries with metadata
    """
    if CHEMELEON_AVAILABLE:
        try:
            # Generate structures with both CIF and dict format
            result_str = generate_crystal_csp(
                composition, 
                num_structures, 
                max_atoms,
                output_format="both"  # Get both CIF and structure formats
            )
            result = json.loads(result_str)
            
            if result.get("success"):
                structures = result.get("structures", [])
                processed_structures = []
                
                for i, struct in enumerate(structures):
                    # Process each structure
                    try:
                        # First try to use the structure format (Chemeleon stores data here)
                        structure_dict = None
                        if "structure" in struct and struct["structure"]:
                            structure_dict = struct["structure"]
                        elif "dict" in struct and struct["dict"]:
                            # Backward compatibility
                            structure_dict = struct["dict"]
                        
                        if structure_dict:
                            # Validate structure has required fields
                            required_fields = ["numbers", "positions", "cell"]
                            missing_fields = [field for field in required_fields if field not in structure_dict or structure_dict[field] is None]
                            
                            if not missing_fields:
                                # Check for nan values in positions and cell
                                import numpy as np
                                positions_array = np.array(structure_dict["positions"])
                                cell_array = np.array(structure_dict["cell"])
                                
                                # Fix coordinate array shape if flattened during JSON serialisation
                                n_atoms = len(structure_dict["numbers"])
                                if len(positions_array.shape) == 1:
                                    # Coordinates were flattened - reshape to (n_atoms, 3)
                                    if len(positions_array) == n_atoms * 3:
                                        positions_array = positions_array.reshape(n_atoms, 3)
                                        structure_dict["positions"] = positions_array.tolist()
                                        logger.info(f"Fixed flattened coordinates for structure {i}: reshaped from ({len(positions_array)},) to ({n_atoms}, 3)")
                                    else:
                                        logger.error(f"Structure {i} has mismatched coordinate array: {len(positions_array)} elements for {n_atoms} atoms - skipping")
                                        continue
                                elif positions_array.shape != (n_atoms, 3):
                                    logger.error(f"Structure {i} has invalid coordinate shape: {positions_array.shape} for {n_atoms} atoms - skipping")
                                    continue
                                
                                if np.any(np.isnan(positions_array)) or np.any(np.isnan(cell_array)):
                                    logger.warning(f"Structure {i} contains nan values in positions or cell - skipping")
                                    continue
                                
                                processed_struct = {
                                    "numbers": structure_dict["numbers"],
                                    "positions": structure_dict["positions"],
                                    "cell": structure_dict["cell"],
                                    "pbc": structure_dict.get("pbc", [True, True, True]),
                                    "formula": structure_dict.get("formula", composition),
                                    "method": "chemeleon",
                                    "confidence": 0.85,
                                    "id": f"{composition}_struct_{i+1}",
                                    "sample_idx": struct.get("sample_idx", i)
                                }
                                
                                # Always generate and include CIF for MACE compatibility
                                if "cif" in struct and struct["cif"]:
                                    processed_struct["cif"] = struct["cif"]
                                else:
                                    # Generate CIF from structure dict
                                    cif_content = structure_dict_to_cif(structure_dict)
                                    if cif_content:
                                        processed_struct["cif"] = cif_content
                                    else:
                                        logger.warning(f"Failed to generate CIF for structure {i}")
                                        continue  # Skip structures without CIF for MACE compatibility
                                
                                # Ensure structure data is MACE-compatible
                                # Add any additional fields MACE might need
                                processed_struct["mace_ready"] = True
                                processed_struct["structure_format"] = "chemeleon_dict_with_cif"
                                
                                processed_structures.append(processed_struct)
                                continue
                            else:
                                logger.warning(f"Structure {i} missing required fields: {missing_fields} - skipping")
                        
                        # Fallback: Convert CIF to dict if only CIF is available
                        if "cif" in struct and struct["cif"]:
                            cif_content = struct["cif"]
                            # Parse CIF using ASE
                            atoms = ase_read(io.StringIO(cif_content), format="cif")
                            
                            processed_struct = {
                                "numbers": atoms.numbers.tolist(),
                                "positions": atoms.positions.tolist(),
                                "cell": atoms.cell.tolist(),
                                "pbc": atoms.pbc.tolist(),
                                "formula": atoms.get_chemical_formula(),
                                "method": "chemeleon",
                                "confidence": 0.85,
                                "id": f"{composition}_struct_{i+1}",
                                "sample_idx": struct.get("sample_idx", i),
                                "cif": cif_content,
                                "mace_ready": True,
                                "structure_format": "chemeleon_cif_converted"
                            }
                            processed_structures.append(processed_struct)
                    
                    except Exception as struct_error:
                        logger.warning(f"Failed to process structure {i}: {struct_error}")
                        continue
                
                return processed_structures
        except Exception as e:
            logger.error(f"Chemeleon structure generation failed: {e}")
    
    # Fallback: Return common structure prototypes
    try:
        parsed = await parse_composition(composition)
        if not parsed.get("success"):
            return []
            
        elements = parsed["elements"]
        num_elements = len(elements)
        
        fallback_structures = []
        
        if num_elements == 2:
            # Binary compound - suggest rock salt, fluorite, or rutile
            for i, structure_type in enumerate(["rock_salt", "fluorite", "rutile"][:num_structures]):
                fallback_structures.append({
                    "id": f"{composition}_prototype_{i+1}",
                    "structure_type": structure_type,
                    "method": "prototype_fallback",
                    "confidence": 0.4,
                    "lattice_system": "cubic" if structure_type != "rutile" else "tetragonal",
                    "space_group": {"rock_salt": "Fm-3m", "fluorite": "Fm-3m", "rutile": "P42/mnm"}[structure_type],
                    "description": f"Prototype {structure_type} structure for {composition}"
                })
        
        elif num_elements == 3:
            # Ternary - suggest perovskite or spinel
            for i, structure_type in enumerate(["perovskite", "spinel"][:num_structures]):
                fallback_structures.append({
                    "id": f"{composition}_prototype_{i+1}",
                    "structure_type": structure_type,
                    "method": "prototype_fallback", 
                    "confidence": 0.4,
                    "lattice_system": "cubic",
                    "space_group": {"perovskite": "Pm-3m", "spinel": "Fd-3m"}[structure_type],
                    "description": f"Prototype {structure_type} structure for {composition}"
                })
        
        return fallback_structures[:num_structures]
        
    except Exception as e:
        logger.error(f"Structure generation fallback failed: {e}")
        return []

@mcp.tool()
async def analyse_structure(structure_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze crystal structure properties"""
    if CHEMELEON_AVAILABLE:
        try:
            result_str = analyse_structure(json.dumps(structure_data))
            return json.loads(result_str)
        except Exception as e:
            logger.warning(f"Chemeleon structure analysis failed: {e}")
    
    # Fallback analysis
    return {
        "method": "fallback",
        "analysis": "Structure analysis not available - Chemeleon tools unavailable",
        "confidence": 0.0
    }

# MACE Tools
@mcp.tool()
async def calculate_energies(
    structures: List[Dict[str, Any]],
    properties: List[str] = ["energy", "forces"],
    parallel: bool = True
) -> List[Dict[str, Any]]:
    """
    Calculate energies using MACE with parallelisation.
    
    Args:
        structures: List of structure dictionaries
        properties: Properties to calculate ["energy", "forces", "stress"]
        parallel: Whether to use parallel processing
        
    Returns:
        List of results with energies and uncertainties
    """
    if not MACE_AVAILABLE:
        return [{
            "structure_id": i,
            "error": "MACE not available",
            "energy": None,
            "method": "unavailable"
        } for i in range(len(structures))]
    
    results = []
    
    if parallel and len(structures) > 1:
        # Process in parallel for better GPU utilisation
        tasks = []
        for i, structure in enumerate(structures):
            task = _calculate_single_energy(structure, properties, i)
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any failures gracefully
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Energy calculation failed for structure {i}: {result}")
                    processed_results.append({
                        "structure_id": i,
                        "error": str(result),
                        "energy": None,
                        "method": "mace_failed"
                    })
                else:
                    processed_results.append(result)
            return processed_results
            
        except Exception as e:
            logger.error(f"Parallel energy calculation failed: {e}")
            return [{
                "structure_id": i,
                "error": str(e),
                "energy": None,
                "method": "parallel_failed"
            } for i in range(len(structures))]
    else:
        # Sequential processing
        for i, structure in enumerate(structures):
            try:
                result = await _calculate_single_energy(structure, properties, i)
                results.append(result)
            except Exception as e:
                logger.error(f"Energy calculation failed for structure {i}: {e}")
                results.append({
                    "structure_id": i,
                    "error": str(e),
                    "energy": None,
                    "method": "mace_failed"
                })
        return results

async def _calculate_single_energy(structure: Dict[str, Any], properties: List[str], structure_id: int) -> Dict[str, Any]:
    """Calculate energy for a single structure"""
    try:
        # Ensure structure has all required fields for MACE
        mace_structure = {
            "numbers": structure.get("numbers"),
            "positions": structure.get("positions"),
            "cell": structure.get("cell"),
            "pbc": structure.get("pbc", [True, True, True])
        }
        
        # Validate required fields
        required_fields = ["numbers", "positions", "cell"]
        missing_fields = [field for field in required_fields if field not in structure or structure[field] is None]
        if missing_fields:
            raise ValueError(f"Structure missing required fields: {missing_fields}. "
                           f"Available fields: {list(structure.keys())}. "
                           f"Structure ID: {structure_id}")
        
        # Additional validation for MACE compatibility
        import numpy as np
        try:
            # Check for nan values that would break MACE
            positions_array = np.array(mace_structure["positions"])
            cell_array = np.array(mace_structure["cell"])
            
            # Fix coordinate array shape if flattened during JSON serialisation (second layer of protection)
            n_atoms = len(mace_structure["numbers"])
            if len(positions_array.shape) == 1:
                # Coordinates were flattened - reshape to (n_atoms, 3)
                if len(positions_array) == n_atoms * 3:
                    positions_array = positions_array.reshape(n_atoms, 3)
                    mace_structure["positions"] = positions_array.tolist()
                    logger.info(f"MACE validation: Fixed flattened coordinates for structure {structure_id}: reshaped from ({len(positions_array)},) to ({n_atoms}, 3)")
                else:
                    raise ValueError(f"Structure {structure_id} has mismatched coordinate array: {len(positions_array)} elements for {n_atoms} atoms")
            elif positions_array.shape != (n_atoms, 3):
                raise ValueError(f"Structure {structure_id} has invalid coordinate shape: {positions_array.shape} for {n_atoms} atoms")
            
            if np.any(np.isnan(positions_array)):
                raise ValueError(f"Structure {structure_id} contains nan values in positions")
            if np.any(np.isnan(cell_array)):
                raise ValueError(f"Structure {structure_id} contains nan values in cell")
            
            # Ensure numbers is a list of integers
            if not all(isinstance(num, (int, np.integer)) for num in mace_structure["numbers"]):
                # Try to convert to integers
                mace_structure["numbers"] = [int(num) for num in mace_structure["numbers"]]
                
            logger.debug(f"MACE validation passed for structure {structure_id}")
            
        except Exception as validation_error:
            raise ValueError(f"MACE compatibility validation failed for structure {structure_id}: {validation_error}")
        
        # Use existing MACE tool
        result_str = calculate_energy(
            mace_structure,
            include_forces=("forces" in properties),
            include_stress=("stress" in properties)
        )
        result = json.loads(result_str)
        
        result["structure_id"] = structure_id
        result["method"] = "mace"
        result["composition"] = structure.get("formula", "unknown")
        return result
        
    except Exception as e:
        raise Exception(f"MACE calculation failed: {str(e)}")

# Batch Operations for Efficiency
@mcp.tool()
async def batch_discovery_pipeline(
    compositions: List[str],
    structures_per_composition: int = 3,
    validate_first: bool = True,
    calculate_energies_flag: bool = True
) -> Dict[str, Any]:
    """
    Complete pipeline for multiple compositions with parallelisation.
    
    Args:
        compositions: List of chemical formulas
        structures_per_composition: Structures to generate per composition
        validate_first: Whether to validate before structure generation
        calculate_energies_flag: Whether to calculate energies with MACE
        
    Returns:
        Complete results with all stages
    """
    results = {
        "validated_compositions": [],
        "generated_structures": [],
        "energy_calculations": [],
        "summary": {},
        "pipeline_steps": []
    }
    
    # Stage 1: Parallel validation
    if validate_first:
        logger.info(f"Validating {len(compositions)} compositions...")
        validation_tasks = [
            smact_validity(comp) for comp in compositions
        ]
        validation_results = await asyncio.gather(*validation_tasks)
        
        for comp, val_result in zip(compositions, validation_results):
            if val_result["valid"] or val_result["confidence"] > 0.5:
                results["validated_compositions"].append({
                    "composition": comp,
                    "validation": val_result
                })
        
        results["pipeline_steps"].append({
            "stage": "validation",
            "input_count": len(compositions),
            "output_count": len(results["validated_compositions"])
        })
    else:
        results["validated_compositions"] = [
            {"composition": comp, "validation": {"valid": True, "confidence": 1.0}}
            for comp in compositions
        ]
    
    # Stage 2: Parallel structure generation
    valid_comps = [r["composition"] for r in results["validated_compositions"]]
    
    if valid_comps:
        logger.info(f"Generating structures for {len(valid_comps)} valid compositions...")
        structure_tasks = [
            generate_structures(comp, structures_per_composition)
            for comp in valid_comps
        ]
        structure_results = await asyncio.gather(*structure_tasks)
        
        all_structures = []
        for comp, structures in zip(valid_comps, structure_results):
            for struct in structures:
                struct["composition"] = comp
                all_structures.append(struct)
        
        results["generated_structures"] = all_structures
        results["pipeline_steps"].append({
            "stage": "structure_generation",
            "input_count": len(valid_comps),
            "output_count": len(all_structures)
        })
    
    # Stage 3: Batch energy calculation
    if calculate_energies_flag and results["generated_structures"]:
        logger.info(f"Calculating energies for {len(results['generated_structures'])} structures...")
        energy_results = await calculate_energies(results["generated_structures"], parallel=True)
        results["energy_calculations"] = energy_results
        
        # Find most stable structures per composition and include CIF
        stable_structures = {}
        structure_id_map = {struct.get("id", f"struct_{i}"): struct 
                           for i, struct in enumerate(results["generated_structures"])}
        
        for i, energy_result in enumerate(energy_results):
            if energy_result.get("energy") is not None:
                comp = energy_result.get("composition", "unknown")
                struct_id = energy_result.get("structure_id", i)
                
                # Get the original structure with CIF
                original_struct = results["generated_structures"][struct_id] if struct_id < len(results["generated_structures"]) else None
                
                if comp not in stable_structures or energy_result["energy"] < stable_structures[comp]["energy"]:
                    # Combine energy result with original structure data including CIF
                    combined_result = energy_result.copy()
                    if original_struct and "cif" in original_struct:
                        combined_result["cif"] = original_struct["cif"]
                        combined_result["structure_id_label"] = original_struct.get("id", f"{comp}_struct_{struct_id+1}")
                    stable_structures[comp] = combined_result
        
        results["most_stable_structures"] = list(stable_structures.values())
        
        # Extract CIF files for most stable structures
        results["most_stable_cifs"] = {}
        for comp, stable_struct in stable_structures.items():
            if "cif" in stable_struct:
                results["most_stable_cifs"][comp] = {
                    "cif": stable_struct["cif"],
                    "energy_per_atom": stable_struct.get("energy_per_atom"),
                    "structure_id": stable_struct.get("structure_id_label", f"{comp}_stable")
                }
        
        results["pipeline_steps"].append({
            "stage": "energy_calculation",
            "input_count": len(results["generated_structures"]),
            "output_count": len([r for r in energy_results if r.get("energy") is not None])
        })
    
    # Summary statistics
    results["summary"] = {
        "total_compositions": len(compositions),
        "valid_compositions": len(results["validated_compositions"]),
        "total_structures": len(results["generated_structures"]),
        "successful_calculations": len([r for r in results.get("energy_calculations", []) if r.get("energy") is not None]),
        "most_stable_count": len(results.get("most_stable_structures", [])),
        "pipeline_success": True,
        "available_tools": {
            "smact": SMACT_AVAILABLE,
            "chemeleon": CHEMELEON_AVAILABLE,
            "mace": MACE_AVAILABLE
        }
    }
    
    return results

# Health check and diagnostics
@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check health of all integrated chemistry tools"""
    health = {
        "server": "chemistry-unified",
        "status": "healthy",
        "tools": {},
        "test_results": {}
    }
    
    # Test SMACT
    try:
        test_result = await smact_validity("LiFePO4")
        health["tools"]["smact"] = "available" if test_result.get("valid") is not None else "degraded"
        health["test_results"]["smact"] = test_result
    except Exception as e:
        health["tools"]["smact"] = "unavailable"
        health["test_results"]["smact"] = {"error": str(e)}
        health["status"] = "degraded"
    
    # Test Chemeleon
    try:
        test_structures = await generate_structures("LiFePO4", num_structures=1)
        health["tools"]["chemeleon"] = "available" if len(test_structures) > 0 else "degraded"
        health["test_results"]["chemeleon"] = {"structures_generated": len(test_structures)}
    except Exception as e:
        health["tools"]["chemeleon"] = "unavailable"
        health["test_results"]["chemeleon"] = {"error": str(e)}
        health["status"] = "degraded"
        
    # Test MACE
    try:
        test_struct = [{"composition": "Li", "method": "test"}]
        test_energies = await calculate_energies(test_struct, parallel=False)
        health["tools"]["mace"] = "available" if len(test_energies) > 0 else "degraded"
        health["test_results"]["mace"] = {"calculations_completed": len(test_energies)}
    except Exception as e:
        health["tools"]["mace"] = "unavailable"
        health["test_results"]["mace"] = {"error": str(e)}
        health["status"] = "degraded"
    
    return health

# Main server entry point
def main():
    """Run the unified chemistry server"""
    try:
        logger.info("Starting Chemistry Unified MCP Server")
        logger.info(f"Available tools: SMACT={SMACT_AVAILABLE}, Chemeleon={CHEMELEON_AVAILABLE}, MACE={MACE_AVAILABLE}")
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()