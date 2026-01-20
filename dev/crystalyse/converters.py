import logging
import os
import re
import tempfile
from typing import Any

from ase.build import make_supercell
from ase.io import write
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

logger = logging.getLogger(__name__)


def _preprocess_cif_string(cif_string: str) -> str:
    """
    Preprocess CIF string to fix common issues from Chemeleon generation.

    Args:
        cif_string: Raw CIF string from Chemeleon

    Returns:
        Preprocessed CIF string with fixes applied
    """
    # Remove any leading/trailing whitespace
    cif_string = cif_string.strip()

    # Fix missing symmetry information - add default P1 symmetry
    if (
        "_symmetry_equiv_pos_as_xyz" not in cif_string
        and "_space_group_symop_operation_xyz" not in cif_string
    ):
        # Insert symmetry information before the atom site loop
        if "loop_" in cif_string:
            # Find the first loop (usually atom sites)
            loop_pos = cif_string.find("loop_")
            if loop_pos != -1:
                symmetry_block = """
_symmetry_equiv_pos_as_xyz
'x,y,z'

"""
                cif_string = cif_string[:loop_pos] + symmetry_block + cif_string[loop_pos:]

    # Fix atom site labels if they're malformed
    # Look for patterns like "Co1" without proper atom site loop structure
    if "_atom_site_label" in cif_string:
        # Ensure proper atom site loop structure
        lines = cif_string.split("\n")
        fixed_lines = []
        in_atom_site_loop = False
        atom_site_headers = []

        for line in lines:
            line = line.strip()
            if line.startswith("_atom_site_"):
                if not in_atom_site_loop:
                    in_atom_site_loop = True
                    if len(fixed_lines) > 0 and fixed_lines[-1] != "loop_":
                        fixed_lines.append("loop_")
                atom_site_headers.append(line)
                fixed_lines.append(line)
            elif in_atom_site_loop and line and not line.startswith("_"):
                # This should be atom data - ensure it's properly formatted
                fixed_lines.append(line)
            elif in_atom_site_loop and (line.startswith("_") or line == ""):
                in_atom_site_loop = False
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        cif_string = "\n".join(fixed_lines)

    # Extract chemical formula from atom sites if missing or malformed
    if "_chemical_formula_sum" not in cif_string or re.search(
        r'_chemical_formula_sum\s*["\']?\s*["\']?', cif_string
    ):
        # Derive chemical formula from atom sites
        formula = _derive_chemical_formula_from_cif(cif_string)
        if formula and formula != "Unknown":
            # Find a good place to insert the formula
            if "data_" in cif_string:
                # Insert after the data_ line
                lines = cif_string.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("data_"):
                        lines.insert(i + 1, f"_chemical_formula_sum '{formula}'")
                        break
                cif_string = "\n".join(lines)
            else:
                # Insert at the beginning
                cif_string = f"_chemical_formula_sum '{formula}'\n" + cif_string
    else:
        # Fix existing chemical formula format
        if "_chemical_formula_sum" in cif_string:
            # Ensure chemical formula is properly quoted
            cif_string = re.sub(
                r'_chemical_formula_sum\s+([^"\n]*?)(\n|$)',
                r'_chemical_formula_sum "\1"\2',
                cif_string,
            )

    # Fix space group name format
    if "_space_group_name_H-M_alt" in cif_string:
        # Ensure space group is properly quoted
        cif_string = re.sub(
            r'_space_group_name_H-M_alt\s+([^"\n]+)', r'_space_group_name_H-M_alt "\1"', cif_string
        )

    return cif_string


def _derive_chemical_formula_from_cif(cif_string: str) -> str:
    """
    Derive chemical formula from CIF atom site data.

    Args:
        cif_string: CIF string content

    Returns:
        Chemical formula string
    """
    # Extract atom types and counts from atom site data
    atom_counts = {}

    # Look for atom site data patterns
    atom_patterns = [
        r"^\s*([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # Standard format
        r"^\s*([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # With occupancy
        r"^\s*([A-Z][a-z]?)\d*\s+[A-Z][a-z]?\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # With type column
    ]

    for pattern in atom_patterns:
        matches = re.findall(pattern, cif_string, re.MULTILINE)
        for match in matches:
            element = match.strip()
            # Clean up element symbol (remove numbers, keep only letters)
            element = re.sub(r"\d+", "", element)
            if len(element) <= 2 and element.isalpha():
                atom_counts[element] = atom_counts.get(element, 0) + 1

    # If no atom sites found, try to extract from data header
    if not atom_counts:
        # Look for composition hints in data_ line or comments
        data_match = re.search(r"data_([A-Z][a-z]?(?:\d*[A-Z][a-z]?\d*)*)", cif_string)
        if data_match:
            # Try to parse formula from data line
            formula_candidate = data_match.group(1)
            element_matches = re.findall(r"([A-Z][a-z]?)(\d*)", formula_candidate)
            for element, count in element_matches:
                count = int(count) if count else 1
                atom_counts[element] = atom_counts.get(element, 0) + count

    # Generate formula string
    if not atom_counts:
        return "Unknown"

    # Reduce to smallest whole number ratio (formula unit)
    from functools import reduce
    from math import gcd

    # Find the GCD of all counts to reduce to formula unit
    counts = list(atom_counts.values())
    if len(counts) > 1:
        overall_gcd = reduce(gcd, counts)
        if overall_gcd > 1:
            # Reduce all counts by the GCD
            for element in atom_counts:
                atom_counts[element] = atom_counts[element] // overall_gcd
    else:
        # Special case for single element structures
        # For metals, we typically represent as just the element symbol
        if len(atom_counts) == 1:
            element = list(atom_counts.keys())[0]
            atom_counts[element] = 1

    # Sort elements by electronegativity (approximate order)
    element_order = [
        "H",
        "Li",
        "Na",
        "K",
        "Rb",
        "Cs",
        "Be",
        "Mg",
        "Ca",
        "Sr",
        "Ba",
        "Sc",
        "Y",
        "La",
        "Ti",
        "Zr",
        "Hf",
        "V",
        "Nb",
        "Ta",
        "Cr",
        "Mo",
        "W",
        "Mn",
        "Tc",
        "Re",
        "Fe",
        "Ru",
        "Os",
        "Co",
        "Rh",
        "Ir",
        "Ni",
        "Pd",
        "Pt",
        "Cu",
        "Ag",
        "Au",
        "Zn",
        "Cd",
        "Hg",
        "Al",
        "Ga",
        "In",
        "Tl",
        "Si",
        "Ge",
        "Sn",
        "Pb",
        "P",
        "As",
        "Sb",
        "Bi",
        "S",
        "Se",
        "Te",
        "Po",
        "F",
        "Cl",
        "Br",
        "I",
        "At",
        "O",
        "N",
        "C",
        "B",
    ]

    sorted_elements = []
    for element in element_order:
        if element in atom_counts:
            sorted_elements.append(element)

    # Add any remaining elements not in the order list
    for element in sorted(atom_counts.keys()):
        if element not in sorted_elements:
            sorted_elements.append(element)

    # Build formula string
    formula_parts = []
    for element in sorted_elements:
        count = atom_counts[element]
        if count > 1:
            formula_parts.append(f"{element}{count}")
        else:
            formula_parts.append(element)

    return "".join(formula_parts)


def _create_ase_atoms_from_cif_data(cif_string: str):
    """
    Create ASE Atoms object from CIF data with fallback methods.

    Args:
        cif_string: CIF string content

    Returns:
        ASE Atoms object
    """
    try:
        # Method 1: Use pymatgen (preferred)
        preprocessed_cif = _preprocess_cif_string(cif_string)
        p_structure = Structure.from_str(preprocessed_cif, fmt="cif")
        ase_atoms = AseAtomsAdaptor.get_atoms(p_structure)
        return ase_atoms
    except Exception as e:
        logger.warning(f"Pymatgen CIF parsing failed: {e}")

        try:
            # Method 2: Use ASE directly with temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False) as tmp_file:
                tmp_file.write(_preprocess_cif_string(cif_string))
                tmp_filename = tmp_file.name

            try:
                from ase.io import read

                ase_atoms = read(tmp_filename, format="cif")
                return ase_atoms
            finally:
                if os.path.exists(tmp_filename):
                    os.unlink(tmp_filename)

        except Exception as e2:
            logger.warning(f"ASE CIF parsing also failed: {e2}")

            # Method 3: Manual parsing for basic structures
            try:
                return _manual_cif_parse(cif_string)
            except Exception as e3:
                logger.error(f"All CIF parsing methods failed: {e3}")
                raise Exception(f"CIF parsing failed with all methods. Original error: {e}") from e3


def _manual_cif_parse(cif_string: str):
    """
    Manual CIF parsing for basic structures as last resort.

    Args:
        cif_string: CIF string content

    Returns:
        ASE Atoms object
    """
    from ase import Atoms

    # Extract cell parameters
    cell_a = float(re.search(r"_cell_length_a\s+([\d.]+)", cif_string).group(1))
    cell_b = float(re.search(r"_cell_length_b\s+([\d.]+)", cif_string).group(1))
    cell_c = float(re.search(r"_cell_length_c\s+([\d.]+)", cif_string).group(1))
    alpha = float(re.search(r"_cell_angle_alpha\s+([\d.]+)", cif_string).group(1))
    beta = float(re.search(r"_cell_angle_beta\s+([\d.]+)", cif_string).group(1))
    gamma = float(re.search(r"_cell_angle_gamma\s+([\d.]+)", cif_string).group(1))

    # Extract atom positions
    # Look for atom data lines (element symbol followed by coordinates)
    atom_pattern = r"([A-Z][a-z]?)\d*\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)"
    atom_matches = re.findall(atom_pattern, cif_string)

    if not atom_matches:
        raise Exception("No atom positions found in CIF")

    symbols = [match[0] for match in atom_matches]
    positions = [[float(match[1]), float(match[2]), float(match[3])] for match in atom_matches]

    # Create ASE Atoms object
    atoms = Atoms(
        symbols=symbols,
        scaled_positions=positions,
        cell=[cell_a, cell_b, cell_c, alpha, beta, gamma],
        pbc=True,
    )

    return atoms


def convert_cif_to_mace_input(cif_string: str) -> dict[str, Any]:
    """
    Converts a CIF string into a MACE-compatible dictionary.
    Enhanced version with robust error handling for Chemeleon-generated CIFs.

    Args:
        cif_string: The crystal structure in CIF format.

    Returns:
        A dictionary with 'numbers', 'positions', 'cell', and 'pbc' keys.
    """
    try:
        ase_atoms = _create_ase_atoms_from_cif_data(cif_string)

        # Get basic structural data
        numbers = ase_atoms.get_atomic_numbers()
        positions = ase_atoms.get_positions()
        cell = ase_atoms.get_cell()
        pbc = ase_atoms.get_pbc()

        # Fix coordinate array shape if flattened during JSON serialization
        import numpy as np

        if isinstance(positions, np.ndarray) and len(positions.shape) == 1:
            n_atoms = len(numbers)
            if len(positions) == n_atoms * 3:
                positions = positions.reshape(n_atoms, 3)
                logger.info(
                    f"Fixed flattened coordinate array: reshaped {len(positions)} elements to ({n_atoms}, 3)"
                )
            else:
                raise ValueError(
                    f"Flattened coordinate array has wrong size: {len(positions)} != {n_atoms * 3}"
                )

        # Validate data dimensions
        if len(numbers) == 0:
            raise ValueError("No atoms found in structure")

        if positions.shape[0] != len(numbers):
            raise ValueError(
                f"Position array length ({positions.shape[0]}) doesn't match number of atoms ({len(numbers)})"
            )

        if positions.shape[1] != 3:
            raise ValueError(
                f"Position array must have 3 coordinates per atom, got {positions.shape[1]}"
            )

        if cell.shape != (3, 3):
            raise ValueError(f"Cell array must be 3x3, got {cell.shape}")

        # Ensure proper data types and convert to lists for JSON serialization
        mace_input = {
            "numbers": numbers.astype(int).tolist(),
            "positions": positions.astype(float).tolist(),
            "cell": cell.astype(float).tolist(),
            "pbc": pbc.astype(bool).tolist(),
        }

        # Add chemical formula for debugging
        formula = ase_atoms.get_chemical_formula()

        # Final validation
        if not mace_input["numbers"]:
            raise ValueError("Empty atomic numbers array")

        if not mace_input["positions"]:
            raise ValueError("Empty positions array")

        if len(mace_input["numbers"]) != len(mace_input["positions"]):
            raise ValueError("Mismatch between atomic numbers and positions array lengths")

        logger.info(
            f"Successfully converted CIF to MACE input: {formula} with {len(mace_input['numbers'])} atoms"
        )

        return {
            "success": True,
            "mace_input": mace_input,
            "formula": formula,
            "num_atoms": len(mace_input["numbers"]),
        }

    except Exception as e:
        logger.error(f"CIF to MACE conversion failed: {e}")
        return {"success": False, "error": str(e)}


def create_supercell_cif(cif_string: str, supercell_matrix: list) -> dict[str, Any]:
    """
    Creates a supercell from a CIF string and returns the supercell as a CIF string.
    Enhanced version with robust error handling for Chemeleon-generated CIFs.

    Args:
        cif_string: The crystal structure in CIF format.
        supercell_matrix: A 3x3 matrix defining the supercell (e.g., [[2,0,0],[0,2,0],[0,0,2]]).

    Returns:
        A dictionary with 'success' and 'cif_string' keys, or 'success' and 'error' keys.
    """
    try:
        if isinstance(cif_string, bytes):
            cif_string = cif_string.decode("utf-8")

        # Use our robust CIF parsing
        ase_atoms = _create_ase_atoms_from_cif_data(cif_string)

        # Log original structure info
        original_formula = ase_atoms.get_chemical_formula()
        original_num_atoms = len(ase_atoms)
        logger.info(f"Creating supercell for {original_formula} ({original_num_atoms} atoms)")

        # Create supercell
        supercell_atoms = make_supercell(ase_atoms, supercell_matrix)

        # Log supercell info
        supercell_formula = supercell_atoms.get_chemical_formula()
        supercell_num_atoms = len(supercell_atoms)
        logger.info(f"Created supercell: {supercell_formula} ({supercell_num_atoms} atoms)")

        # Write the supercell to a CIF string using temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        try:
            # Write supercell to temporary file
            write(tmp_filename, supercell_atoms, format="cif")

            # Read back the content
            with open(tmp_filename, encoding="utf-8") as f:
                supercell_cif_string = f.read()

            # Enhanced CIF post-processing to ensure chemical formula is included
            supercell_cif_string = _enhance_supercell_cif(supercell_cif_string, supercell_formula)

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)

        return {
            "success": True,
            "cif_string": supercell_cif_string,
            "original_formula": original_formula,
            "supercell_formula": supercell_formula,
            "original_atoms": original_num_atoms,
            "supercell_atoms": supercell_num_atoms,
        }

    except Exception as e:
        logger.error(f"Supercell creation failed: {e}")
        return {"success": False, "error": str(e)}


def _enhance_supercell_cif(cif_string: str, formula: str) -> str:
    """
    Enhance supercell CIF string to ensure chemical formula is properly included.

    Args:
        cif_string: Generated supercell CIF string
        formula: Chemical formula of the supercell

    Returns:
        Enhanced CIF string with proper chemical formula
    """
    # Check if chemical formula is already present
    if "_chemical_formula_sum" not in cif_string:
        # Add chemical formula after the data_ line
        lines = cif_string.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("data_"):
                lines.insert(i + 1, f"_chemical_formula_sum '{formula}'")
                break
        cif_string = "\n".join(lines)

    return cif_string


def validate_cif_string(cif_string: str) -> dict[str, Any]:
    """
    Validate a CIF string and return diagnostic information.

    Args:
        cif_string: CIF string to validate

    Returns:
        Dictionary with validation results and diagnostic info
    """
    try:
        ase_atoms = _create_ase_atoms_from_cif_data(cif_string)

        return {
            "success": True,
            "valid": True,
            "num_atoms": len(ase_atoms),
            "chemical_formula": ase_atoms.get_chemical_formula(),
            "volume": ase_atoms.get_volume(),
            "cell": ase_atoms.get_cell().tolist(),
            "pbc": ase_atoms.get_pbc().tolist(),
        }
    except Exception as e:
        return {"success": False, "valid": False, "error": str(e), "preprocessing_attempted": True}
