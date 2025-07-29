"""
Unified Chemistry MCP Server
Integrates SMACT, Chemeleon, and MACE for a comprehensive materials discovery workflow.
"""

import logging
import json
from typing import List, Dict, Any
import sys
import os
from mcp.server.fastmcp import FastMCP
from pathlib import Path

# Add parent directories to path for importing existing tools
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
# Add paths for all the old servers
sys.path.insert(0, str(project_root / "oldmcpservers" / "smact-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "mace-mcp-server" / "src"))
# Add path for the new converter
sys.path.insert(0, str(project_root / "crystalyse"))

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

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
    def generate_structures(composition: str, num_samples: int = 3) -> str:
        """Generate crystal structures for a composition using Chemeleon."""
        return generate_crystal_csp(composition, num_samples=num_samples, output_format="both")

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
        return json.dumps({
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