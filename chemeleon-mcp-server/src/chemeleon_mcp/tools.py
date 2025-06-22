"""Chemeleon tools for MCP server."""

import json
import os
import tempfile
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import logging

# Import Chemeleon modules
import torch
from chemeleon_dng.diffusion.diffusion_module import DiffusionModule
from chemeleon_dng.script_util import create_diffusion_module
from chemeleon_dng.download_util import get_checkpoint_path
import ase
from ase.io import write as ase_write
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

from .server import mcp

logger = logging.getLogger(__name__)

# Global model cache
_model_cache = {}

def _get_device(prefer_gpu: bool = False):
    """Get the computing device.
    
    Args:
        prefer_gpu: If True, use GPU if available. Otherwise use CPU.
    
    Returns:
        Device string ("cpu", "cuda", or "mps")
    """
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
        # Default checkpoint paths for different tasks
        default_paths = {
            "csp": "/home/ryan/crystalyseai/ckpts/chemeleon_csp_alex_mp_20_v0.0.2.ckpt",
            "dng": "/home/ryan/crystalyseai/ckpts/chemeleon_dng_alex_mp_20_v0.0.2.ckpt",
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
            # Use create_diffusion_module function for proper initialization
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

@mcp.tool(
    description="Generate crystal structures from chemical formulas using Chemeleon CSP"
)
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
            from pymatgen.core import Composition
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
        
        return json.dumps({
            "success": True,
            "num_structures": len(all_results),
            "structures": all_results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in generate_crystal_csp: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "formulas": formulas
        }, indent=2)


@mcp.tool(
    description="Get information about available Chemeleon models and benchmarks"
)
def get_model_info() -> str:
    """
    Get information about available Chemeleon models and benchmarks.
    
    Returns:
        JSON string with model information
    """
    try:
        info = {
            "available_tasks": ["csp"],
            "device": _get_device(prefer_gpu=False),
            "cached_models": list(_model_cache.keys()),
            "benchmarks": {}
        }
        
        # Check for benchmark files
        # Note: benchmark path functionality not available in current download_util
        # This can be added later if needed
        
        return json.dumps(info, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e)
        }, indent=2)

@mcp.tool(
    description="Analyse and validate generated crystal structures"
)
def analyse_structure(
    structure_dict: Dict[str, Any],
    calculate_symmetry: bool = True,
    tolerance: float = 0.1
) -> str:
    """
    Analyse a generated crystal structure.
    
    Args:
        structure_dict: Structure dictionary from generation (with cell, positions, numbers)
        calculate_symmetry: Whether to calculate space group
        tolerance: Tolerance for symmetry analysis
    
    Returns:
        JSON string with analysis results
    """
    try:
        # Reconstruct ASE Atoms
        atoms = ase.Atoms(
            numbers=structure_dict["numbers"],
            positions=structure_dict["positions"],
            cell=structure_dict["cell"],
            pbc=structure_dict.get("pbc", [True, True, True])
        )
        
        # Convert to pymatgen Structure for analysis
        adaptor = AseAtomsAdaptor()
        structure = adaptor.get_structure(atoms)
        
        analysis = {
            "formula": structure.formula,
            "volume": float(structure.volume),
            "density": float(structure.density),
            "num_sites": len(structure),
            "lattice": {
                "a": float(structure.lattice.a),
                "b": float(structure.lattice.b),
                "c": float(structure.lattice.c),
                "alpha": float(structure.lattice.alpha),
                "beta": float(structure.lattice.beta),
                "gamma": float(structure.lattice.gamma),
                "volume": float(structure.lattice.volume)
            }
        }
        
        # Calculate symmetry if requested
        if calculate_symmetry:
            try:
                from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
                sga = SpacegroupAnalyzer(structure, symprec=tolerance)
                analysis["symmetry"] = {
                    "space_group": sga.get_space_group_symbol(),
                    "space_group_number": sga.get_space_group_number(),
                    "crystal_system": sga.get_crystal_system(),
                    "point_group": sga.get_point_group_symbol()
                }
            except Exception as e:
                analysis["symmetry_error"] = str(e)
        
        return json.dumps(analysis, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e)
        }, indent=2)

@mcp.tool(
    description="Clear cached Chemeleon models from memory"
)
def clear_model_cache() -> str:
    """
    Clear all cached models from memory.
    
    Returns:
        JSON string with status
    """
    global _model_cache
    num_cleared = len(_model_cache)
    _model_cache.clear()
    
    # Force garbage collection
    import gc
    gc.collect()
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return json.dumps({
        "success": True,
        "models_cleared": num_cleared
    }, indent=2)