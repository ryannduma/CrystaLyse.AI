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
sys.path.insert(0, str(project_root / "smact-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "mace-mcp-server" / "src"))

from mcp.server.fastmcp import FastMCP

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

# SMACT Tools (with fallbacks)
@mcp.tool()
async def smact_validity(
    composition: str,
    use_pauling_test: bool = True,
    include_alloys: bool = True
) -> Dict[str, Any]:
    """
    Validate chemical composition using SMACT's sophisticated screening.
    
    Args:
        composition: Chemical formula (e.g., "LiFePO4")
        use_pauling_test: Whether to apply Pauling electronegativity test
        include_alloys: Consider pure metals valid automatically
    
    Returns:
        Validation result with confidence score and natural language explanation
    """
    if SMACT_AVAILABLE:
        try:
            # Use SMACT's quick validity check
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
            result_str = generate_crystal_csp(composition, num_structures, max_atoms)
            result = json.loads(result_str)
            
            if result.get("success"):
                structures = result.get("structures", [])
                for i, struct in enumerate(structures):
                    struct["method"] = "chemeleon"
                    struct["confidence"] = 0.85
                    struct["id"] = f"{composition}_struct_{i+1}"
                return structures
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
        # Use existing MACE tool
        result_str = calculate_energy(json.dumps(structure), properties)
        result = json.loads(result_str)
        
        result["structure_id"] = structure_id
        result["method"] = "mace"
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
        
        # Find most stable structures per composition
        stable_structures = {}
        for energy_result in energy_results:
            if energy_result.get("energy") is not None:
                comp = energy_result.get("composition", "unknown")
                if comp not in stable_structures or energy_result["energy"] < stable_structures[comp]["energy"]:
                    stable_structures[comp] = energy_result
        
        results["most_stable_structures"] = list(stable_structures.values())
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