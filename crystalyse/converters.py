
from typing import Dict, Any
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

def convert_cif_to_mace_input(cif_string: str) -> Dict[str, Any]:
    """
    Converts a CIF string into a MACE-compatible dictionary.

    Args:
        cif_string: The crystal structure in CIF format.

    Returns:
        A dictionary with 'numbers', 'positions', 'cell', and 'pbc' keys.
    """
    try:
        p_structure = Structure.from_str(cif_string, fmt="cif")
        ase_atoms = AseAtomsAdaptor.get_atoms(p_structure)
        return {
            "success": True,
            "mace_input": {
                "numbers": ase_atoms.get_atomic_numbers().tolist(),
                "positions": ase_atoms.get_positions().tolist(),
                "cell": ase_atoms.get_cell().tolist(),
                "pbc": ase_atoms.get_pbc().tolist(),
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


from ase.build import make_supercell
from ase.io import write
import io

def create_supercell_cif(cif_string: str, supercell_matrix: list) -> Dict[str, Any]:
    """
    Creates a supercell from a CIF string and returns the supercell as a CIF string.

    Args:
        cif_string: The crystal structure in CIF format.
        supercell_matrix: A 3x3 matrix defining the supercell (e.g., [[2,0,0],[0,2,0],[0,0,2]]).

    Returns:
        A dictionary with 'success' and 'cif_string' keys, or 'success' and 'error' keys.
    """
    try:
        if isinstance(cif_string, bytes):
            cif_string = cif_string.decode('utf-8')
        p_structure = Structure.from_str(cif_string, fmt="cif")
        ase_atoms = AseAtomsAdaptor.get_atoms(p_structure)
        
        supercell_atoms = make_supercell(ase_atoms, supercell_matrix)
        
        # Write the supercell to a CIF string
        f = io.StringIO()
        write(f, supercell_atoms, format="cif")
        supercell_cif_string = f.getvalue()
        
        return {"success": True, "cif_string": supercell_cif_string}
    except Exception as e:
        return {"success": False, "error": str(e)}
