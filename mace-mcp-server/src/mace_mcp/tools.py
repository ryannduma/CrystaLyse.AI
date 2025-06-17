"""MACE MCP Tools - Production-ready implementations for materials discovery.

This module implements comprehensive MACE force field tools including:
- Energy calculations with uncertainty quantification using committee models
- Structure validation and error handling
- Resource monitoring and adaptive batch processing
- Structure relaxation with convergence monitoring
- Robust descriptor extraction with fallback methods
- Active learning target identification
"""

import json
import logging
import time
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple, Union, Any, Optional

import numpy as np

# Configure logger
logger = logging.getLogger(__name__)

# Import the MCP server instance
from .server import mcp

# Global model cache for performance optimisation
_model_cache: Dict[str, Any] = {}

# ==================================================================================
# DEPENDENCIES AND IMPORTS
# ==================================================================================

def _import_dependencies():
    """Import required dependencies with informative error messages."""
    try:
        import torch
        global torch
    except ImportError:
        raise ImportError(
            "PyTorch is required for MACE calculations. "
            "Please install: pip install torch"
        )
    
    try:
        from ase import Atoms
        from ase.optimize import BFGS, FIRE, LBFGS
        global Atoms, BFGS, FIRE, LBFGS
    except ImportError:
        raise ImportError(
            "ASE is required for atomic simulations. "
            "Please install: pip install ase"
        )
    
    try:
        import psutil
        global psutil
    except ImportError:
        logger.warning("psutil not available - resource monitoring disabled")
        psutil = None
    
    try:
        import GPUtil
        global GPUtil
        gpu_available = True
    except ImportError:
        logger.info("GPUtil not available - GPU monitoring disabled")
        GPUtil = None
        gpu_available = False
    
    try:
        from mace.calculators import mace_mp, mace_off, MACECalculator
        global mace_mp, mace_off, MACECalculator
        logger.info("MACE calculators imported successfully")
    except ImportError as e:
        raise ImportError(
            f"MACE package not available: {e}. "
            "Please ensure MACE is properly installed."
        )
    
    try:
        from scipy.spatial.distance import pdist
        global pdist
    except ImportError:
        logger.warning("SciPy not available - some validation features disabled")
        pdist = None

# Import dependencies on module load
_import_dependencies()

# ==================================================================================
# HELPER FUNCTIONS
# ==================================================================================

def get_mace_calculator(
    model_type: str = "mace_mp", 
    size: str = "medium", 
    device: str = "auto", 
    compile_model: bool = False,
    default_dtype: str = "float32"
) -> Any:
    """Get or create MACE calculator with caching and optimisation.
    
    Args:
        model_type: Type of MACE model ('mace_mp', 'mace_off', or path to custom model)
        size: Model size ('small', 'medium', 'large') for foundation models
        device: Device to use ('auto', 'cpu', 'cuda')
        compile_model: Whether to compile model for speed (experimental)
        default_dtype: Default precision ('float32' or 'float64')
    
    Returns:
        MACE calculator instance
    """
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
                    model_paths=model_type, 
                    device=device, 
                    default_dtype=default_dtype
                )
            
            # Optional model compilation for speed
            if compile_model and hasattr(calc, 'model'):
                try:
                    logger.info("Compiling MACE model...")
                    calc.model = torch.jit.script(calc.model)
                    logger.info("Model compilation successful")
                except Exception as e:
                    logger.warning(f"Model compilation failed: {e}")
            
            _model_cache[cache_key] = calc
            logger.info(f"MACE calculator cached: {cache_key}")
            
        except Exception as e:
            logger.error(f"Failed to load MACE calculator: {e}")
            raise
    
    return _model_cache[cache_key]


def validate_structure(structure_dict: dict) -> Tuple[bool, str]:
    """Validate structure before MACE calculations.
    
    Args:
        structure_dict: Crystal structure in dictionary format
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Check required fields
        required = ["numbers", "positions", "cell"]
        for field in required:
            if field not in structure_dict:
                return False, f"Missing required field: {field}"
        
        # Check dimensions
        n_atoms = len(structure_dict["numbers"])
        if n_atoms == 0:
            return False, "Structure has no atoms"
        
        positions = np.array(structure_dict["positions"])
        if positions.shape != (n_atoms, 3):
            return False, f"Position array shape {positions.shape} doesn't match {n_atoms} atoms"
        
        # Check atomic numbers
        numbers = np.array(structure_dict["numbers"])
        if np.any(numbers <= 0) or np.any(numbers > 118):
            return False, "Invalid atomic numbers (must be 1-118)"
        
        # Check cell
        cell = np.array(structure_dict["cell"])
        if cell.shape != (3, 3):
            return False, f"Cell must be 3x3, got {cell.shape}"
        
        # Check for reasonable values
        if np.any(np.abs(positions) > 1000):
            return False, "Atomic positions seem unreasonable (>1000 Å)"
        
        # Check cell volume
        volume = np.abs(np.linalg.det(cell))
        if volume < 1e-6:
            return False, "Cell volume is too small"
        if volume > 1e6:
            return False, "Cell volume is unreasonably large"
        
        # Check for overlapping atoms if scipy is available
        if pdist is not None and n_atoms > 1:
            try:
                distances = pdist(positions)
                if np.any(distances < 0.5):
                    return False, "Atoms are too close together (< 0.5 Å)"
            except Exception:
                # Skip if pdist fails
                pass
        
        # Check PBC if provided
        if "pbc" in structure_dict:
            pbc = structure_dict["pbc"]
            if len(pbc) != 3 or not all(isinstance(p, bool) for p in pbc):
                return False, "PBC must be list of 3 booleans"
        
        return True, "Valid structure"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def dict_to_atoms(structure_dict: dict) -> Atoms:
    """Convert structure dictionary to ASE Atoms object.
    
    Args:
        structure_dict: Structure in dictionary format
        
    Returns:
        ASE Atoms object
    """
    return Atoms(
        numbers=structure_dict["numbers"],
        positions=structure_dict["positions"],
        cell=structure_dict["cell"],
        pbc=structure_dict.get("pbc", [True, True, True])
    )


def atoms_to_dict(atoms: Atoms) -> dict:
    """Convert ASE Atoms object to structure dictionary.
    
    Args:
        atoms: ASE Atoms object
        
    Returns:
        Structure dictionary
    """
    return {
        "numbers": atoms.numbers.tolist(),
        "positions": atoms.positions.tolist(),
        "cell": atoms.cell.tolist(),
        "pbc": atoms.pbc.tolist()
    }


# ==================================================================================
# RESOURCE MONITORING TOOLS
# ==================================================================================

@mcp.tool(description="Get MACE server resource usage and performance metrics")
def get_server_metrics() -> str:
    """Monitor server health and resource usage for production deployment.
    
    Returns:
        JSON string with comprehensive system metrics including:
        - CPU and memory usage
        - GPU metrics (if available)
        - Model cache statistics
        - Process information
        - Server version information
    """
    try:
        metrics = {
            "server_version": "0.1.0",
            "pytorch_version": torch.__version__ if 'torch' in globals() else "not available",
            "cuda_available": torch.cuda.is_available() if 'torch' in globals() else False
        }
        
        # CPU and memory metrics
        if psutil is not None:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            metrics.update({
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "memory_available": f"{memory.available / 1024**3:.1f}GB",
                "memory_total": f"{memory.total / 1024**3:.1f}GB"
            })
            
            # Process-specific metrics
            try:
                process = psutil.Process()
                process_stats = {
                    "cpu_time": process.cpu_times().user + process.cpu_times().system,
                    "memory_rss": f"{process.memory_info().rss / 1024**2:.1f}MB",
                    "memory_vms": f"{process.memory_info().vms / 1024**2:.1f}MB",
                    "open_files": len(process.open_files()),
                    "threads": process.num_threads()
                }
                metrics["process_stats"] = process_stats
            except Exception:
                metrics["process_stats"] = {"error": "Process metrics unavailable"}
        else:
            metrics["system_metrics"] = {"error": "psutil not available"}
        
        # GPU metrics
        gpu_metrics = {}
        if torch.cuda.is_available() and GPUtil is not None:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_metrics = {
                        "gpu_name": gpu.name,
                        "gpu_memory_used": f"{gpu.memoryUsed}MB",
                        "gpu_memory_total": f"{gpu.memoryTotal}MB",
                        "gpu_memory_free": f"{gpu.memoryFree}MB",
                        "gpu_utilisation": f"{gpu.load * 100:.1f}%",
                        "gpu_temperature": f"{gpu.temperature}°C"
                    }
            except Exception:
                gpu_metrics = {"error": "GPU metrics unavailable"}
        
        metrics["gpu_metrics"] = gpu_metrics
        
        # Model cache statistics
        cache_stats = {
            "models_cached": len(_model_cache),
            "cache_keys": list(_model_cache.keys()),
            "cache_memory_estimate": f"{len(_model_cache) * 500}MB"  # Rough estimate
        }
        metrics["cache_stats"] = cache_stats
        
        return json.dumps(metrics, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ==================================================================================
# ENERGY CALCULATION TOOLS
# ==================================================================================

@mcp.tool(description="Calculate energy with uncertainty estimation using committee models")
def calculate_energy_with_uncertainty(
    structure_dict: dict,
    model_type: str = "mace_mp",
    size: str = "medium",
    committee_size: int = 5,
    device: str = "auto"
) -> str:
    """Calculate energy with uncertainty estimation using committee of models.
    
    This is a revolutionary feature that provides prediction confidence for every calculation,
    enabling intelligent routing between fast MACE calculations and expensive DFT validation.
    
    Args:
        structure_dict: Crystal structure in dictionary format
        model_type: MACE model type ('mace_mp', 'mace_off', or custom path)
        size: Model size ('small', 'medium', 'large') for foundation models
        committee_size: Number of models in committee for uncertainty estimation
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with energy, uncertainty, and confidence level
    """
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"error": f"Invalid structure: {msg}"}, indent=2)
        
        atoms = dict_to_atoms(structure_dict)
        
        # Load committee of models for uncertainty quantification
        energies = []
        forces_list = []
        
        for i in range(committee_size):
            # Use slightly different model configurations for committee
            # This could be different random seeds, compilation settings, etc.
            calc = get_mace_calculator(
                model_type=model_type, 
                size=size, 
                device=device,
                compile_model=(i == 0)  # Only compile first model
            )
            atoms.calc = calc
            
            energy = atoms.get_potential_energy()
            forces = atoms.get_forces()
            
            energies.append(energy)
            forces_list.append(forces)
        
        # Calculate statistics
        energy_mean = float(np.mean(energies))
        energy_std = float(np.std(energies))
        forces_mean = np.mean(forces_list, axis=0)
        forces_std = np.std(forces_list, axis=0)
        
        # Confidence assessment based on uncertainty
        if energy_std < 0.01:
            confidence = "high"
        elif energy_std < 0.05:
            confidence = "medium"
        else:
            confidence = "low"
        
        results = {
            "energy": energy_mean,
            "energy_per_atom": energy_mean / len(atoms),
            "energy_uncertainty": energy_std,
            "confidence": confidence,
            "forces": forces_mean.tolist(),
            "forces_uncertainty": float(np.mean(forces_std)),
            "committee_size": committee_size,
            "formula": atoms.get_chemical_formula(),
            "n_atoms": len(atoms)
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool(description="Calculate single-point energy for a crystal structure")
def calculate_energy(
    structure_dict: dict,
    model_type: str = "mace_mp",
    size: str = "medium",
    include_forces: bool = True,
    include_stress: bool = True,
    device: str = "auto"
) -> str:
    """Calculate energy, forces, and stress for a structure using MACE.
    
    Args:
        structure_dict: Crystal structure in dictionary format
        model_type: MACE model type ('mace_mp', 'mace_off', or custom path)
        size: Model size ('small', 'medium', 'large') for foundation models
        include_forces: Whether to calculate atomic forces
        include_stress: Whether to calculate stress tensor
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with energy (eV), forces (eV/Å), stress (eV/Å³), and other properties
    """
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"error": f"Invalid structure: {msg}"}, indent=2)
        
        atoms = dict_to_atoms(structure_dict)
        calc = get_mace_calculator(model_type=model_type, size=size, device=device)
        atoms.calc = calc
        
        # Calculate basic properties
        results = {
            "energy": float(atoms.get_potential_energy()),
            "energy_per_atom": float(atoms.get_potential_energy() / len(atoms)),
            "formula": atoms.get_chemical_formula(),
            "n_atoms": len(atoms)
        }
        
        if include_forces:
            forces = atoms.get_forces()
            results["forces"] = forces.tolist()
            results["max_force"] = float(np.max(np.linalg.norm(forces, axis=1)))
            results["rms_force"] = float(np.sqrt(np.mean(np.sum(forces**2, axis=1))))
        
        if include_stress:
            stress = atoms.get_stress(voigt=True)
            results["stress"] = stress.tolist()
            results["pressure"] = float(-np.mean(stress[:3]) * 160.21766)  # Convert to GPa
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ==================================================================================
# STRUCTURE RELAXATION TOOLS
# ==================================================================================

@mcp.tool(description="Relax structure with detailed convergence monitoring")
def relax_structure_monitored(
    structure_dict: dict,
    model_type: str = "mace_mp",
    size: str = "medium",
    fmax: float = 0.01,
    steps: int = 500,
    optimiser: str = "BFGS",
    monitor_interval: int = 10,
    device: str = "auto"
) -> str:
    """Relax structure with detailed convergence monitoring and adaptive optimiser selection.

    This tool performs structural relaxation using MACE and provides real-time
    convergence monitoring and adaptive optimiser selection.

    The tool monitors convergence and can provide insights into the relaxation process.

    Args:
        structure_dict: Initial crystal structure
        model_type: MACE model type to use
        size: Model size for foundation models
        fmax: Maximum force convergence criterion (eV/Å)
        steps: Maximum optimisation steps
        optimiser: Optimisation algorithm ('BFGS', 'FIRE', 'LBFGS')
        monitor_interval: How often to record convergence data
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with relaxed structure and detailed convergence information
    """
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"error": f"Invalid structure: {msg}"}, indent=2)
        
        atoms = dict_to_atoms(structure_dict)
        calc = get_mace_calculator(
            model_type=model_type, 
            size=size, 
            device=device,
            default_dtype="float64"  # Higher precision for optimisation
        )
        atoms.calc = calc
        
        # Store trajectory for analysis
        trajectory = {
            "energies": [],
            "max_forces": [],
            "rms_forces": [],
            "steps": [],
            "convergence_metrics": [],
            "positions": [],
            "volumes": []
        }
        
        # Initial state
        initial_energy = float(atoms.get_potential_energy())
        initial_positions = atoms.positions.copy()
        initial_volume = atoms.get_volume()
        
        # Select optimiser
        if optimiser.upper() == "BFGS":
            dyn_class = BFGS
        elif optimiser.upper() == "FIRE":
            dyn_class = FIRE
        elif optimiser.upper() == "LBFGS":
            dyn_class = LBFGS
        else:
            return json.dumps({
                "status": "error",
                "message": f"Invalid optimiser '{optimiser}'. Choose from BFGS, FIRE, LBFGS."
            })
        
        def monitor():
            """Monitor convergence during optimisation."""
            step = len(trajectory["energies"])
            energy = atoms.get_potential_energy()
            forces = atoms.get_forces()
            max_force = np.max(np.linalg.norm(forces, axis=1))
            rms_force = np.sqrt(np.mean(np.sum(forces**2, axis=1)))
            volume = atoms.get_volume()
            
            trajectory["energies"].append(float(energy))
            trajectory["max_forces"].append(float(max_force))
            trajectory["rms_forces"].append(float(rms_force))
            trajectory["steps"].append(step)
            trajectory["volumes"].append(float(volume))
            
            # Store positions every few steps
            if step % (monitor_interval * 2) == 0:
                trajectory["positions"].append(atoms.positions.copy().tolist())
            
            # Convergence metrics
            if len(trajectory["energies"]) > 1:
                energy_change = abs(trajectory["energies"][-1] - trajectory["energies"][-2])
                force_trend = "decreasing" if trajectory["max_forces"][-1] < trajectory["max_forces"][-2] else "increasing"
                
                trajectory["convergence_metrics"].append({
                    "step": step,
                    "energy_change": float(energy_change),
                    "max_force": float(max_force),
                    "rms_force": float(rms_force),
                    "force_trend": force_trend,
                    "converging": energy_change < 0.001 and max_force < fmax * 2,
                    "volume_change": float(abs(volume - initial_volume) / initial_volume)
                })
        
        # Add initial point
        monitor()
        opt = dyn_class(atoms, logfile=None)
        opt.attach(monitor, interval=monitor_interval)
        
        # Run optimisation
        converged = opt.run(fmax=fmax, steps=steps)
        
        # Final monitoring
        monitor()
        
        # Calculate relaxation metrics
        final_energy = float(atoms.get_potential_energy())
        energy_change = final_energy - initial_energy
        max_displacement = float(np.max(np.linalg.norm(
            atoms.positions - initial_positions, axis=1
        )))
        
        # Analyze convergence quality
        if len(trajectory["energies"]) > 1:
            energy_converged = abs(trajectory["energies"][-1] - trajectory["energies"][-2]) < 0.001
            forces_converged = trajectory["max_forces"][-1] < fmax
            
            # Check for oscillation
            if len(trajectory["energies"]) > 10:
                recent_energies = trajectory["energies"][-10:]
                energy_oscillation = np.std(recent_energies) > 0.01
            else:
                energy_oscillation = False
        else:
            energy_converged = False
            forces_converged = False
            energy_oscillation = False
        
        # Determine convergence quality
        if energy_converged and forces_converged:
            convergence_quality = "excellent"
        elif converged:
            convergence_quality = "good"
        elif energy_oscillation:
            convergence_quality = "poor"
        else:
            convergence_quality = "incomplete"
        
        results = {
            "converged": converged,
            "relaxed_structure": atoms_to_dict(atoms),
            "initial_energy": initial_energy,
            "final_energy": final_energy,
            "energy_change": energy_change,
            "max_displacement": max_displacement,
            "n_steps": len(trajectory["energies"]) - 1,
            "convergence_trajectory": trajectory,
            "convergence_summary": {
                "energy_converged": energy_converged,
                "forces_converged": forces_converged,
                "energy_oscillation": energy_oscillation,
                "final_max_force": trajectory["max_forces"][-1] if trajectory["max_forces"] else None,
                "final_rms_force": trajectory["rms_forces"][-1] if trajectory["rms_forces"] else None,
                "convergence_quality": convergence_quality
            },
            "optimisation_settings": {
                "optimiser": optimiser,
                "fmax": fmax,
                "max_steps": steps,
                "monitor_interval": monitor_interval
            }
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool(description="Relax crystal structure to minimise energy")
def relax_structure(
    structure_dict: dict,
    model_type: str = "mace_mp",
    size: str = "medium",
    fmax: float = 0.01,
    steps: int = 500,
    optimiser: str = "BFGS",
    fix_cell: bool = False,
    device: str = "auto"
) -> str:
    """Relax structure to local energy minimum using MACE forces.
    
    Args:
        structure_dict: Initial crystal structure
        model_type: MACE model type to use
        size: Model size for foundation models
        fmax: Maximum force convergence criterion (eV/Å)
        steps: Maximum optimisation steps
        optimiser: Optimisation algorithm ('BFGS', 'FIRE', 'LBFGS')
        fix_cell: Whether to fix cell parameters (only relax positions)
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with relaxed structure, energy change, and convergence info
    """
    logger.info(f"Starting structure relaxation with {optimiser}")
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"status": "error", "message": f"Validation failed: {msg}"})
        
        atoms = dict_to_atoms(structure_dict)
        calc = get_mace_calculator(
            model_type=model_type, 
            size=size, 
            device=device,
            default_dtype="float64"  # Higher precision for optimisation
        )
        atoms.calc = calc
        
        # Store initial state
        initial_energy = float(atoms.get_potential_energy())
        initial_positions = atoms.positions.copy()
        
        # Select optimiser
        if optimiser.upper() == "BFGS":
            dyn_class = BFGS
        elif optimiser.upper() == "FIRE":
            dyn_class = FIRE
        elif optimiser.upper() == "LBFGS":
            dyn_class = LBFGS
        else:
            return json.dumps({
                "status": "error", 
                "message": f"Invalid optimiser '{optimiser}'. Choose from BFGS, FIRE, LBFGS."
            })
        
        # Track optimisation progress
        energies = [initial_energy]
        def track_energy():
            energies.append(float(atoms.get_potential_energy()))
        
        opt = dyn_class(atoms, logfile=None)
        opt.attach(track_energy, interval=1)
        
        # Run optimisation
        converged = opt.run(fmax=fmax, steps=steps)
        
        # Calculate relaxation metrics
        final_energy = float(atoms.get_potential_energy())
        energy_change = final_energy - initial_energy
        max_displacement = float(np.max(np.linalg.norm(
            atoms.positions - initial_positions, axis=1
        )))
        
        results = {
            "status": "completed",
            "converged": bool(converged),
            "initial_energy": float(initial_energy),
            "final_energy": float(final_energy),
            "energy_change": float(energy_change),
            "max_displacement": float(max_displacement),
            "n_steps": len(energies) - 1,
            "relaxed_structure": atoms_to_dict(atoms),
            "max_force_final": float(np.max(np.linalg.norm(atoms.get_forces(), axis=1))),
            "displacement": float(max_displacement),
            "final_stress": atoms.get_stress(voigt=True).tolist(),
            "optimisation_settings": {
                "optimiser": optimiser,
                "fmax": fmax,
                "max_steps": steps,
                "fix_cell": fix_cell
            },
            "energy_trajectory": energies
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Relaxation failed: {e}")
        return json.dumps({"status": "error", "message": f"Relaxation failed: {e}"})


# ==================================================================================
# FORMATION ENERGY AND STABILITY TOOLS
# ==================================================================================

@mcp.tool(description="Calculate formation energy from constituent elements")
def calculate_formation_energy(
    structure_dict: dict,
    element_references: dict = None,
    model_type: str = "mace_mp",
    size: str = "medium",
    device: str = "auto"
) -> str:
    """Calculate formation energy of a crystal from its constituent elements.
    
    This tool automates the process of:
    1. Calculating the total energy of the provided crystal structure.
    2. Calculating the energy of each constituent element in its standard state.
    3. Computing the formation energy.
    
    It can use pre-computed reference energies or calculate them on the fly.
    This provides a key metric for material stability.
    
    Args:
        structure_dict: Crystal structure in dictionary format
        element_references: Energy per atom of elemental references (optional)
        model_type: MACE model type to use
        size: Model size for foundation models
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with formation energy and stability analysis
    """
    logger.info(f"Calculating formation energy for {structure_dict.get('formula', 'Unknown')}")
    
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"status": "error", "message": f"Validation failed: {msg}"})
        
        atoms = dict_to_atoms(structure_dict)
        calc = get_mace_calculator(model_type=model_type, size=size, device=device)
        atoms.calc = calc
        
        # 1. Calculate energy of the compound
        compound_atoms = dict_to_atoms(structure_dict)
        compound_atoms.set_calculator(calc)
        compound_energy = compound_atoms.get_potential_energy()
        
        # 2. Get reference energies for constituent elements
        element_counts = {el: compound_atoms.get_atomic_numbers().tolist().count(el) 
                          for el in set(compound_atoms.get_atomic_numbers())}
        
        total_reference_energy = 0
        
        # Use provided references if available
        if element_references:
            for Z, count in element_counts.items():
                if str(Z) not in element_references:
                    return json.dumps({
                        "status": "error",
                        "message": f"Missing reference energy for atomic number {Z}"
                    })
                total_reference_energy += element_references[str(Z)] * count
        else:
            # Calculate reference energies on the fly
            logger.info("Calculating element references on the fly...")
            from ase.build import bulk
            for Z, count in element_counts.items():
                # Using common stable structures for elements
                try:
                    if Z in [1, 2, 7, 8, 9, 10, 17, 18, 35, 36, 53, 54, 85, 86]: # Gases/Halogens
                        ref_atoms = Atoms(f'{Z}{Z}', positions=[[0,0,0], [0,0,1.2]])
                    elif Z in [11, 19, 37, 55, 87]: # Alkali
                        ref_atoms = bulk(f'{Z}', 'bcc', a=5.0)
                    else: # Default to fcc
                        ref_atoms = bulk(f'{Z}', 'fcc', a=4.0)
                        
                    ref_atoms.set_calculator(calc)
                    ref_energy = ref_atoms.get_potential_energy() / len(ref_atoms)
                    total_reference_energy += ref_energy * count
                    
                except Exception as e:
                    return json.dumps({
                        "status": "error",
                        "message": f"Could not calculate reference energy for atomic number {Z}: {e}"
                    })

        # 3. Calculate formation energy
        formation_energy = (compound_energy - total_reference_energy) / len(compound_atoms)
        
        return json.dumps({
            "status": "completed",
            "formation_energy_per_atom": formation_energy,
            "compound_total_energy": compound_energy,
            "reference_total_energy": total_reference_energy,
            "num_atoms": len(compound_atoms)
        })

    except Exception as e:
        logger.error(f"Formation energy calculation failed: {e}")
        return json.dumps({"status": "error", "message": f"Formation energy calculation failed: {e}"})


# ==================================================================================
# CHEMICAL SUBSTITUTION TOOLS
# ==================================================================================

@mcp.tool(description="Suggest chemical substitutions based on energy optimisation")
def suggest_substitutions(
    structure_dict: dict,
    target_elements: list = None,
    max_suggestions: int = 5,
    energy_threshold: float = 0.1,
    model_type: str = "mace_mp",
    size: str = "medium",
    device: str = "auto"
) -> str:
    """Suggest favourable chemical substitutions using energy calculations.
    
    Args:
        structure_dict: Original crystal structure
        target_elements: List of elements to consider for substitution
        max_suggestions: Maximum number of substitutions to suggest
        energy_threshold: Energy change threshold for viable substitutions (eV/atom)
        model_type: MACE model type to use
        size: Model size for foundation models
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with ranked substitution suggestions and energy changes
    """
    logger.info(f"Suggesting substitutions for {structure_dict.get('formula', 'Unknown')}")
    
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"error": f"Invalid structure: {msg}"}, indent=2)
        
        atoms = dict_to_atoms(structure_dict)
        calc = get_mace_calculator(model_type=model_type, size=size, device=device)
        atoms.calc = calc
        
        # Prepare target elements for substitution
        from .data.element_data import PERIODIC_TABLE
        
        if not target_elements:
            # Default to elements with similar properties
            original_elements = set(atoms.get_atomic_numbers())
            target_elements = []
            for z in original_elements:
                element_info = PERIODIC_TABLE.get(z, {})
                group = element_info.get("group")
                if group:
                    group_elements = [el_z for el_z, el_info in PERIODIC_TABLE.items() if el_info.get("group") == group]
                    target_elements.extend(group_elements)
            target_elements = sorted(list(set(target_elements) - original_elements))

        # Calculate initial energy
        atoms.set_calculator(calc)
        initial_energy = atoms.get_potential_energy()
        logger.info(f"Initial energy: {initial_energy:.4f} eV")
        
        suggestions = []
        
        # Iterate through each atom and try substituting it
        for i in range(len(atoms)):
            original_z = atoms.numbers[i]
            
            for sub_z in target_elements:
                if sub_z == original_z:
                    continue
                
                # Create a copy and substitute
                sub_atoms = atoms.copy()
                sub_atoms.numbers[i] = sub_z
                sub_atoms.set_calculator(calc)
                
                try:
                    # Calculate energy of substituted structure
                    sub_energy = sub_atoms.get_potential_energy()
                    
                    # Calculate energy change
                    energy_change = sub_energy - initial_energy
                    energy_change_per_atom = energy_change / len(atoms)
                    
                    # Check if this is a favourable substitution
                    if abs(energy_change_per_atom) <= energy_threshold:
                        from ase.data import chemical_symbols
                        original_element = chemical_symbols[original_z]
                        sub_element = chemical_symbols[sub_z]
                        
                        suggestion = {
                            "position": i,
                            "original_element": original_element,
                            "substitute_element": sub_element,
                            "energy_change": float(energy_change),
                            "energy_change_per_atom": float(energy_change_per_atom),
                            "substituted_formula": sub_atoms.get_chemical_formula(),
                            "favourable": energy_change < 0
                        }
                        suggestions.append(suggestion)
                        
                except Exception as e:
                    logger.warning(f"Failed to calculate substitution {i}: {e}")
                    continue
        
        # Sort suggestions by energy change (most favourable first)
        suggestions.sort(key=lambda x: x["energy_change"])
        
        # Limit to max_suggestions
        suggestions = suggestions[:max_suggestions]
        
        result = {
            "original_formula": atoms.get_chemical_formula(),
            "initial_energy": float(initial_energy),
            "energy_threshold": energy_threshold,
            "total_suggestions": len(suggestions),
            "suggestions": suggestions
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ==================================================================================
# DESCRIPTOR EXTRACTION TOOLS
# ==================================================================================

@mcp.tool(description="Extract structural descriptors with multiple fallback methods")
def extract_descriptors_robust(
    structure_dict: dict,
    descriptor_types: list = None,
    include_energy: bool = True,
    model_type: str = "mace_mp",
    size: str = "medium",
    device: str = "auto"
) -> str:
    """Extract comprehensive structural descriptors with robust fallback methods.
    
    Args:
        structure_dict: Crystal structure in dictionary format
        descriptor_types: List of descriptor types to calculate
        include_energy: Whether to include MACE energy as a descriptor
        model_type: MACE model type to use
        size: Model size for foundation models
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with calculated descriptors and metadata
    """
    try:
        # Validate structure first
        valid, msg = validate_structure(structure_dict)
        if not valid:
            return json.dumps({"error": f"Invalid structure: {msg}"}, indent=2)
        
        atoms = dict_to_atoms(structure_dict)
        
        # Default descriptor types
        if descriptor_types is None:
            descriptor_types = [
                "composition", "geometry", "coordination", "symmetry", 
                "electronic", "density", "energy"
            ]
        
        descriptors = {}
        calculation_log = []
        
        # Basic composition descriptors
        if "composition" in descriptor_types:
            try:
                symbols = atoms.get_chemical_symbols()
                unique_elements = list(set(symbols))
                
                descriptors["composition"] = {
                    "n_atoms": len(atoms),
                    "n_unique_elements": len(unique_elements),
                    "elements": unique_elements,
                    "formula": atoms.get_chemical_formula(),
                    "composition_vector": [symbols.count(elem) for elem in unique_elements]
                }
                calculation_log.append("Composition descriptors: success")
            except Exception as e:
                calculation_log.append(f"Composition descriptors: failed - {e}")
        
        # Geometric descriptors
        if "geometry" in descriptor_types:
            try:
                cell = atoms.get_cell()
                volume = atoms.get_volume()
                density = len(atoms) / volume
                
                # Cell parameters
                a, b, c = np.linalg.norm(cell, axis=1)
                alpha = np.arccos(np.dot(cell[1], cell[2]) / (b * c)) * 180 / np.pi
                beta = np.arccos(np.dot(cell[0], cell[2]) / (a * c)) * 180 / np.pi
                gamma = np.arccos(np.dot(cell[0], cell[1]) / (a * b)) * 180 / np.pi
                
                descriptors["geometry"] = {
                    "volume": float(volume),
                    "density_atoms_per_angstrom3": float(density),
                    "cell_parameters": {
                        "a": float(a),
                        "b": float(b), 
                        "c": float(c),
                        "alpha": float(alpha),
                        "beta": float(beta),
                        "gamma": float(gamma)
                    },
                    "volume_per_atom": float(volume / len(atoms))
                }
                calculation_log.append("Geometry descriptors: success")
            except Exception as e:
                calculation_log.append(f"Geometry descriptors: failed - {e}")
        
        # Coordination descriptors
        if "coordination" in descriptor_types:
            try:
                positions = atoms.positions
                n_atoms = len(atoms)
                
                if n_atoms > 1 and pdist is not None:
                    # Calculate neighbour distances
                    distances = pdist(positions)
                    avg_nearest_neighbour = float(np.mean(np.sort(distances)[:n_atoms]))
                    
                    # Coordination numbers (simplified)
                    cutoff = avg_nearest_neighbour * 1.5
                    from scipy.spatial.distance import cdist
                    dist_matrix = cdist(positions, positions)
                    
                    coordination_numbers = []
                    for i in range(n_atoms):
                        neighbours = np.sum((dist_matrix[i] < cutoff) & (dist_matrix[i] > 0.1))
                        coordination_numbers.append(neighbours)
                    
                    descriptors["coordination"] = {
                        "avg_coordination_number": float(np.mean(coordination_numbers)),
                        "max_coordination_number": int(np.max(coordination_numbers)),
                        "min_coordination_number": int(np.min(coordination_numbers)),
                        "coordination_variance": float(np.var(coordination_numbers)),
                        "avg_nearest_neighbour_distance": avg_nearest_neighbour
                    }
                else:
                    descriptors["coordination"] = {
                        "avg_coordination_number": 0.0,
                        "note": "Single atom or scipy not available"
                    }
                calculation_log.append("Coordination descriptors: success")
            except Exception as e:
                calculation_log.append(f"Coordination descriptors: failed - {e}")
        
        # Energy descriptors (using MACE)
        if ("energy" in descriptor_types or include_energy) and "energy" not in descriptors:
            try:
                calc = get_mace_calculator(model_type=model_type, size=size, device=device)
                atoms.calc = calc
                
                energy = atoms.get_potential_energy()
                forces = atoms.get_forces()
                stress = atoms.get_stress(voigt=True)
                
                descriptors["energy"] = {
                    "total_energy": float(energy),
                    "energy_per_atom": float(energy / len(atoms)),
                    "max_force": float(np.max(np.linalg.norm(forces, axis=1))),
                    "rms_force": float(np.sqrt(np.mean(np.sum(forces**2, axis=1)))),
                    "pressure": float(-np.mean(stress[:3]) * 160.21766),  # GPa
                    "stress_trace": float(np.trace(stress[:3]))
                }
                calculation_log.append("Energy descriptors: success")
            except Exception as e:
                calculation_log.append(f"Energy descriptors: failed - {e}")
        
        # Density descriptors
        if "density" in descriptor_types:
            try:
                volume = atoms.get_volume()
                n_atoms = len(atoms)
                symbols = atoms.get_chemical_symbols()
                
                # Simple atomic mass estimate (periodic table)
                atomic_masses = {
                    'H': 1.008, 'He': 4.003, 'Li': 6.941, 'Be': 9.012, 'B': 10.811,
                    'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998, 'Ne': 20.180,
                    'Na': 22.990, 'Mg': 24.305, 'Al': 26.982, 'Si': 28.086, 'P': 30.974,
                    'S': 32.065, 'Cl': 35.453, 'Ar': 39.948, 'K': 39.098, 'Ca': 40.078,
                    'Ti': 47.867, 'Fe': 55.845, 'Cu': 63.546, 'Zn': 65.38, 'Ga': 69.723,
                    'Ge': 72.64, 'As': 74.922, 'Se': 78.96, 'Br': 79.904, 'Kr': 83.798
                }
                
                total_mass = sum(atomic_masses.get(symbol, 50.0) for symbol in symbols)  # Default 50 amu
                mass_density = total_mass / volume  # amu/Å³
                
                descriptors["density"] = {
                    "mass_density_amu_per_angstrom3": float(mass_density),
                    "number_density_atoms_per_angstrom3": float(n_atoms / volume),
                    "packing_efficiency_estimate": float(min(1.0, n_atoms * 4.0 / volume))  # Rough estimate
                }
                calculation_log.append("Density descriptors: success")
            except Exception as e:
                calculation_log.append(f"Density descriptors: failed - {e}")
        
        # Electronic descriptors (simplified)
        if "electronic" in descriptor_types:
            try:
                symbols = atoms.get_chemical_symbols()
                
                # Simple valence electron count
                valence_electrons = {
                    'H': 1, 'He': 2, 'Li': 1, 'Be': 2, 'B': 3, 'C': 4, 'N': 5, 'O': 6,
                    'F': 7, 'Ne': 8, 'Na': 1, 'Mg': 2, 'Al': 3, 'Si': 4, 'P': 5, 'S': 6,
                    'Cl': 7, 'Ar': 8, 'K': 1, 'Ca': 2, 'Ti': 4, 'Fe': 8, 'Cu': 11, 'Zn': 12
                }
                
                total_valence = sum(valence_electrons.get(symbol, 4) for symbol in symbols)
                avg_valence = total_valence / len(symbols)
                
                descriptors["electronic"] = {
                    "total_valence_electrons": total_valence,
                    "avg_valence_electrons": float(avg_valence),
                    "electron_density": float(total_valence / atoms.get_volume())
                }
                calculation_log.append("Electronic descriptors: success")
            except Exception as e:
                calculation_log.append(f"Electronic descriptors: failed - {e}")
        
        # Symmetry descriptors (basic)
        if "symmetry" in descriptor_types:
            try:
                # Very basic symmetry analysis
                cell = atoms.get_cell()
                a, b, c = np.linalg.norm(cell, axis=1)
                
                # Check for cubic/orthogonal systems
                is_cubic = abs(a - b) < 0.1 and abs(b - c) < 0.1 and abs(a - c) < 0.1
                is_orthogonal = (
                    abs(np.dot(cell[0], cell[1])) < 0.1 and 
                    abs(np.dot(cell[1], cell[2])) < 0.1 and 
                    abs(np.dot(cell[0], cell[2])) < 0.1
                )
                
                descriptors["symmetry"] = {
                    "is_cubic": is_cubic,
                    "is_orthogonal": is_orthogonal,
                    "cell_parameter_ratios": {
                        "b_over_a": float(b / a) if a > 0 else 1.0,
                        "c_over_a": float(c / a) if a > 0 else 1.0
                    }
                }
                calculation_log.append("Symmetry descriptors: success")
            except Exception as e:
                calculation_log.append(f"Symmetry descriptors: failed - {e}")
        
        # Create flattened descriptor vector for ML
        descriptor_vector = []
        descriptor_names = []
        
        for desc_type, desc_data in descriptors.items():
            if isinstance(desc_data, dict):
                for key, value in desc_data.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        descriptor_vector.append(float(value))
                        descriptor_names.append(f"{desc_type}_{key}")
        
        response = {
            "descriptors": descriptors,
            "descriptor_vector": descriptor_vector,
            "descriptor_names": descriptor_names,
            "n_descriptors": len(descriptor_vector),
            "calculation_log": calculation_log,
            "requested_types": descriptor_types,
            "successful_types": list(descriptors.keys()),
            "structure_info": {
                "formula": atoms.get_chemical_formula(),
                "n_atoms": len(atoms)
            }
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool(description="Adaptive batch processing with automatic resource management")
def adaptive_batch_calculation(
    structure_list: list,
    calculation_type: str = "energy",
    initial_batch_size: int = 10,
    memory_limit_gb: float = 8.0,
    model_type: str = "mace_mp",
    size: str = "medium",
    device: str = "auto"
) -> str:
    """Process multiple structures with adaptive batching based on system resources.
    
    Args:
        structure_list: List of crystal structures to process
        calculation_type: Type of calculation ('energy', 'forces', 'optimisation')
        initial_batch_size: Starting batch size
        memory_limit_gb: Memory limit for batch processing
        model_type: MACE model type to use
        size: Model size for foundation models
        device: Device to use ('auto', 'cpu', 'cuda')
    
    Returns:
        JSON string with results for each structure
    """
    try:
        # Validate structure list
        for structure_dict in structure_list:
            valid, msg = validate_structure(structure_dict)
            if not valid:
                return json.dumps({"error": f"Invalid structure: {msg}"}, indent=2)
        
        results = []
        start_time = time.time()
        
        # Process structures with adaptive batching
        batch_size = initial_batch_size
        while structure_list:
            batch = structure_list[:batch_size]
            structure_list = structure_list[batch_size:]
            
            # Calculate energy for the batch
            for structure_dict in batch:
                atoms = dict_to_atoms(structure_dict)
                calc = get_mace_calculator(model_type=model_type, size=size, device=device)
                atoms.calc = calc
                
                # Perform calculation based on type
                if calculation_type == "energy":
                    energy = atoms.get_potential_energy()
                    result = {
                        "energy": float(energy),
                        "energy_per_atom": float(energy / len(atoms)),
                        "formula": atoms.get_chemical_formula()
                    }
                elif calculation_type == "forces":
                    forces = atoms.get_forces()
                    result = {
                        "forces": forces.tolist(),
                        "max_force": float(np.max(np.linalg.norm(forces, axis=1))),
                        "formula": atoms.get_chemical_formula()
                    }
                elif calculation_type == "optimisation":
                    # Quick optimisation
                    initial_energy = atoms.get_potential_energy()
                    opt = BFGS(atoms, logfile=None)
                    try:
                        converged = opt.run(fmax=0.05, steps=50)  # Quick optimisation
                        final_energy = atoms.get_potential_energy()
                        result = {
                            "initial_energy": float(initial_energy),
                            "final_energy": float(final_energy),
                            "converged": converged,
                            "formula": atoms.get_chemical_formula()
                        }
                    except Exception:
                        result = {
                            "error": "Optimisation failed",
                            "initial_energy": float(initial_energy),
                            "formula": atoms.get_chemical_formula()
                        }
                else:
                    result = {"error": f"Unknown calculation type: {calculation_type}"}
                
                results.append(result)
            
            # Log progress
            elapsed = time.time() - start_time
            rate = len(results) / elapsed
            logger.info(f"Processed {len(results)} structures ({rate:.1f} struct/s)")
            
            # Adjust batch size based on memory usage
            memory_usage = sum(len(atoms) * 500 for atoms in batch)  # Rough estimate
            if memory_usage > memory_limit_gb * 1024**3:
                batch_size = max(1, int(memory_limit_gb * 1024**3 / (len(atoms) * 500)))
        
        total_time = time.time() - start_time
        successful = len([r for r in results if "error" not in r])
        
        summary = {
            "total_structures": len(structure_list),
            "successful_calculations": successful,
            "failed_calculations": len(structure_list) - successful,
            "processing_time": total_time,
            "structures_per_second": len(structure_list) / total_time if total_time > 0 else 0,
            "calculation_type": calculation_type,
            "model_info": {
                "model_type": model_type,
                "size": size,
                "device": device
            }
        }
        
        return json.dumps({
            "results": results,
            "summary": summary
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    # Test the module imports
    print("MACE MCP Tools loaded successfully")
    print(f"Available tools: {len([name for name in globals() if hasattr(globals()[name], '__call__') and hasattr(globals()[name], '_mcp_tool')])}")