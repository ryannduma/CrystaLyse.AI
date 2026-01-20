"""MACE formation energy calculations - extracted from MCP server."""

import logging
import warnings
from typing import Any

import numpy as np
from pydantic import BaseModel

# Suppress e3nn warning about TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD
warnings.filterwarnings(
    "ignore", category=UserWarning, module="e3nn", message=".*TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD.*"
)

logger = logging.getLogger(__name__)

# Global model cache
_model_cache: dict[str, Any] = {}


class EnergyResult(BaseModel):
    """Formation energy calculation result."""

    success: bool = True
    formula: str
    formation_energy: float | None = None
    energy_per_atom: float | None = None
    total_energy: float | None = None
    unit: str = "eV"
    method: str = "mace"
    max_force: float | None = None
    rms_force: float | None = None
    error: str | None = None


class RelaxationResult(BaseModel):
    """Structure relaxation result."""

    success: bool = True
    converged: bool = False
    initial_energy: float | None = None
    final_energy: float | None = None
    energy_change: float | None = None
    max_displacement: float | None = None
    n_steps: int = 0
    relaxed_structure: dict[str, Any] | None = None
    error: str | None = None


def _import_dependencies():
    """Import required dependencies with informative error messages."""
    try:
        import torch  # noqa: F401

        global torch  # noqa: F811
    except ImportError as e:
        raise ImportError("PyTorch is required for MACE calculations") from e

    try:
        from ase import Atoms
        from ase.optimize import BFGS, FIRE, LBFGS

        global Atoms, BFGS, FIRE, LBFGS  # noqa: F811
    except ImportError as e:
        raise ImportError("ASE is required for atomic simulations") from e

    try:
        from mace.calculators import MACECalculator, mace_mp, mace_off

        global mace_mp, mace_off, MACECalculator  # noqa: F811
        logger.info("MACE calculators imported successfully")
    except ImportError as e:
        raise ImportError(f"MACE package not available: {e}") from e


# Import dependencies on module load
_import_dependencies()


def get_mace_calculator(
    model_type: str = "mace_mp",
    size: str = "medium",
    device: str = "auto",
    compile_model: bool = False,
    default_dtype: str = "float32",
) -> Any:
    """Get or create MACE calculator with caching and optimisation."""
    cache_key = f"{model_type}_{size}_{device}_{compile_model}_{default_dtype}"

    if cache_key not in _model_cache:
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading MACE model: {model_type} ({size}) on {device}")

        try:
            if model_type == "mace_mp":
                calc = mace_mp(model=size, device=device, default_dtype=default_dtype)
            elif model_type == "mace_off":
                calc = mace_off(model=size, device=device, default_dtype=default_dtype)
            else:
                # Custom model path
                calc = MACECalculator(
                    model_paths=model_type, device=device, default_dtype=default_dtype
                )

            _model_cache[cache_key] = calc
            logger.info(f"MACE calculator cached: {cache_key}")

        except Exception as e:
            logger.error(f"Failed to load MACE calculator: {e}")
            raise

    return _model_cache[cache_key]


def validate_structure(structure_dict: dict) -> tuple[bool, str]:
    """Validate structure before MACE calculations."""
    try:
        required = ["numbers", "positions", "cell"]
        for field in required:
            if field not in structure_dict:
                return False, f"Missing required field: {field}"

        n_atoms = len(structure_dict["numbers"])
        if n_atoms == 0:
            return False, "Structure has no atoms"

        positions = np.array(structure_dict["positions"])
        if positions.shape != (n_atoms, 3):
            return False, f"Position array shape {positions.shape} doesn't match {n_atoms} atoms"

        numbers = np.array(structure_dict["numbers"])
        if np.any(numbers <= 0) or np.any(numbers > 118):
            return False, "Invalid atomic numbers (must be 1-118)"

        cell = np.array(structure_dict["cell"])
        if cell.shape != (3, 3):
            return False, f"Cell must be 3x3, got {cell.shape}"

        volume = np.abs(np.linalg.det(cell))
        if volume < 1e-6:
            return False, "Cell volume is too small"
        if volume > 1e6:
            return False, "Cell volume is unreasonably large"

        return True, "Valid structure"

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def dict_to_atoms(structure_dict: dict) -> Any:
    """Convert structure dictionary to ASE Atoms object."""
    return Atoms(
        numbers=structure_dict["numbers"],
        positions=structure_dict["positions"],
        cell=structure_dict["cell"],
        pbc=structure_dict.get("pbc", [True, True, True]),
    )


def atoms_to_dict(atoms: Any) -> dict:
    """Convert ASE Atoms object to structure dictionary."""
    return {
        "numbers": atoms.numbers.tolist(),
        "positions": atoms.positions.tolist(),
        "cell": atoms.cell.tolist(),
        "pbc": atoms.pbc.tolist(),
    }


class MACECalculator:  # noqa: F811
    """MACE energy calculations without MCP."""

    def __init__(self, model_type: str = "mace_mp", size: str = "medium", device: str = "auto"):
        self.model_type = model_type
        self.size = size
        self.device = device

    async def calculate_formation_energy(self, structure: dict[str, Any]) -> EnergyResult:
        """Calculate formation energy using MACE."""
        try:
            # Validate structure
            valid, msg = validate_structure(structure)
            if not valid:
                return EnergyResult(
                    success=False, formula="unknown", error=f"Validation failed: {msg}"
                )

            atoms = dict_to_atoms(structure)
            calc = get_mace_calculator(
                model_type=self.model_type, size=self.size, device=self.device
            )
            atoms.calc = calc

            # Calculate energy
            compound_energy = atoms.get_potential_energy()

            # Get reference energies from the foundation model
            atomic_numbers = atoms.get_atomic_numbers()
            indices = torch.tensor(
                [calc.z_table.z_to_index(z) for z in atomic_numbers], device=calc.device
            )

            # Convert to one-hot encoding
            num_elements = len(calc.z_table)
            one_hot = torch.nn.functional.one_hot(indices, num_classes=num_elements).float()

            # Get atomic energies
            atomic_energies = calc.models[0].atomic_energies_fn(one_hot).detach().cpu().numpy()
            total_reference_energy = np.sum(atomic_energies)

            # Calculate formation energy
            formation_energy = (compound_energy - total_reference_energy) / len(atoms)

            return EnergyResult(
                success=True,
                formula=atoms.get_chemical_formula(),
                formation_energy=float(formation_energy),
                energy_per_atom=float(formation_energy),
                total_energy=float(compound_energy),
            )

        except Exception as e:
            logger.error(f"Formation energy calculation failed: {e}")
            return EnergyResult(success=False, formula="unknown", error=str(e))

    async def relax_structure(
        self,
        structure: dict[str, Any],
        fmax: float = 0.01,
        steps: int = 500,
        optimizer: str = "BFGS",
    ) -> RelaxationResult:
        """Relax structure to local energy minimum."""
        try:
            # Validate structure
            valid, msg = validate_structure(structure)
            if not valid:
                return RelaxationResult(success=False, error=f"Validation failed: {msg}")

            atoms = dict_to_atoms(structure)
            calc = get_mace_calculator(
                model_type=self.model_type, size=self.size, device=self.device
            )
            atoms.calc = calc

            # Store initial state
            initial_energy = float(atoms.get_potential_energy())
            initial_positions = atoms.positions.copy()

            # Select optimizer
            if optimizer.upper() == "BFGS":
                opt_class = BFGS
            elif optimizer.upper() == "FIRE":
                opt_class = FIRE
            elif optimizer.upper() == "LBFGS":
                opt_class = LBFGS
            else:
                return RelaxationResult(
                    success=False,
                    error=f"Invalid optimizer '{optimizer}'. Choose from BFGS, FIRE, LBFGS.",
                )

            # Track optimization progress
            energies = [initial_energy]

            def track_energy():
                energies.append(float(atoms.get_potential_energy()))

            opt = opt_class(atoms, logfile=None)
            opt.attach(track_energy, interval=1)

            # Run optimization
            converged = opt.run(fmax=fmax, steps=steps)

            # Calculate metrics
            final_energy = float(atoms.get_potential_energy())
            energy_change = final_energy - initial_energy
            max_displacement = float(
                np.max(np.linalg.norm(atoms.positions - initial_positions, axis=1))
            )

            return RelaxationResult(
                success=True,
                converged=bool(converged),
                initial_energy=initial_energy,
                final_energy=final_energy,
                energy_change=energy_change,
                max_displacement=max_displacement,
                n_steps=len(energies) - 1,
                relaxed_structure=atoms_to_dict(atoms),
            )

        except Exception as e:
            logger.error(f"Relaxation failed: {e}")
            return RelaxationResult(success=False, error=str(e))

    async def calculate_energy(self, cif_content: str, prefer_gpu: bool = True) -> dict[str, Any]:
        """
        Calculate energy from CIF content (compatible with MCP server interface).

        Args:
            cif_content: Crystal structure in CIF format
            prefer_gpu: Use GPU if available

        Returns:
            Energy calculation results
        """
        try:
            # Parse CIF to atoms
            from io import StringIO

            from ase.io import read

            atoms = read(StringIO(cif_content), format="cif")

            # Convert to structure dict
            structure = atoms_to_dict(atoms)

            # Update device based on preference
            if prefer_gpu:
                self.device = "auto"  # Will auto-select CUDA if available
            else:
                self.device = "cpu"

            # Calculate energy
            result = await self.calculate_formation_energy(structure)

            # Return in dict format for MCP server
            return {
                "success": result.success,
                "formula": result.formula,
                "formation_energy_per_atom": result.formation_energy,
                "total_energy": result.total_energy,
                "num_atoms": len(atoms) if result.success else 0,
                "uncertainty": None,  # MACE doesn't provide uncertainty by default
                "computation_time": None,
                "model_used": f"{self.model_type}_{self.size}",
                "error": result.error,
            }

        except Exception as e:
            logger.error(f"Energy calculation from CIF failed: {e}")
            return {"success": False, "error": str(e)}

    def calculate_formation_energy_sync(self, structure: dict[str, Any]) -> EnergyResult:
        """Synchronous version of calculate_formation_energy."""
        import asyncio

        return asyncio.run(self.calculate_formation_energy(structure))

    def relax_structure_sync(
        self,
        structure: dict[str, Any],
        fmax: float = 0.01,
        steps: int = 500,
        optimizer: str = "BFGS",
    ) -> RelaxationResult:
        """Synchronous version of relax_structure."""
        import asyncio

        return asyncio.run(self.relax_structure(structure, fmax, steps, optimizer))
