"""
Unified Chemistry MCP Server
Integrates SMACT, Chemeleon, and MACE for a comprehensive materials discovery workflow.
"""

import logging
import json
from typing import List, Dict, Any, Union
import sys
import os
import numpy as np
import re
import warnings
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from datetime import datetime

# Add parent directories to path for importing existing tools
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent

# Structure validation functions integrated directly

# Add paths for all the old servers
sys.path.insert(0, str(project_root / "oldmcpservers" / "smact-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "mace-mcp-server" / "src"))
# Add path for the new converter
sys.path.insert(0, str(project_root / "crystalyse"))

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Suppress PyMatgen electronegativity warnings
warnings.filterwarnings("ignore", message=".*Pauling electronegativity.*Setting to NaN.*")
warnings.filterwarnings("ignore", message=".*No Pauling electronegativity.*")

# --- Core Utility Functions ---

def make_json_serializable(obj: Any) -> Any:
    """
    Convert objects to JSON-serializable format.
    Handles numpy types, booleans, and other problematic types.
    """
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
    elif isinstance(obj, (np.complex128, np.complex64)):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    elif hasattr(obj, 'tolist'):  # Other numpy-like objects
        return obj.tolist()
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        # Try to convert to string as fallback
        try:
            return str(obj)
        except:
            return f"<non-serializable: {type(obj).__name__}>"

def validate_structure_atoms(cif_string: str) -> Dict[str, Any]:
    """
    Validate that a CIF string contains actual atoms.
    Addresses the "0 atoms" degenerate structure issue.
    """
    try:
        # Count atom sites in CIF
        atom_count = 0
        valid_elements = set()
        
        lines = cif_string.strip().split('\n')
        in_atom_loop = False
        
        for line in lines:
            line = line.strip()
            
            # Check for atom site loop
            if 'loop_' in line:
                in_atom_loop = False
            elif '_atom_site_label' in line or '_atom_site_type_symbol' in line:
                in_atom_loop = True
                continue
            elif in_atom_loop and line and not line.startswith('_'):
                # This should be an atom line
                parts = line.split()
                if len(parts) >= 4:  # label, x, y, z minimum
                    atom_count += 1
                    # Extract element from atom label
                    element_match = re.match(r'([A-Z][a-z]?)', parts[0])
                    if element_match:
                        valid_elements.add(element_match.group(1))
        
        return {
            "is_valid": atom_count > 0,
            "atom_count": atom_count,
            "elements_found": list(valid_elements),
            "error": None if atom_count > 0 else "No atoms found in CIF structure"
        }
        
    except Exception as e:
        return {
            "is_valid": False,
            "atom_count": 0,
            "elements_found": [],
            "error": f"CIF validation failed: {str(e)}"
        }

def fix_chemeleon_degenerate_structures(structures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out degenerate structures with 0 atoms from Chemeleon output.
    
    Args:
        structures: List of structure dictionaries
        
    Returns:
        Filtered list with only valid structures
    """
    valid_structures = []
    
    for i, structure in enumerate(structures):
        # Check if structure has valid CIF content
        cif_content = structure.get('cif', '')
        
        if cif_content:
            validation = validate_structure_atoms(cif_content)
            
            if validation['is_valid']:
                structure['atom_count'] = validation['atom_count']
                structure['elements'] = validation['elements_found']
                valid_structures.append(structure)
                logger.info(f"Structure {i}: Valid with {validation['atom_count']} atoms")
            else:
                logger.warning(f"Structure {i}: Degenerate - {validation['error']}")
        else:
            logger.warning(f"Structure {i}: No CIF content")
    
    return valid_structures

def fix_mace_dtype_mismatch(structure_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix MACE dtype mismatches by ensuring consistent float32 precision.
    Updated to use float32 for better compatibility with MACE models.
    """
    fixed_dict = structure_dict.copy()
    
    # Fix common dtype issues - use float32 for MACE compatibility
    dtype_fixes = {
        'positions': np.float32,
        'forces': np.float32,
        'energy': np.float32,
        'stress': np.float32,
        'cell': np.float32
    }
    
    for key, target_dtype in dtype_fixes.items():
        if key in fixed_dict:
            try:
                if isinstance(fixed_dict[key], (list, tuple)):
                    fixed_dict[key] = np.array(fixed_dict[key], dtype=target_dtype)
                elif isinstance(fixed_dict[key], np.ndarray):
                    fixed_dict[key] = fixed_dict[key].astype(target_dtype)
                elif isinstance(fixed_dict[key], (int, float)):
                    fixed_dict[key] = target_dtype(fixed_dict[key])
            except Exception as e:
                logger.warning(f"Could not fix dtype for {key}: {e}")
    
    return fixed_dict

def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safe JSON dumps that automatically handles problematic types.
    """
    try:
        # First try normal JSON serialization
        import json as json_module
        return json_module.dumps(data, **kwargs)
    except TypeError as e:
        if "not JSON serializable" in str(e):
            # Apply our fixes and try again
            logger.debug("Applying JSON serialization fixes...")
            fixed_data = make_json_serializable(data)
            import json as json_module
            return json_module.dumps(fixed_data, **kwargs)
        else:
            raise

# Initialise unified server
mcp = FastMCP("chemistry-unified")

# --- Tool Imports ---

# Import SMACT tools
try:
    from smact_mcp.tools import smact_validity
    SMACT_AVAILABLE = True
    logger.info("SMACT tools loaded successfully")
except ImportError as e:
    logger.warning(f"SMACT tools not available: {e}")
    SMACT_AVAILABLE = False

# Import Chemeleon tools directly (bypassing MCP layer)
try:
    import json
    import tempfile
    import os
    from typing import Union, List, Dict, Any, Optional
    from pathlib import Path
    
    # Import Chemeleon modules directly
    import torch
    from chemeleon_dng.diffusion.diffusion_module import DiffusionModule
    from chemeleon_dng.script_util import create_diffusion_module
    from chemeleon_dng.download_util import get_checkpoint_path
    import ase
    from ase.io import write as ase_write
    from pymatgen.core import Structure, Composition
    from pymatgen.io.ase import AseAtomsAdaptor
    
    CHEMELEON_AVAILABLE = True
    logger.info("Chemeleon tools loaded successfully")
    
    # Global model cache
    _model_cache = {}
    
    def _get_device(prefer_gpu: bool = False):
        """Get the computing device."""
        if prefer_gpu:
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        return "cpu"
    
    def _load_model(task: str = "csp", checkpoint_path: Optional[str] = None, prefer_gpu: bool = False):
        """Load or retrieve cached Chemeleon model."""
        cache_key = f"{task}_{checkpoint_path or 'default'}"
        
        if cache_key in _model_cache:
            logger.info(f"Using cached model for {cache_key}")
            return _model_cache[cache_key]
        
        logger.info(f"Loading new model for {cache_key}")
        
        # Download checkpoint if needed
        if checkpoint_path is None:
            # Use user-portable checkpoint directory
            checkpoint_dir = Path.home() / ".crystalyse" / "checkpoints"
            default_paths = {
                "csp": str(checkpoint_dir / "chemeleon_csp_alex_mp_20_v0.0.2.ckpt"),
                "dng": str(checkpoint_dir / "chemeleon_dng_alex_mp_20_v0.0.2.ckpt"),
                "guide": "."
            }
            checkpoint_path = get_checkpoint_path(task=task, default_paths=default_paths)
        
        # Load model
        device = _get_device(prefer_gpu=prefer_gpu)
        logger.info(f"Loading model on device: {device}")
        
        # Handle version compatibility for DiffusionModule
        try:
            # First try standard checkpoint loading
            diffusion_module = DiffusionModule.load_from_checkpoint(
                checkpoint_path, 
                map_location=device
            )
        except TypeError as e:
            if "optimiser_configs" in str(e):
                # Handle newer Chemeleon versions that require optimiser_configs
                logger.info("Loading model with optimiser_configs compatibility mode")
                
                # Load checkpoint to extract hyperparameters
                checkpoint = torch.load(checkpoint_path, map_location=device)
                hparams = checkpoint.get('hyper_parameters', {})
                
                # Create a new DiffusionModule instance with required parameters
                try:
                    # Get task from hyperparameters and convert to string
                    task_param = hparams.get('task', 'csp')
                    if hasattr(task_param, 'name'):  # If it's an enum, get the name
                        task_param = task_param.name.lower()
                    elif not isinstance(task_param, str):
                        task_param = str(task_param).lower()
                    
                    diffusion_module = create_diffusion_module(
                        task=task_param,
                        model_configs=hparams.get('model_configs', {}),
                        optimiser_configs=hparams.get('optimiser_configs', {
                            "optimiser": "adam",
                            "lr": 1e-4,
                            "weight_decay": 0.01,
                            "scheduler": "plateau",
                            "patience": 10,
                            "early_stopping": 20,
                            "warmup_steps": 0
                        }),
                        num_timesteps=hparams.get('num_timesteps', 1000),
                        beta_schedule_ddpm=hparams.get('beta_schedule_ddpm', 'cosine'),
                        beta_schedule_d3pm=hparams.get('beta_schedule_d3pm', 'cosine'),
                        max_atoms=hparams.get('max_atoms', 100),
                        d3pm_hybrid_coeff=hparams.get('d3pm_hybrid_coeff', 0.01),
                        sigma_begin=hparams.get('sigma_begin', 10.0),
                        sigma_end=hparams.get('sigma_end', 0.01)
                    )
                    
                    # Load the state dict manually
                    diffusion_module.load_state_dict(checkpoint['state_dict'], strict=False)
                    diffusion_module.to(device)
                    
                except Exception as create_error:
                    logger.error(f"Failed to create diffusion module: {create_error}")
                    # Final fallback - try direct loading with strict=False
                    diffusion_module = DiffusionModule.load_from_checkpoint(
                        checkpoint_path,
                        map_location=device,
                        strict=False
                    )
            else:
                raise e
        diffusion_module.eval()
        
        # Cache the model
        _model_cache[cache_key] = diffusion_module
        
        return diffusion_module
    
    def _atoms_to_dict(atoms: ase.Atoms) -> Dict[str, Any]:
        """Convert ASE Atoms to a JSON-serializable dictionary."""
        return {
            "cell": atoms.cell.tolist(),
            "positions": atoms.positions.tolist(),
            "numbers": atoms.numbers.tolist(),
            "symbols": atoms.get_chemical_symbols(),
            "formula": atoms.get_chemical_formula(),
            "volume": float(atoms.get_volume()),
            "pbc": atoms.pbc.tolist()
        }
    
    def _atoms_to_cif(atoms: ase.Atoms) -> str:
        """Convert ASE Atoms to CIF string."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.cif', delete=False) as f:
            ase_write(f.name, atoms, format='cif')
            with open(f.name, 'r') as cif_file:
                cif_content = cif_file.read()
            os.unlink(f.name)
        return cif_content
    
    def generate_crystal_csp(
        formulas: Union[str, List[str]],
        num_samples: int = 1,
        batch_size: int = 16,
        output_format: str = "cif",
        checkpoint_path: Optional[str] = None,
        prefer_gpu: bool = False
    ) -> str:
        """
        Generate crystal structures from chemical formulas using Crystal Structure Prediction.
        
        Args:
            formulas: Chemical formula(s) to generate structures for (e.g., "NaCl" or ["NaCl", "SiO2"])
            num_samples: Number of structures to generate per formula
            batch_size: Batch size for generation
            output_format: Output format - "cif" (default), "dict", or "both"
            checkpoint_path: Optional path to custom checkpoint
            prefer_gpu: If True, use GPU if available. Otherwise use CPU (default)
        
        Returns:
            JSON string with generated structures
        """
        try:
            # Handle single formula
            if isinstance(formulas, str):
                formulas = [formulas]
            
            # Load model
            model = _load_model(task="csp", checkpoint_path=checkpoint_path, prefer_gpu=prefer_gpu)
            
            # Generate structures
            all_results = []
            
            for formula in formulas:
                logger.info(f"Generating {num_samples} structures for {formula}")
                
                # Parse formula to get atom types and counts
                comp = Composition(formula)
                
                # Create atom_types and num_atoms for all samples
                batch_atom_types = []
                batch_num_atoms = []
                
                for _ in range(num_samples):
                    atomic_numbers = [el.Z for el, amt in comp.items() for _ in range(int(amt))]
                    batch_atom_types.extend(atomic_numbers)
                    batch_num_atoms.append(len(atomic_numbers))
                
                # Sample structures
                samples = model.sample(
                    task="csp",
                    atom_types=batch_atom_types,
                    num_atoms=batch_num_atoms
                )
                
                # Convert to desired format
                formula_results = []
                for i, atoms in enumerate(samples):
                    result = {
                        "formula": formula,
                        "sample_index": i
                    }
                    
                    if output_format in ["dict", "both"]:
                        result["structure"] = _atoms_to_dict(atoms)
                    
                    if output_format in ["cif", "both"]:
                        result["cif"] = _atoms_to_cif(atoms)
                    
                    formula_results.append(result)
                
                all_results.extend(formula_results)
            
            return safe_json_dumps({
                "success": True,
                "num_structures": len(all_results),
                "structures": all_results
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error in generate_crystal_csp: {e}")
            return safe_json_dumps({
                "success": False,
                "error": str(e),
                "formulas": formulas
            }, indent=2)
    
except ImportError as e:
    logger.warning(f"Chemeleon tools not available: {e}")
    CHEMELEON_AVAILABLE = False

# Import MACE tools
try:
    from mace_mcp.tools import (
        calculate_formation_energy,
    )
    MACE_AVAILABLE = True
    logger.info("MACE tools loaded successfully")
except ImportError as e:
    logger.warning(f"MACE tools not available: {e}")
    MACE_AVAILABLE = False

# Import the new converter tool
try:
    from converters import convert_cif_to_mace_input
    CONVERTER_AVAILABLE = True
    logger.info("CIF to MACE converter loaded successfully")
except ImportError as e:
    logger.warning(f"CIF to MACE converter not available: {e}")
    CONVERTER_AVAILABLE = False


# --- Direct Tool Access ---

# Expose SMACT tools
if SMACT_AVAILABLE:
    @mcp.tool()
    def validate_composition_smact(composition: str) -> str:
        """Validate a chemical composition using SMACT."""
        return smact_validity(composition)

# Expose Chemeleon tools
if CHEMELEON_AVAILABLE:
    @mcp.tool()
    def generate_structures(
        composition: str, 
        num_samples: int = 3,
        min_atoms: int = 20,
        max_formula_units: int = 4,
        output_format: str = "both"
    ) -> str:
        """
        Generate crystal structures for a composition using Chemeleon.
        
        Args:
            composition: Chemical formula (e.g., "NaCl", "Li2O")
            num_samples: Number of structures to generate per formula unit
            min_atoms: Minimum number of atoms in the unit cell (will create supercell if needed)
            max_formula_units: Maximum formula units to explore (e.g., 3 means try M₁X₁, M₂X₂, M₃X₃)
            output_format: Output format - "cif", "dict", or "both"
            
        Returns:
            JSON string with generated structures at various stoichiometries
        """
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
                formula_dict = {str(el): amt for el, amt in zip(elements, amounts)}
                
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
                        
                        # Add metadata about formula units and validate structures
                        for struct in structures:
                            struct["formula_units"] = n_units
                            struct["base_formula"] = composition
                            struct["scaled_formula"] = scaled_formula
                            
                            # Validate structure has atoms
                            if "cif" in struct:
                                validation = validate_structure_atoms(struct["cif"])
                                struct["atom_count"] = validation["atom_count"]
                                struct["is_valid"] = validation["is_valid"]
                                if not validation["is_valid"]:
                                    logger.warning(f"⚠️ Degenerate structure {scaled_formula} with {validation['atom_count']} atoms: {validation['error']}")
                                else:
                                    logger.info(f"✅ Valid structure {scaled_formula} with {validation['atom_count']} atoms")
                        
                        all_structures.extend(structures)
                        formulas_generated.append(scaled_formula)
                    else:
                        logger.warning(f"Failed to generate structures for {scaled_formula}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error generating structures for {scaled_formula}: {e}")
                    continue
            
            # Filter out degenerate structures using proper CIF validation
            logger.info(f"Applying degenerate structure filtering to {len(all_structures)} structures")
            valid_structures = fix_chemeleon_degenerate_structures(all_structures)
            degenerate_count = len(all_structures) - len(valid_structures)
            
            logger.info(f"Structure filtering: {len(valid_structures)} valid, {degenerate_count} degenerate structures filtered")
            
            if len(valid_structures) == 0:
                return safe_json_dumps({
                    "success": False,
                    "error": f"All {len(all_structures)} generated structures were degenerate (0 atoms)",
                    "structures_attempted": len(all_structures),
                    "degenerate_filtered": degenerate_count
                })
            
            # Process valid structures with enhanced analysis capabilities
            enhanced_structures = []
            logger.info(f"🔍 Processing {len(valid_structures)} valid structures for enhanced analysis...")
            logger.info(f"   • Multiple formula units: {set(s.get('scaled_formula', 'Unknown') for s in valid_structures)}")
            logger.info(f"   • Atom counts: {[s.get('atom_count', 0) for s in valid_structures]}")
            logger.info("")
            
            for structure in valid_structures:
                # Use atom_count from filtering if available, otherwise fallback to structure parsing
                num_atoms = structure.get("atom_count", len(structure.get("structure", {}).get("atom_types", [])))
                structure["original_atoms"] = num_atoms
                structure["supercell_created"] = False
                
                # Smart supercell decision: only for genuinely undersized structures
                if num_atoms < min_atoms and num_atoms >= 1:  # Avoid degenerate cases
                    # Calculate reasonable supercell dimensions with caps
                    max_final_atoms = min_atoms * 3  # Cap to avoid computational explosion
                    multiplier = max(1, int((min_atoms / num_atoms) ** (1/3)))
                    
                    # Safety checks before creating supercell
                    predicted_atoms = multiplier**3 * num_atoms
                    if predicted_atoms > max_final_atoms:
                        # Recalculate with linear scaling instead
                        multiplier = min(max_final_atoms // num_atoms, 3)  # Cap at 3x in any dimension
                        predicted_atoms = multiplier**3 * num_atoms
                    
                    # Only create supercell if it's actually beneficial and reasonable
                    if multiplier > 1 and predicted_atoms <= max_final_atoms:
                        supercell_matrix = [[multiplier, 0, 0], [0, multiplier, 0], [0, 0, multiplier]]
                        
                        logger.info(f"FALLBACK: Creating {multiplier}x{multiplier}x{multiplier} supercell for {structure['scaled_formula']} "
                                  f"(original: {num_atoms} atoms → target: {predicted_atoms} atoms)")
                        
                        # Create supercell if CIF is available
                        if "cif" in structure and SUPERCELL_CONVERTER_AVAILABLE:
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
                                        
                                        # Convert supercell CIF to dict format if needed
                                        if output_format in ["dict", "both"]:
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
            
            # Group structures by formula units for systematic analysis
            structures_by_units = {}
            logger.info(f"🔬 Grouping {len(enhanced_structures)} structures by formula units for systematic analysis...")
            for struct in enhanced_structures:
                n_units = struct["formula_units"]
                if n_units not in structures_by_units:
                    structures_by_units[n_units] = []
                structures_by_units[n_units].append(struct)
            
            return safe_json_dumps({
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
                "max_formula_units": max_formula_units,
                "degenerate_structures_filtered": degenerate_count,
                "filtering_summary": {
                    "total_generated": len(all_structures),
                    "valid_structures": len(valid_structures), 
                    "degenerate_filtered": degenerate_count
                }
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error in enhanced structure generation: {e}")
            return safe_json_dumps({
                "success": False,
                "error": str(e),
                "composition": composition
            }, indent=2)

# Expose MACE tools
if MACE_AVAILABLE:
    @mcp.tool()
    def calculate_energy_mace(structure: Dict[str, Any]) -> str:
        """Calculate formation energy using MACE."""
        # Extract mace_input from converter output if present
        if isinstance(structure, dict) and "mace_input" in structure:
            mace_structure = structure["mace_input"]
        else:
            # Assume it's already in the correct format
            mace_structure = structure
        
        return calculate_formation_energy(mace_structure)
    
    @mcp.tool()
    def relax_and_analyze_structure(
        cif_string: str,
        composition: str,
        relax: bool = True,
        calculate_hull: bool = True
    ) -> str:
        """
        Comprehensive structure analysis: relax, calculate energies, and determine stability.
        
        Args:
            cif_string: CIF format structure
            composition: Chemical formula for energy above hull calculation
            relax: Whether to relax the structure before energy calculation
            calculate_hull: Whether to calculate energy above convex hull
            
        Returns:
            JSON string with relaxed structure, energies, and stability analysis
        """
        try:
            # First validate the structure has atoms
            validation = validate_structure_atoms(cif_string)
            if not validation['is_valid']:
                return safe_json_dumps({
                    "success": False,
                    "error": f"Invalid structure: {validation['error']}",
                    "composition": composition,
                    "atom_count": validation['atom_count']
                })
            from mace_mcp.tools import relax_structure
            
            # Convert CIF to MACE input
            mace_input_result = convert_cif_to_mace_input(cif_string)
            if not mace_input_result.get("success", False):
                return safe_json_dumps({
                    "success": False,
                    "error": f"CIF conversion failed: {mace_input_result.get('error', 'Unknown error')}"
                })
            
            mace_input = mace_input_result["mace_input"]
            initial_formula = mace_input_result.get("formula", composition)
            
            # Apply MACE dtype fixes
            mace_input = fix_mace_dtype_mismatch(mace_input)
            
            results = {
                "success": True,
                "composition": composition,
                "initial_formula": initial_formula,
                "relaxation_performed": relax,
                "hull_calculation_performed": calculate_hull
            }
            
            # Step 1: Relax structure if requested
            if relax:
                logger.info(f"Relaxing structure for {composition}")
                try:
                    relax_result_str = relax_structure(
                        mace_input,
                        model_type="mace_mp",
                        size="medium", 
                        fmax=0.01,
                        optimiser="BFGS",
                        steps=200,
                        device="auto"
                    )
                    relax_result = json.loads(relax_result_str)
                    
                    if relax_result.get("status") == "completed":
                        # Use relaxed structure for energy calculations
                        final_structure = relax_result["relaxed_structure"]
                        results["relaxation"] = {
                            "converged": relax_result.get("converged", False),
                            "energy_change": relax_result.get("energy_change", 0.0),
                            "max_displacement": relax_result.get("max_displacement", 0.0),
                            "n_steps": relax_result.get("n_steps", 0)
                        }
                    else:
                        error_msg = relax_result.get('message') or relax_result.get('error', 'Unknown relaxation error')
                        logger.warning(f"Relaxation failed, using original structure: {error_msg}")
                        final_structure = mace_input
                        results["relaxation"] = {"error": error_msg}
                except Exception as e:
                    logger.error(f"Relaxation error: {e}")
                    final_structure = mace_input
                    results["relaxation"] = {"error": str(e)}
            else:
                final_structure = mace_input
            
            # Step 2: Calculate formation energy
            logger.info(f"Calculating formation energy for {composition}")
            try:
                energy_result_str = calculate_formation_energy(final_structure)
                energy_result = json.loads(energy_result_str)
                
                if energy_result.get("status") == "completed":
                    formation_energy_per_atom = energy_result["formation_energy_per_atom"]
                    total_energy = energy_result.get("total_energy", 0.0)
                    
                    results["energies"] = {
                        "formation_energy_per_atom": formation_energy_per_atom,
                        "total_energy": total_energy,
                        "calculation_model": energy_result.get("model", "mace_mp"),
                        "num_atoms": energy_result.get("num_atoms", len(final_structure.get("numbers", [])))
                    }
                else:
                    return safe_json_dumps({
                        "success": False,
                        "error": f"Energy calculation failed: {energy_result.get('error', 'Unknown error')}"
                    })
            except Exception as e:
                return safe_json_dumps({
                    "success": False,
                    "error": f"Energy calculation error: {str(e)}"
                })
            
            # Step 3: Calculate energy above convex hull if requested and pymatgen server is available
            if calculate_hull:
                logger.info(f"Calculating energy above convex hull for {composition}")
                try:
                    # Try to import and use the pymatgen MCP server functions
                    sys.path.insert(0, str(project_root / "pymatgen-mcp-server" / "src"))
                    from pymatgen_mcp.server import calculate_energy_above_hull
                    
                    hull_result = calculate_energy_above_hull(
                        composition=composition,
                        energy=formation_energy_per_atom,
                        per_atom=True
                    )
                    
                    if hull_result.get("success", False):
                        results["stability"] = {
                            "energy_above_hull": hull_result["energy_above_hull"],
                            "is_stable": hull_result["stability"]["is_stable"],
                            "is_metastable": hull_result["stability"]["is_metastable"],
                            "is_unstable": hull_result["stability"]["is_unstable"],
                            "decomposition_products": hull_result.get("decomposition", []),
                            "competing_phases": hull_result.get("competing_phases", 0)
                        }
                    else:
                        results["stability"] = {
                            "error": hull_result.get("error", "Hull calculation failed"),
                            "hull_calculation_available": False
                        }
                except Exception as e:
                    logger.warning(f"Energy above hull calculation failed: {e}")
                    results["stability"] = {
                        "error": str(e),
                        "hull_calculation_available": False
                    }
            
            # Step 4: Convert final structure back to CIF if relaxed
            if relax and "relaxed_structure" in locals():
                try:
                    # Convert relaxed structure to CIF format
                    from ase import Atoms
                    from ase.io import write
                    import tempfile
                    import os
                    
                    atoms = Atoms(
                        numbers=final_structure["numbers"],
                        positions=final_structure["positions"],
                        cell=final_structure["cell"],
                        pbc=final_structure.get("pbc", [True, True, True])
                    )
                    
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.cif', delete=False) as tmp_file:
                        tmp_filename = tmp_file.name
                    
                    write(tmp_filename, atoms, format='cif')
                    
                    with open(tmp_filename, 'r') as f:
                        relaxed_cif = f.read()
                    
                    os.unlink(tmp_filename)
                    results["relaxed_cif"] = relaxed_cif
                    
                except Exception as e:
                    logger.warning(f"Could not convert relaxed structure to CIF: {e}")
            
            return safe_json_dumps(results, indent=2)
            
        except Exception as e:
            logger.error(f"Comprehensive structure analysis failed: {e}")
            return safe_json_dumps({
                "success": False,
                "error": str(e),
                "composition": composition
            }, indent=2)

# Import and expose PyMatgen analysis tools
try:
    sys.path.insert(0, str(project_root / "pymatgen-mcp-server" / "src"))
    from pymatgen_mcp.server import analyze_space_group, calculate_energy_above_hull, analyze_coordination
    PYMATGEN_AVAILABLE = True
    logger.info("PyMatgen analysis tools loaded successfully")
except ImportError as e:
    logger.warning(f"PyMatgen analysis tools not available: {e}")
    PYMATGEN_AVAILABLE = False

# Expose PyMatgen tools
if PYMATGEN_AVAILABLE:
    @mcp.tool()
    def analyze_crystal_symmetry(
        structure_input: Union[str, Dict[str, Any]],
        symprec: float = 0.1
    ) -> Dict[str, Any]:
        """Analyze space group and crystal symmetry of a structure."""
        return analyze_space_group(structure_input, symprec=symprec)
    
    @mcp.tool()
    def calculate_stability_hull(
        composition: str,
        energy: float,
        per_atom: bool = True
    ) -> Dict[str, Any]:
        """Calculate energy above convex hull for thermodynamic stability assessment."""
        return calculate_energy_above_hull(composition, energy, per_atom)
    
    @mcp.tool()
    def analyze_structure_coordination(
        structure_input: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze coordination environment and bonding in crystal structure."""
        return analyze_coordination(structure_input)

# Expose the new converter tool
if CONVERTER_AVAILABLE:
    @mcp.tool()
    def convert_cif_to_mace(cif_string: str) -> Dict[str, Any]:
        """Converts a CIF string into a MACE-compatible dictionary."""
        return convert_cif_to_mace_input(cif_string)

# Import the new supercell converter tool
try:
    from converters import create_supercell_cif
    SUPERCELL_CONVERTER_AVAILABLE = True
    logger.info("Supercell converter loaded successfully")
except ImportError as e:
    logger.warning(f"Supercell converter not available: {e}")
    SUPERCELL_CONVERTER_AVAILABLE = False

# Expose the new supercell converter tool
if SUPERCELL_CONVERTER_AVAILABLE:
    @mcp.tool()
    def create_supercell(cif_string: str, supercell_matrix: List[List[int]]) -> Dict[str, Any]:
        """Creates a supercell from a CIF string and returns the supercell as a CIF string."""
        return create_supercell_cif(cif_string, supercell_matrix)

# Import and expose the new validation function
try:
    from converters import validate_cif_string
    VALIDATOR_AVAILABLE = True
    logger.info("CIF validator loaded successfully")
except ImportError as e:
    logger.warning(f"CIF validator not available: {e}")
    VALIDATOR_AVAILABLE = False

# Expose the validation function
if VALIDATOR_AVAILABLE:
    @mcp.tool()
    def validate_cif(cif_string: str) -> Dict[str, Any]:
        """Validate a CIF string and return diagnostic information."""
        return validate_cif_string(cif_string)


def _generate_analysis_report(results: Dict[str, Any], composition: str) -> str:
    """Generate comprehensive markdown analysis report."""
    try:
        mode = results.get("mode", "adaptive")
        summary = results.get("summary", {})
        structures = results.get("structures", [])
        energies = results.get("energies", [])
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# CrystaLyse.AI Materials Analysis Report

## Analysis Summary
- **Composition**: {composition}
- **Analysis Mode**: {mode.title()}
- **Generated**: {timestamp}
- **Structures Generated**: {summary.get('total_structures_generated', 0)}
- **Structures with Energy Data**: {summary.get('structures_with_energies', 0)}
- **Formula Units Explored**: {summary.get('formula_units_explored', 0)}

## Key Findings

### Most Stable Structures
"""
        
        # Add most stable structures
        most_stable = results.get("most_stable_structures", [])
        if most_stable:
            for i, structure in enumerate(most_stable[:5]):  # Top 5
                formula = structure.get("scaled_formula", composition)
                energy = structure.get("formation_energy_per_atom", "N/A")
                space_group = "N/A"
                if "analysis" in structure and "symmetry" in structure["analysis"]:
                    space_group = structure["analysis"]["symmetry"].get("space_group", {}).get("symbol", "N/A")
                
                report += f"""
**{i+1}. {formula}**
- Formation Energy: {energy} eV/atom
- Space Group: {space_group}
- Structure ID: {structure.get('id', 'N/A')}
"""
        
        # Add energy statistics
        if energies:
            formation_energies = [e.get("formation_energy_per_atom") for e in energies if e.get("formation_energy_per_atom") is not None]
            if formation_energies:
                report += f"""
## Energy Analysis
- **Lowest Formation Energy**: {min(formation_energies):.4f} eV/atom
- **Highest Formation Energy**: {max(formation_energies):.4f} eV/atom
- **Average Formation Energy**: {sum(formation_energies)/len(formation_energies):.4f} eV/atom
- **Energy Range**: {max(formation_energies) - min(formation_energies):.4f} eV/atom
"""
        
        # Add structural diversity
        if structures:
            space_groups = []
            crystal_systems = []
            for structure in structures:
                if "analysis" in structure and "symmetry" in structure["analysis"]:
                    sg_info = structure["analysis"]["symmetry"].get("space_group", {})
                    if "symbol" in sg_info:
                        space_groups.append(sg_info["symbol"])
                    if "crystal_system" in sg_info:
                        crystal_systems.append(sg_info["crystal_system"])
            
            unique_space_groups = list(set(space_groups))
            unique_crystal_systems = list(set(crystal_systems))
            
            report += f"""
## Structural Diversity
- **Unique Space Groups Found**: {len(unique_space_groups)}
- **Space Groups**: {', '.join(unique_space_groups) if unique_space_groups else 'N/A'}
- **Crystal Systems**: {', '.join(unique_crystal_systems) if unique_crystal_systems else 'N/A'}
"""
        
        # Add methodology
        report += f"""
## Methodology
- **Structure Generation**: Chemeleon deep learning model
- **Relaxation**: MACE machine learning potential
- **Symmetry Analysis**: PyMatGen crystallographic analysis
- **Energy Calculations**: MACE formation energy prediction
- **Mode**: {mode.title()} ({summary.get('total_structures_generated', 0)} structures sampled)

## Files Generated
"""
        
        # Add file list
        files_generated = results.get("files_generated", [])
        if files_generated:
            for file_info in files_generated:
                filename = file_info.get("filename", "Unknown")
                description = file_info.get("description", "No description")
                report += f"- **{filename}**: {description}\n"
        else:
            report += "- No additional files generated\n"
        
        report += f"""
---
*Report generated by CrystaLyse.AI v2.0-alpha*
*Analysis completed: {timestamp}*
"""
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating analysis report: {e}")
        return f"# Analysis Report Generation Failed\n\nError: {str(e)}\n\nComposition: {composition}\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

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


def _generate_pymatviz_analysis(structures: List[Dict], session_dir: Path, composition: str):
    """Generate pymatviz analysis plots for rigorous mode."""
    try:
        # Create analysis subdirectory
        analysis_dir = session_dir / f"{composition.replace(' ', '_')}_analysis"
        analysis_dir.mkdir(exist_ok=True)
        
        # Generate pymatviz analysis for the most stable structure
        if structures:
            # Find the structure with the lowest formation energy
            best_structure = None
            lowest_energy = float('inf')
            
            for structure in structures:
                if "analysis" in structure and "energies" in structure["analysis"]:
                    energy = structure["analysis"]["energies"].get("formation_energy_per_atom")
                    if energy is not None and energy < lowest_energy:
                        lowest_energy = energy
                        best_structure = structure
            
            if best_structure and "cif" in best_structure:
                # Call visualization server for pymatviz analysis
                try:
                    logger.info(f"Generating pymatviz analysis suite for {composition}")
                    
                    # Import and use the pymatviz analysis suite
                    sys.path.append(str(Path(__file__).parent.parent.parent / "visualization-mcp-server" / "src"))
                    from visualization_mcp.tools import create_pymatviz_analysis_suite
                    
                    # Generate the analysis suite with XRD, RDF, coordination analysis, etc.
                    result_str = create_pymatviz_analysis_suite(
                        cif_content=best_structure["cif"],
                        formula=composition.replace(' ', '_'),
                        output_dir=str(session_dir),
                        title=f"{composition} - Rigorous Analysis",
                        color_scheme="vesta"
                    )
                    
                    # Parse result to check if successful
                    import json
                    result = json.loads(result_str)
                    if result.get("status") == "success":
                        logger.info(f"✅ Pymatviz analysis suite created successfully")
                        logger.info(f"📊 Generated files: {result.get('analysis_files', [])}")
                    else:
                        logger.warning(f"⚠️ Pymatviz analysis had issues: {result.get('status', 'unknown')}")
                        logger.info("Creating placeholder analysis files for rigorous mode")
                        _create_placeholder_analysis_files(analysis_dir, composition)
                        
                except ImportError as import_error:
                    logger.warning(f"Visualization tools not available: {import_error}")
                    logger.info("Creating placeholder analysis files for rigorous mode")
                    _create_placeholder_analysis_files(analysis_dir, composition)
                    
                except Exception as viz_error:
                    logger.warning(f"Pymatviz visualization failed: {viz_error}")
                    logger.info("Creating placeholder analysis files for rigorous mode")
                    _create_placeholder_analysis_files(analysis_dir, composition)
        
        logger.info(f"Pymatviz analysis directory created: {analysis_dir}")
        
    except Exception as e:
        logger.error(f"Failed to generate pymatviz analysis: {e}")


def _create_placeholder_analysis_files(analysis_dir: Path, composition: str):
    """Create placeholder analysis files when pymatviz is not available."""
    try:
        # Create placeholder files that would normally be generated by pymatviz
        placeholder_files = [
            f"XRD_Pattern_{composition.replace(' ', '_')}.pdf",
            f"RDF_Analysis_{composition.replace(' ', '_')}.pdf", 
            f"Coordination_Analysis_{composition.replace(' ', '_')}.pdf",
            f"analysis_report.html"
        ]
        
        for filename in placeholder_files:
            placeholder_path = analysis_dir / filename
            with open(placeholder_path, 'w') as f:
                if filename.endswith('.pdf'):
                    f.write(f"% Placeholder PDF for {filename}\n% Pymatviz analysis would generate actual plots here\n")
                elif filename.endswith('.html'):
                    f.write(f"""<!DOCTYPE html>
<html>
<head><title>{composition} Analysis Report</title></head>
<body>
<h1>{composition} Analysis Report</h1>
<p>This is a placeholder report. In a complete implementation, pymatviz would generate:</p>
<ul>
<li>XRD patterns</li>
<li>Radial distribution functions</li>
<li>Coordination environment analysis</li>
<li>Interactive visualizations</li>
</ul>
</body>
</html>""")
        
        logger.info(f"Created {len(placeholder_files)} placeholder analysis files")
        
    except Exception as e:
        logger.error(f"Failed to create placeholder analysis files: {e}")


def _update_session_metadata(session_dir: Path, composition: str, mode: str, files_generated: List[Dict]):
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
        
        metadata["files_generated"].extend(files_generated)
        metadata["last_updated"] = datetime.now().isoformat()
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Updated session metadata: {metadata_file}")
        
    except Exception as e:
        logger.error(f"Failed to update session metadata: {e}")


@mcp.tool()
def comprehensive_materials_analysis(
    composition: str,
    mode: str,
    num_samples: int = 4,
    max_formula_units: int = 4,
    min_atoms: int = 20,
    relax_structures: bool = True,
    analyze_symmetry: bool = True,
    calculate_hull: bool = True,
    create_report: bool = True
) -> str:
    """
    Complete materials discovery pipeline with intelligent parameter selection
    based on analysis mode and LLM clarification.
    
    Args:
        composition: Chemical formula (e.g., "CuO", "Li2O")
        mode: Analysis mode - REQUIRED ("creative", "rigorous", "adaptive")
        num_samples: Number of structures per formula unit (auto if None)
        max_formula_units: Maximum formula units to explore (auto if None)
        min_atoms: Minimum atoms per cell (will create supercells if needed)
        relax_structures: Whether to relax structures with MACE
        analyze_symmetry: Whether to perform space group analysis
        calculate_hull: Whether to calculate energy above convex hull
        create_report: Whether to generate comprehensive markdown report
        
    Returns:
        JSON with complete analysis results and generated files
    """
    try:
        # Validate required mode parameter
        valid_modes = ["creative", "adaptive", "rigorous"]
        if not mode or mode not in valid_modes:
            error_msg = f"Mode parameter is required and must be one of: {valid_modes}. Received: {mode}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg,
                "composition": composition
            })
        
        # Intelligent parameter selection based on mode
        mode_params = {
            "creative": {"num_samples": 3, "max_formula_units": 3},
            "adaptive": {"num_samples": 4, "max_formula_units": 4},
            "rigorous": {"num_samples": 6, "max_formula_units": 5}
        }
        
        # Use mode-specific defaults if using default values
        if num_samples == 4 and max_formula_units == 4:  # Default values, apply mode-specific
            mode_specific = mode_params.get(mode, mode_params["adaptive"])
            num_samples = mode_specific["num_samples"]
            max_formula_units = mode_specific["max_formula_units"]
        
        # Log the enhanced analysis parameters
        logger.info(f"🔬 Enhanced analysis parameters:")
        logger.info(f"   • Mode: {mode}")
        logger.info(f"   • Samples per formula unit: {num_samples}")
        logger.info(f"   • Formula units to explore: {max_formula_units}")
        logger.info(f"   • Expected total structures: {num_samples * max_formula_units}")
        logger.info(f"   • Structure relaxation: {'✅' if relax_structures else '❌'}")
        logger.info(f"   • Space group analysis: {'✅' if analyze_symmetry else '❌'}")
        logger.info(f"   • Energy above hull: {'✅' if calculate_hull else '❌'}")
        logger.info(f"   • Scientific reporting: {'✅' if create_report else '❌'}")
        logger.info("")
        logger.info("🚀 Expected enhancements:")
        logger.info(f"   • {num_samples * max_formula_units}x structural diversity vs single structure")
        logger.info(f"   • Proper space groups replacing P1 defaults")
        logger.info(f"   • Thermodynamic stability assessment")
        logger.info(f"   • Formation energy normalization")
        logger.info("")
        
        logger.info(f"Starting comprehensive materials analysis for {composition} in {mode} mode")
        logger.info(f"Parameters: {num_samples} samples per formula unit, {max_formula_units} formula units")
        
        results = {
            "success": True,
            "composition": composition,
            "mode": mode,
            "analysis_parameters": {
                "num_samples": num_samples,
                "max_formula_units": max_formula_units,
                "min_atoms": min_atoms,
                "relax_structures": relax_structures,
                "analyze_symmetry": analyze_symmetry,
                "calculate_hull": calculate_hull,
                "create_report": create_report,
                "parameter_selection": "intelligent_mode_based"
            },
            "structures": [],
            "energies": [],
            "symmetry_analysis": [],
            "stability_analysis": [],
            "most_stable_structures": {},
            "files_generated": [],
            "summary": {}
        }
        
        # Step 1: Generate diverse structures with different formula units
        logger.info(f"Step 1: Generating structures for {composition}")
        
        if not CHEMELEON_AVAILABLE:
            return safe_json_dumps({
                "success": False,
                "error": "Chemeleon structure generation is not available. Please install chemeleon-dng package."
            }, indent=2)
        
        structures_result_str = generate_structures(
            composition=composition,
            num_samples=num_samples,
            min_atoms=min_atoms,
            max_formula_units=max_formula_units,
            output_format="both"
        )
        structures_result = json.loads(structures_result_str)
        
        if not structures_result.get("success", False):
            return safe_json_dumps({
                "success": False,
                "error": f"Structure generation failed: {structures_result.get('error', 'Unknown error')}"
            }, indent=2)
        
        results["structures"] = structures_result["structures"]
        logger.info(f"Generated {len(results['structures'])} structures across {len(structures_result.get('formulas_generated', []))} formula units")
        
        # Step 2: Analyze each structure
        for i, structure in enumerate(results["structures"]):
            struct_id = f"{structure['scaled_formula']}_sample_{structure['sample_index']}"
            logger.info(f"Analyzing structure {i+1}/{len(results['structures'])}: {struct_id}")
            
            try:
                # Get CIF for analysis
                cif_content = structure.get("cif", "")
                if not cif_content:
                    logger.warning(f"No CIF available for {struct_id}")
                    continue
                
                struct_results = {
                    "structure_id": struct_id,
                    "formula": structure["scaled_formula"],
                    "formula_units": structure["formula_units"],
                    "original_atoms": structure.get("original_atoms", 0),
                    "supercell_created": structure.get("supercell_created", False)
                }
                
                # Comprehensive analysis using the new tool
                if relax_structures or calculate_hull:
                    analysis_result_str = relax_and_analyze_structure(
                        cif_string=cif_content,
                        composition=structure["scaled_formula"],
                        relax=relax_structures,
                        calculate_hull=calculate_hull
                    )
                    analysis_result = json.loads(analysis_result_str)
                    
                    if analysis_result.get("success", False):
                        struct_results.update({
                            "energies": analysis_result.get("energies", {}),
                            "relaxation": analysis_result.get("relaxation", {}),
                            "stability": analysis_result.get("stability", {})
                        })
                        
                        # Use relaxed CIF if available
                        if "relaxed_cif" in analysis_result:
                            cif_content = analysis_result["relaxed_cif"]
                            struct_results["relaxed_cif_available"] = True
                    else:
                        logger.warning(f"Energy/relaxation analysis failed for {struct_id}: {analysis_result.get('error')}")
                
                # Symmetry analysis
                if analyze_symmetry and PYMATGEN_AVAILABLE:
                    try:
                        symmetry_result = analyze_crystal_symmetry(cif_content)
                        if symmetry_result.get("success", False):
                            struct_results["symmetry"] = {
                                "space_group": symmetry_result["space_group"],
                                "crystal_system": symmetry_result["space_group"]["crystal_system"],
                                "lattice_parameters": symmetry_result["lattice_parameters"]
                            }
                    except Exception as e:
                        logger.warning(f"Symmetry analysis failed for {struct_id}: {e}")
                
                results["structures"][i]["analysis"] = struct_results
                
                # Track energies for ranking
                if "energies" in struct_results:
                    results["energies"].append({
                        "structure_id": struct_id,
                        "formula": structure["scaled_formula"],
                        "formation_energy_per_atom": struct_results["energies"].get("formation_energy_per_atom"),
                        "energy_above_hull": struct_results.get("stability", {}).get("energy_above_hull"),
                        "is_stable": struct_results.get("stability", {}).get("is_stable", False)
                    })
                
            except Exception as e:
                logger.error(f"Analysis failed for structure {struct_id}: {e}")
                continue
        
        # Step 3: Find most stable structures by formula unit
        if results["energies"]:
            # Group by formula
            by_formula = {}
            for energy_data in results["energies"]:
                formula = energy_data["formula"]
                if formula not in by_formula:
                    by_formula[formula] = []
                by_formula[formula].append(energy_data)
            
            # Find most stable for each formula
            for formula, energy_list in by_formula.items():
                # Sort by formation energy per atom (most negative first)
                stable_energies = [e for e in energy_list if e["formation_energy_per_atom"] is not None]
                if stable_energies:
                    most_stable = min(stable_energies, key=lambda x: x["formation_energy_per_atom"])
                    results["most_stable_structures"][formula] = most_stable
        
        # Step 4: Generate summary statistics
        results["summary"] = {
            "total_structures_generated": len(results["structures"]),
            "structures_with_energies": len(results["energies"]),
            "formula_units_explored": len(set(s["formula_units"] for s in results["structures"])),
            "most_stable_by_formula": len(results["most_stable_structures"]),
            "stable_phases_found": len([e for e in results["energies"] if e.get("is_stable", False)]),
            "average_atoms_per_structure": sum(s["atom_count"] for s in results["structures"]) / len(results["structures"]) if results["structures"] else 0
        }
        
        # Step 5: Generate comprehensive report with session-based file organization
        if create_report:
            try:
                report_content = _generate_analysis_report(results, composition)
                
                # Create session-based directory structure
                session_dir = _create_session_directory(composition, mode)
                
                # Save markdown report
                report_filename = f"{composition.replace(' ', '_')}_{mode}_analysis.md"
                report_path = session_dir / report_filename
                
                with open(report_path, 'w') as f:
                    f.write(report_content)
                
                results["files_generated"].append({
                    "type": "analysis_report",
                    "filename": report_filename,
                    "path": str(report_path),
                    "description": f"Comprehensive materials analysis report ({mode} mode)"
                })
                
                # Save CIF files for all structures
                for i, structure in enumerate(results["structures"]):
                    if "cif" in structure and structure["cif"]:
                        # Generate meaningful filename with formula and structure info
                        formula = structure.get('scaled_formula', composition)
                        struct_id = structure.get('id', f'structure_{i+1}')
                        cif_filename = f"{formula.replace(' ', '_')}_{struct_id}.cif"
                        cif_path = session_dir / cif_filename
                        
                        with open(cif_path, 'w') as f:
                            f.write(structure["cif"])
                        
                        results["files_generated"].append({
                            "type": "cif_file", 
                            "filename": cif_filename,
                            "path": str(cif_path),
                            "description": f"Crystal structure file for {formula} ({struct_id})"
                        })
                        
                        logger.info(f"Saved CIF file: {cif_path}")
                
                # For rigorous mode, generate pymatviz analysis plots
                if mode == "rigorous" and results["structures"]:
                    try:
                        _generate_pymatviz_analysis(results["structures"], session_dir, composition)
                    except Exception as e:
                        logger.warning(f"Pymatviz analysis failed: {e}")
                
                # Update session metadata
                _update_session_metadata(session_dir, composition, mode, results["files_generated"])
                
                logger.info(f"Generated analysis files in session directory: {session_dir}")
                
            except Exception as e:
                logger.error(f"🚨 CRITICAL: Report generation failed: {e}", exc_info=True)
                print(f"🚨 CRITICAL ERROR - File saving failed: {e}")  # Force visibility
        
        # Update summary with final statistics
        results["summary"]["files_generated"] = len(results["files_generated"])
        results["summary"]["analysis_mode"] = mode
        results["summary"]["analysis_successful"] = True
        
        logger.info(f"Comprehensive analysis complete for {composition} in {mode} mode")
        return safe_json_dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Comprehensive materials analysis failed: {e}")
        return safe_json_dumps({
            "success": False,
            "error": str(e),
            "composition": composition,
            "mode": mode
        }, indent=2)


@mcp.tool()
def save_analysis_to_files(
    analysis_results: str,
    composition: str,
    mode: str = "manual",
    session_name: str = None
) -> str:
    """
    Save analysis results to files during a chat session.
    
    This tool allows users to explicitly save results to CIF and markdown files
    at any point during a conversation, useful for saving intermediate results
    or when analysis modes switch dynamically.
    
    Args:
        analysis_results: JSON string containing analysis results
        composition: Chemical composition being analyzed
        mode: Analysis mode for file naming
        session_name: Optional custom session name
        
    Returns:
        JSON string with saved file information
    """
    try:
        # Parse the analysis results
        try:
            results = json.loads(analysis_results)
        except json.JSONDecodeError as e:
            return safe_json_dumps({
                "success": False,
                "error": f"Invalid JSON in analysis_results: {e}"
            })
        
        # Create session directory (reuse existing or create new)
        if session_name:
            session_id = f"session_{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
            
        project_root_path = Path(__file__).parent.parent.parent.parent.parent
        session_dir = project_root_path / "all-runtime-output" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        files_saved = []
        
        # Save markdown report if results contain structures/analysis
        if results.get("structures") or results.get("summary"):
            report_filename = f"{composition.replace(' ', '_')}_{mode}_analysis.md"
            report_path = session_dir / report_filename
            
            # Generate report content
            if "summary" in results:
                report_content = _generate_analysis_report(results, composition)
            else:
                # Simple report for basic results
                report_content = f"""# Analysis Results: {composition}

**Mode**: {mode}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Results Summary

```json
{json.dumps(results, indent=2)}
```

*Generated by CrystaLyse.AI*
"""
            
            with open(report_path, 'w') as f:
                f.write(report_content)
            
            files_saved.append({
                "type": "analysis_report",
                "filename": report_filename,
                "path": str(report_path),
                "description": f"Analysis report for {composition} ({mode} mode)"
            })
        
        # Save CIF files if structures are available
        if "structures" in results:
            for i, structure in enumerate(results["structures"]):
                if "cif" in structure and structure["cif"]:
                    formula = structure.get('scaled_formula', composition)
                    struct_id = structure.get('id', f'structure_{i+1}')
                    cif_filename = f"{formula.replace(' ', '_')}_{struct_id}.cif"
                    cif_path = session_dir / cif_filename
                    
                    with open(cif_path, 'w') as f:
                        f.write(structure["cif"])
                    
                    files_saved.append({
                        "type": "cif_file",
                        "filename": cif_filename,
                        "path": str(cif_path),
                        "description": f"Crystal structure file for {formula} ({struct_id})"
                    })
        
        # Update session metadata
        _update_session_metadata(session_dir, composition, mode, files_saved)
        
        logger.info(f"Saved {len(files_saved)} files to session directory: {session_dir}")
        
        return safe_json_dumps({
            "success": True,
            "session_directory": str(session_dir),
            "files_saved": files_saved,
            "total_files": len(files_saved)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to save analysis to files: {e}")
        return safe_json_dumps({
            "success": False,
            "error": str(e),
            "composition": composition,
            "mode": mode
        }, indent=2)


@mcp.tool()
def list_session_files(session_directory: str = None) -> str:
    """
    List files in a specific session directory or show recent sessions.
    
    Args:
        session_directory: Path to specific session directory, or None for recent sessions
        
    Returns:
        JSON string with session and file information
    """
    try:
        project_root_path = Path(__file__).parent.parent.parent.parent.parent
        output_dir = project_root_path / "all-runtime-output"
        
        if session_directory:
            # Show specific session
            session_path = Path(session_directory)
            if not session_path.exists():
                return safe_json_dumps({
                    "success": False,
                    "error": f"Session directory does not exist: {session_directory}"
                })
            
            files = []
            for file_path in session_path.iterdir():
                if file_path.is_file():
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime
                    })
            
            return safe_json_dumps({
                "success": True,
                "session_directory": str(session_path),
                "files": files,
                "total_files": len(files)
            }, indent=2)
            
        else:
            # Show recent sessions
            if not output_dir.exists():
                return safe_json_dumps({
                    "success": True,
                    "sessions": [],
                    "total_sessions": 0
                })
            
            sessions = []
            session_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
            
            for session_dir in sorted(session_dirs, reverse=True)[:10]:  # Last 10 sessions
                files = list(session_dir.glob("*"))
                sessions.append({
                    "name": session_dir.name,
                    "path": str(session_dir),
                    "file_count": len(files),
                    "created": session_dir.stat().st_ctime
                })
            
            return safe_json_dumps({
                "success": True,
                "sessions": sessions,
                "total_sessions": len(sessions)
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to list session files: {e}")
        return safe_json_dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


def _generate_analysis_report(results: Dict[str, Any], composition: str) -> str:
    """Generate a comprehensive markdown report of the materials analysis."""
    
    mode = results.get("mode", "unknown")
    report = f"""# Materials Analysis Report: {composition}

**Analysis Mode**: {mode.title()}  
**Parameter Selection**: {results['analysis_parameters'].get('parameter_selection', 'manual')}

## Analysis Summary

- **Composition**: {composition}
- **Analysis Mode**: {mode.title()}
- **Total Structures Generated**: {results['summary']['total_structures_generated']}
- **Formula Units Explored**: {results['summary']['formula_units_explored']}
- **Structures with Energy Data**: {results['summary']['structures_with_energies']}
- **Stable Phases Found**: {results['summary']['stable_phases_found']}

---

## Most Stable Structures by Formula Unit

"""
    
    # Add most stable structures
    if results["most_stable_structures"]:
        for formula, stable_data in results["most_stable_structures"].items():
            formation_energy = stable_data.get("formation_energy_per_atom", "N/A")
            energy_above_hull = stable_data.get("energy_above_hull", "N/A")
            is_stable = stable_data.get("is_stable", False)
            stability_status = "✅ Stable" if is_stable else "⚠️ Metastable/Unstable"
            
            # Format energy values
            formation_str = f"{formation_energy:.4f} eV/atom" if isinstance(formation_energy, (int, float)) else str(formation_energy)
            hull_str = f"{energy_above_hull:.4f} eV/atom" if isinstance(energy_above_hull, (int, float)) else str(energy_above_hull)
            
            report += f"""
### {formula}
- **Formation Energy**: {formation_str}
- **Energy Above Hull**: {hull_str}
- **Stability**: {stability_status}
- **Structure ID**: {stable_data["structure_id"]}

"""
    
    # Add detailed structure information
    report += """
---

## Detailed Structure Analysis

| Structure ID | Formula | Formula Units | Atoms | Space Group | Formation Energy (eV/atom) | E_hull (eV/atom) | Stable |
|-------------|---------|---------------|-------|-------------|----------------------------|------------------|---------|
"""
    
    for structure in results["structures"]:
        if "analysis" in structure:
            analysis = structure["analysis"]
            struct_id = analysis.get("structure_id", "N/A")
            formula = analysis.get("formula", "N/A")
            formula_units = analysis.get("formula_units", "N/A")
            atoms = analysis.get("original_atoms", "N/A")
            
            # Space group info
            space_group = "N/A"
            if "symmetry" in analysis:
                sg_info = analysis["symmetry"].get("space_group", {})
                space_group = f"{sg_info.get('symbol', 'N/A')} ({sg_info.get('number', 'N/A')})"
            
            # Energy info
            formation_energy = "N/A"
            if "energies" in analysis:
                fe = analysis["energies"].get("formation_energy_per_atom")
                if fe is not None:
                    formation_energy = f"{fe:.4f}"
            
            # Hull energy
            hull_energy = "N/A"
            is_stable = "N/A"
            if "stability" in analysis:
                he = analysis["stability"].get("energy_above_hull")
                if he is not None:
                    hull_energy = f"{he:.4f}"
                    is_stable = "✅" if analysis["stability"].get("is_stable", False) else "❌"
            
            report += f"| {struct_id} | {formula} | {formula_units} | {atoms} | {space_group} | {formation_energy} | {hull_energy} | {is_stable} |\n"
    
    # Add analysis parameters
    report += f"""

---

## Analysis Parameters ({mode.title()} Mode)

- **Number of samples per formula unit**: {results['analysis_parameters']['num_samples']}
- **Maximum formula units explored**: {results['analysis_parameters']['max_formula_units']}
- **Minimum atoms per unit cell**: {results['analysis_parameters']['min_atoms']}
- **Structure relaxation performed**: {'✅' if results['analysis_parameters']['relax_structures'] else '❌'}
- **Symmetry analysis performed**: {'✅' if results['analysis_parameters']['analyze_symmetry'] else '❌'}
- **Energy above hull calculated**: {'✅' if results['analysis_parameters']['calculate_hull'] else '❌'}
- **Parameter selection method**: {results['analysis_parameters'].get('parameter_selection', 'manual')}

---

## Files Generated

"""
    
    if results["files_generated"]:
        for file_info in results["files_generated"]:
            report += f"- **{file_info['type']}**: `{file_info['filename']}` - {file_info['description']}\n"
    else:
        report += "No additional files generated.\n"
    
    report += f"""

---

*Report generated by CrystaLyse.AI v2.0-alpha*  
*Analysis completed with enhanced structure generation, MACE relaxation, and PyMatgen analysis*  
*Mode: {mode.title()} - Intelligent parameter selection based on analysis requirements*
"""
    
    return report


# Add visualization function after existing tools
@mcp.tool()
def create_structure_visualization(
    cif_content: str,
    formula: str,
    mode: str = "rigorous",
    title: str = "Crystal Structure"
) -> str:
    """Create comprehensive visualization for rigorous mode structures."""
    try:
        # Use dedicated runtime output directory
        project_root = Path(__file__).parent.parent.parent.parent.parent
        output_dir = str(project_root / "all-runtime-output")
        
        # Import and use visualization tools
        from visualization_mcp.tools import create_rigorous_visualization
        return create_rigorous_visualization(cif_content, formula, output_dir, title)
        
    except Exception as e:
        return safe_json_dumps({
            "type": "visualization",
            "status": "error",
            "error": f"Rigorous visualization failed: {str(e)}"
        })

# --- Health Check ---
@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check health of all integrated chemistry tools"""
    health = {
        "server": "chemistry-unified",
        "status": "healthy",
        "tools": {
            "smact": "available" if SMACT_AVAILABLE else "unavailable",
            "chemeleon": "available" if CHEMELEON_AVAILABLE else "unavailable",
            "mace": "available" if MACE_AVAILABLE else "unavailable",
            "converter": "available" if CONVERTER_AVAILABLE else "unavailable",
        },
    }
    if not all(health["tools"].values()):
        health["status"] = "degraded"
    return health

# --- Server Startup ---
def main():
    """Main entry point for the chemistry-unified-server."""
    logger.info("Starting Chemistry Unified MCP Server")
    logger.info(f"Available tools: SMACT={SMACT_AVAILABLE}, Chemeleon={CHEMELEON_AVAILABLE}, MACE={MACE_AVAILABLE}, Converter={CONVERTER_AVAILABLE}")
    mcp.run()

if __name__ == "__main__":
    main()