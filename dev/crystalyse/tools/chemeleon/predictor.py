"""Chemeleon crystal structure prediction using direct API (no file I/O)."""

import logging
import os

import ase
import torch
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Global model cache
_model_cache = {}


class CrystalStructure(BaseModel):
    """Predicted crystal structure."""

    formula: str
    cell: list[list[float]]
    positions: list[list[float]]
    numbers: list[int]
    symbols: list[str]
    volume: float
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class PredictionResult(BaseModel):
    """Structure prediction result."""

    success: bool
    formula: str
    predicted_structures: list[CrystalStructure] = Field(default_factory=list)
    computation_time: float | None = None
    method: str = "chemeleon"
    checkpoint_used: str = ""
    error: str | None = None


def _get_device(prefer_gpu: bool = True):
    """Get the computing device - auto-detects GPU by default."""
    if prefer_gpu:
        if torch.cuda.is_available():
            logger.info("Chemeleon using CUDA GPU")
            return "cuda"
        elif torch.backends.mps.is_available():
            logger.info("Chemeleon using MPS (Apple Silicon)")
            return "mps"
    logger.info("Chemeleon using CPU")
    return "cpu"


def _load_model(task: str = "csp", checkpoint_path: str | None = None, prefer_gpu: bool = True):
    """Load or retrieve cached Chemeleon model."""
    from chemeleon_dng.diffusion.diffusion_module import DiffusionModule
    from chemeleon_dng.script_util import create_diffusion_module

    from .checkpoint_manager import get_checkpoint_path as get_managed_checkpoint_path

    cache_key = f"{task}_{checkpoint_path or 'default'}"

    if cache_key in _model_cache:
        logger.info(f"Using cached model for {cache_key}")
        return _model_cache[cache_key]

    logger.info(f"Loading new model for {cache_key}")

    # Get checkpoint path using our checkpoint manager
    # This handles auto-download to ~/.cache/crystalyse/chemeleon_checkpoints/
    # or uses custom directory from CHEMELEON_CHECKPOINT_DIR environment variable
    if checkpoint_path is None:
        # Check for custom checkpoint directory (optional)
        custom_dir = os.getenv("CHEMELEON_CHECKPOINT_DIR")
        checkpoint_path = str(get_managed_checkpoint_path(task=task, custom_dir=custom_dir))

    # Load model
    device = _get_device(prefer_gpu=prefer_gpu)
    logger.info(f"Loading checkpoint: {checkpoint_path}")
    logger.info(f"Loading model on device: {device}")

    # Handle version compatibility for DiffusionModule
    try:
        diffusion_module = DiffusionModule.load_from_checkpoint(
            checkpoint_path, map_location=device
        )
        diffusion_module.to(device)  # Ensure model is on correct device
    except TypeError as e:
        if "optimiser_configs" in str(e):
            logger.info("Loading model with optimiser_configs compatibility mode")

            checkpoint = torch.load(checkpoint_path, map_location=device)
            hparams = checkpoint.get("hyper_parameters", {})

            task_param = hparams.get("task", "csp")
            if hasattr(task_param, "name"):
                task_param = task_param.name.lower()
            elif not isinstance(task_param, str):
                task_param = str(task_param).lower()

            diffusion_module = create_diffusion_module(
                task=task_param,
                model_configs=hparams.get("model_configs", {}),
                optimiser_configs=hparams.get(
                    "optimiser_configs",
                    {
                        "optimiser": "adam",
                        "lr": 1e-4,
                        "weight_decay": 0.01,
                        "scheduler": "plateau",
                        "patience": 10,
                        "early_stopping": 20,
                        "warmup_steps": 0,
                    },
                ),
                num_timesteps=hparams.get("num_timesteps", 1000),
                beta_schedule_ddpm=hparams.get("beta_schedule_ddpm", "cosine"),
                beta_schedule_d3pm=hparams.get("beta_schedule_d3pm", "cosine"),
                max_atoms=hparams.get("max_atoms", 100),
                d3pm_hybrid_coeff=hparams.get("d3pm_hybrid_coeff", 0.01),
                sigma_begin=hparams.get("sigma_begin", 10.0),
                sigma_end=hparams.get("sigma_end", 0.01),
            )

            diffusion_module.load_state_dict(checkpoint["state_dict"], strict=False)
            diffusion_module.to(device)
        else:
            raise e

    diffusion_module.eval()

    # Log actual device for verification (helps debug HPC GPU issues)
    try:
        actual_device = next(diffusion_module.parameters()).device
        logger.info(f"Model verified on device: {actual_device}")
    except StopIteration:
        logger.warning("Could not verify model device (no parameters found)")

    _model_cache[cache_key] = diffusion_module

    return diffusion_module


def _atoms_to_structure_dict(atoms: ase.Atoms, formula: str) -> CrystalStructure:
    """Convert ASE Atoms to CrystalStructure model."""
    return CrystalStructure(
        formula=formula,
        cell=atoms.cell.tolist(),
        positions=atoms.positions.tolist(),
        numbers=atoms.numbers.tolist(),
        symbols=atoms.get_chemical_symbols(),
        volume=float(atoms.get_volume()),
    )


class ChemeleonPredictor:
    """Chemeleon structure prediction without MCP."""

    def __init__(self, checkpoint_dir: str | None = None):
        # Use environment variables for checkpoint paths
        # Default to None to let chemeleon-dng auto-download
        if checkpoint_dir is None:
            checkpoint_dir = os.getenv("CHEMELEON_CHECKPOINT_DIR")
        self.checkpoint_dir = checkpoint_dir

    async def predict_structure(
        self,
        formula: str,
        num_samples: int = 1,
        checkpoint_path: str | None = None,
        prefer_gpu: bool = True,
    ) -> PredictionResult:
        """
        Predict crystal structure for a formula using direct API (no disk I/O).

        This method uses the direct DiffusionModule API for in-memory structure generation,
        avoiding temporary file I/O overhead and providing better error handling.

        Args:
            formula: Chemical formula (e.g., "TiO2", "GeSn")
            num_samples: Number of structures to generate
            checkpoint_path: Optional path to specific checkpoint file
            prefer_gpu: Use GPU if available

        Returns:
            PredictionResult with structures or error information
        """
        import time

        from pymatgen.core import Composition

        start_time = time.time()

        try:
            # Load model (uses caching via _load_model)
            model = _load_model(task="csp", checkpoint_path=checkpoint_path, prefer_gpu=prefer_gpu)

            # Parse formula to get atomic composition
            comp = Composition(formula)

            # Prepare batched input for all samples
            # Chemeleon expects: atom_types (flat list of atomic numbers for all samples)
            #                    num_atoms (list of atom counts per sample)
            batch_atom_types = []
            batch_num_atoms = []

            for _ in range(num_samples):
                atomic_numbers = [el.Z for el, amt in comp.items() for _ in range(int(amt))]
                batch_atom_types.extend(atomic_numbers)
                batch_num_atoms.append(len(atomic_numbers))

            # Generate structures using direct API (in-memory, no disk I/O)
            logger.info(f"Generating {num_samples} structure(s) for {formula} using Chemeleon CSP")
            samples = model.sample(
                task="csp", atom_types=batch_atom_types, num_atoms=batch_num_atoms
            )

            # Convert ASE Atoms objects to CrystalStructure models
            structures = [_atoms_to_structure_dict(atoms, formula) for atoms in samples]

            computation_time = time.time() - start_time
            logger.info(f"Generated {len(structures)} structure(s) in {computation_time:.2f}s")

            return PredictionResult(
                success=True,
                formula=formula,
                predicted_structures=structures,
                computation_time=computation_time,
                method="chemeleon-dng",
                checkpoint_used=checkpoint_path or "default",
            )

        except Exception as e:
            logger.error(f"Structure prediction failed for {formula}: {e}", exc_info=True)

            # Provide helpful error context
            error_msg = str(e)
            if "checkpoint" in error_msg.lower():
                error_msg = (
                    f"Checkpoint loading failed: {e}\n"
                    f"Try setting CHEMELEON_CHECKPOINT_DIR environment variable "
                    f"or ensure checkpoints are available in ~/.cache/chemeleon_dng/"
                )
            elif "cuda" in error_msg.lower() or "gpu" in error_msg.lower():
                error_msg = f"GPU error: {e}\nTry running with prefer_gpu=False to use CPU instead"

            return PredictionResult(success=False, formula=formula, error=error_msg)

    def predict_structure_sync(
        self,
        formula: str,
        num_samples: int = 1,
        checkpoint_path: str | None = None,
        prefer_gpu: bool = True,
    ) -> PredictionResult:
        """Synchronous version of predict_structure."""
        import asyncio

        return asyncio.run(
            self.predict_structure(formula, num_samples, checkpoint_path, prefer_gpu)
        )

    def clear_cache(self):
        """Clear model cache."""
        global _model_cache
        num_cleared = len(_model_cache)
        _model_cache.clear()

        import gc

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return num_cleared
