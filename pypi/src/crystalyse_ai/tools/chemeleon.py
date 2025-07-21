"""Chemeleon tools for MCP server."""

import json
import os
import tempfile
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import logging

# Import Chemeleon modules with automatic installation
import torch
import ase
from ase.io import write as ase_write
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

logger = logging.getLogger(__name__)

# Import Chemeleon with auto-installation
try:
    from .chemeleon_installer import import_chemeleon
    DiffusionModule, create_diffusion_module, get_checkpoint_path = import_chemeleon()
    CHEMELEON_AVAILABLE = True
    logger.info("Chemeleon imported successfully")
except ImportError as e:
    logger.warning(f"Chemeleon not available: {e}")
    DiffusionModule = None
    create_diffusion_module = None
    get_checkpoint_path = None
    CHEMELEON_AVAILABLE = False

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

def _ensure_checkpoints_in_correct_location():
    """Ensure checkpoints are downloaded to the correct location."""
    import tarfile
    import requests
    from tqdm import tqdm
    
    # Always use the same checkpoint directory in user's home
    checkpoint_dir = Path.home() / ".crystalyse" / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Expected checkpoint files
    expected_files = [
        "chemeleon_csp_alex_mp_20_v0.0.2.ckpt",
        "chemeleon_dng_alex_mp_20_v0.0.2.ckpt",
        "chemeleon_csp_mp_20_v0.0.2.ckpt",
        "chemeleon_dng_mp_20_v0.0.2.ckpt"
    ]
    
    # Check if all checkpoints exist
    all_exist = all((checkpoint_dir / f).exists() for f in expected_files)
    
    if all_exist:
        logger.info("Checkpoints already exist in correct location")
        return checkpoint_dir
    
    # Download checkpoints directly to the correct location
    logger.info(f"Downloading checkpoints to {checkpoint_dir}...")
    
    # Figshare URL from Chemeleon
    FIGSHARE_URL = "https://figshare.com/ndownloader/files/54966305"
    
    try:
        # Download tar.gz file
        tar_file = checkpoint_dir / "checkpoints.tar.gz"
        
        response = requests.get(FIGSHARE_URL, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get("content-length", 0))
        
        with open(tar_file, "wb") as f, tqdm(
            desc="Downloading checkpoints",
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Extract directly to checkpoint directory
        logger.info("Extracting checkpoints...")
        with tarfile.open(tar_file, "r:gz") as tar:
            # Extract files, handling the ckpts/ prefix in the archive
            for member in tar.getmembers():
                if member.name.startswith("ckpts/") and member.name.endswith(".ckpt"):
                    # Remove the ckpts/ prefix when extracting
                    member.name = os.path.basename(member.name)
                    tar.extract(member, path=checkpoint_dir)
        
        # Clean up tar file
        tar_file.unlink()
        
        logger.info(f"Checkpoints downloaded and extracted to {checkpoint_dir}")
        
    except Exception as e:
        logger.error(f"Failed to download checkpoints: {e}")
        raise
    
    return checkpoint_dir

def _load_model(task: str = "csp", checkpoint_path: Optional[str] = None, prefer_gpu: bool = False):
    """Load or retrieve cached Chemeleon model."""
    if not CHEMELEON_AVAILABLE:
        raise ImportError("Chemeleon is not available. Please check installation.")
    
    cache_key = f"{task}_{checkpoint_path or 'default'}"
    
    if cache_key in _model_cache:
        logger.info(f"Using cached model for {cache_key}")
        return _model_cache[cache_key]
    
    logger.info(f"Loading new model for {cache_key}")
    
    # Download checkpoint if needed
    if checkpoint_path is None:
        # Ensure checkpoints are in the correct location
        checkpoint_dir = _ensure_checkpoints_in_correct_location()
        
        # Map task to checkpoint file
        checkpoint_map = {
            "csp": "chemeleon_csp_alex_mp_20_v0.0.2.ckpt",
            "dng": "chemeleon_dng_alex_mp_20_v0.0.2.ckpt"
        }
        
        if task in checkpoint_map:
            checkpoint_path = str(checkpoint_dir / checkpoint_map[task])
            
            # Verify the checkpoint exists
            if not Path(checkpoint_path).exists():
                raise FileNotFoundError(
                    f"Checkpoint not found: {checkpoint_path}\n"
                    f"Please run 'crystalyse check --install' to download checkpoints."
                )
        else:
            # For guide or other tasks, use default
            checkpoint_path = "."
    
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
    if not CHEMELEON_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "Chemeleon is not available. It will be installed automatically on first use.",
            "formulas": formulas if isinstance(formulas, list) else [formulas]
        }, indent=2)
    
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


def get_model_info() -> str:
    """
    Get information about available Chemeleon models and benchmarks.
    
    Returns:
        JSON string with model information
    """
    if not CHEMELEON_AVAILABLE:
        return json.dumps({
            "error": "Chemeleon is not available. It will be installed automatically on first use."
        }, indent=2)
    
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
    # This function doesn't need Chemeleon, just pymatgen and ASE
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