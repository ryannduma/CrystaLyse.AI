"""
MACE Stress/Strain Calculations

Provides stress tensor calculations for mechanical property prediction.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging
import numpy as np

logger = logging.getLogger(__name__)


class StressResult(BaseModel):
    """Stress calculation result."""
    success: bool = True
    formula: str
    stress_tensor_3x3: Optional[List[List[float]]] = Field(
        None, description="Full 3x3 stress tensor in eV/Å³"
    )
    stress_voigt: Optional[List[float]] = Field(
        None, description="Voigt 6-component stress [xx, yy, zz, yz, xz, xy] in eV/Å³"
    )
    pressure: Optional[float] = Field(
        None, description="Hydrostatic pressure (GPa), negative = tensile"
    )
    von_mises_stress: Optional[float] = Field(
        None, description="Von Mises equivalent stress (GPa)"
    )
    max_shear_stress: Optional[float] = Field(
        None, description="Maximum shear stress (GPa)"
    )
    unit: str = "eV/Å³ for stress, GPa for pressure"
    error: Optional[str] = None


class EOSResult(BaseModel):
    """Equation of state fitting result."""
    success: bool = True
    formula: str
    eos_type: str = Field(description="EOS type (e.g., 'birchmurnaghan')")
    v0: Optional[float] = Field(None, description="Equilibrium volume (Å³)")
    e0: Optional[float] = Field(None, description="Minimum energy (eV)")
    b0: Optional[float] = Field(None, description="Bulk modulus (GPa)")
    b0_prime: Optional[float] = Field(None, description="Pressure derivative of bulk modulus")
    volumes: Optional[List[float]] = Field(None, description="Volumes sampled (Å³)")
    energies: Optional[List[float]] = Field(None, description="Energies calculated (eV)")
    error: Optional[str] = None


try:
    import torch
    from ase import Atoms
    from ase.eos import EquationOfState
    from ase.stress import voigt_6_to_full_3x3_stress, full_3x3_to_voigt_6_stress
    ASE_AVAILABLE = True
except ImportError:
    ASE_AVAILABLE = False
    Atoms = None
    EquationOfState = None

try:
    from mace.calculators import mace_mp, mace_off, MACECalculator as MACECalc
    MACE_AVAILABLE = True
except ImportError:
    MACE_AVAILABLE = False
    mace_mp = None
    mace_off = None
    MACECalc = None


# Import from local energy module
try:
    from .energy import get_mace_calculator, dict_to_atoms, atoms_to_dict, validate_structure
except ImportError:
    get_mace_calculator = None
    dict_to_atoms = None
    atoms_to_dict = None
    validate_structure = None


class MACEStressCalculator:
    """
    MACE stress and strain calculations for mechanical properties.

    Capabilities:
    - Full 3x3 stress tensor calculation
    - Voigt 6-component stress
    - Hydrostatic pressure
    - Von Mises stress
    - Equation of state fitting
    """

    def __init__(
        self,
        model_type: str = "mace_mp",
        size: str = "medium",
        device: str = "auto"
    ):
        self.model_type = model_type
        self.size = size
        self.device = device

    @staticmethod
    def calculate_stress(
        structure: Dict[str, Any],
        model_type: str = "mace_mp",
        size: str = "medium",
        device: str = "auto"
    ) -> StressResult:
        """
        Calculate stress tensor for a structure.

        Args:
            structure: Structure dictionary with numbers, positions, cell
            model_type: MACE model type ('mace_mp', 'mace_off', or path)
            size: Model size ('small', 'medium', 'large')
            device: Compute device ('auto', 'cpu', 'cuda')

        Returns:
            Structured stress result with tensor and derived quantities
        """
        if not ASE_AVAILABLE or not MACE_AVAILABLE:
            return StressResult(
                success=False,
                formula="unknown",
                error="ASE or MACE not available - install required packages"
            )

        try:
            # Validate structure
            valid, msg = validate_structure(structure)
            if not valid:
                return StressResult(
                    success=False,
                    formula="unknown",
                    error=f"Validation failed: {msg}"
                )

            # Convert to atoms
            atoms = dict_to_atoms(structure)
            formula = atoms.get_chemical_formula()

            # Get MACE calculator
            calc = get_mace_calculator(
                model_type=model_type,
                size=size,
                device=device
            )
            atoms.calc = calc

            # Calculate stress tensor (ASE returns Voigt form in eV/Å³)
            stress_voigt = atoms.get_stress(voigt=True)  # 6-component
            stress_3x3 = voigt_6_to_full_3x3_stress(stress_voigt)  # Convert to 3x3

            # Calculate pressure (negative trace / 3)
            # Negative sign: compression = positive pressure
            pressure_ev_ang3 = -np.trace(stress_3x3) / 3.0
            pressure_gpa = pressure_ev_ang3 * 160.21766208  # eV/Å³ to GPa

            # Calculate von Mises stress
            # σ_vm = sqrt(0.5 * [(σ_xx-σ_yy)² + (σ_yy-σ_zz)² + (σ_zz-σ_xx)² + 6(σ_xy² + σ_yz² + σ_xz²)])
            s11, s22, s33 = stress_3x3[0, 0], stress_3x3[1, 1], stress_3x3[2, 2]
            s12, s13, s23 = stress_3x3[0, 1], stress_3x3[0, 2], stress_3x3[1, 2]

            von_mises_ev_ang3 = np.sqrt(
                0.5 * ((s11 - s22)**2 + (s22 - s33)**2 + (s33 - s11)**2 +
                       6 * (s12**2 + s13**2 + s23**2))
            )
            von_mises_gpa = von_mises_ev_ang3 * 160.21766208

            # Calculate maximum shear stress
            # τ_max = (σ_max - σ_min) / 2
            eigenvalues = np.linalg.eigvalsh(stress_3x3)
            max_shear_ev_ang3 = (eigenvalues.max() - eigenvalues.min()) / 2.0
            max_shear_gpa = max_shear_ev_ang3 * 160.21766208

            return StressResult(
                success=True,
                formula=formula,
                stress_tensor_3x3=stress_3x3.tolist(),
                stress_voigt=stress_voigt.tolist(),
                pressure=float(pressure_gpa),
                von_mises_stress=float(von_mises_gpa),
                max_shear_stress=float(max_shear_gpa)
            )

        except Exception as e:
            logger.error(f"Stress calculation failed: {e}")
            return StressResult(
                success=False,
                formula=structure.get("formula", "unknown"),
                error=f"Stress calculation failed: {str(e)}"
            )

    @staticmethod
    def fit_equation_of_state(
        structure: Dict[str, Any],
        eos_type: str = "birchmurnaghan",
        strain_range: float = 0.05,
        n_points: int = 7,
        model_type: str = "mace_mp",
        size: str = "medium",
        device: str = "auto"
    ) -> EOSResult:
        """
        Fit equation of state by calculating energy at multiple volumes.

        Args:
            structure: Structure dictionary
            eos_type: EOS type ('birchmurnaghan', 'murnaghan', 'vinet', etc.)
            strain_range: Strain range (+/-)
            n_points: Number of volume points
            model_type: MACE model type
            size: Model size
            device: Compute device

        Returns:
            EOS fitting result with bulk modulus and equilibrium properties
        """
        if not ASE_AVAILABLE or not MACE_AVAILABLE:
            return EOSResult(
                success=False,
                formula="unknown",
                eos_type=eos_type,
                error="ASE or MACE not available"
            )

        try:
            # Validate structure
            valid, msg = validate_structure(structure)
            if not valid:
                return EOSResult(
                    success=False,
                    formula="unknown",
                    eos_type=eos_type,
                    error=f"Validation failed: {msg}"
                )

            # Convert to atoms
            atoms = dict_to_atoms(structure)
            formula = atoms.get_chemical_formula()

            # Get MACE calculator
            calc = get_mace_calculator(
                model_type=model_type,
                size=size,
                device=device
            )

            # Generate volume points
            v0 = atoms.get_volume()
            volumes = np.linspace(v0 * (1 - strain_range), v0 * (1 + strain_range), n_points)
            energies = []

            for vol in volumes:
                # Scale cell to target volume
                scale_factor = (vol / v0) ** (1/3)
                scaled_atoms = atoms.copy()
                scaled_atoms.set_cell(atoms.get_cell() * scale_factor, scale_atoms=True)
                scaled_atoms.calc = calc

                energy = scaled_atoms.get_potential_energy()
                energies.append(energy)

            # Fit EOS
            eos = EquationOfState(volumes, energies, eos=eos_type)
            v_eq, e_eq, B = eos.fit()  # B is in eV/Å³

            # Convert bulk modulus to GPa
            B_gpa = B * 160.21766208

            # Get B' (pressure derivative) if available
            try:
                b0_prime = eos.eos_parameters[3] if len(eos.eos_parameters) > 3 else None
            except:
                b0_prime = None

            return EOSResult(
                success=True,
                formula=formula,
                eos_type=eos_type,
                v0=float(v_eq),
                e0=float(e_eq),
                b0=float(B_gpa),
                b0_prime=float(b0_prime) if b0_prime is not None else None,
                volumes=volumes.tolist(),
                energies=energies
            )

        except Exception as e:
            logger.error(f"EOS fitting failed: {e}")
            return EOSResult(
                success=False,
                formula=structure.get("formula", "unknown"),
                eos_type=eos_type,
                error=f"EOS fitting failed: {str(e)}"
            )
