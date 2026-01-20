#!/usr/bin/env python3
"""
Universal CIF Visualizer for Crystalyse

This module provides comprehensive CIF visualization capabilities inspired by the
user's scaffold. It includes:
1. Universal HTML crystal viewer
2. Individual CIF to HTML conversion
3. Batch processing capabilities
4. Gallery generation for multiple structures

Usage:
    # Create universal viewer
    python -m crystalyse.output.universal_cif_visualizer create-viewer output.html

    # Convert single CIF to HTML
    python -m crystalyse.output.universal_cif_visualizer convert structure.cif

    # Create gallery from directory
    python -m crystalyse.output.universal_cif_visualizer gallery /path/to/cif/files
"""

import argparse
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class UniversalCIFVisualizer:
    """Universal CIF visualization system for Crystalyse."""

    def __init__(self, color_scheme: str = "cpk"):
        """Initialize with configurable color scheme."""
        self.universal_viewer_template = self._get_universal_viewer_template()
        self.color_scheme = color_scheme
        self._setup_color_scheme()

    def _setup_color_scheme(self):
        """Set up element colors based on scheme."""
        if self.color_scheme == "vesta":
            # Import VESTA colors from pymatviz
            from pymatviz.colors import ELEM_COLORS_VESTA

            self.element_colors = ELEM_COLORS_VESTA
        else:
            # Use default CPK colors (or could import Jmol colors)
            self.element_colors = None

    def create_universal_viewer(self, output_path: str) -> None:
        """Create a universal CIF viewer HTML file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.universal_viewer_template)
        print(f"✅ Universal CIF viewer created: {output_path}")

    def convert_cif_to_html(self, cif_path: str, output_path: str | None = None) -> str:
        """Convert a single CIF file to HTML visualization."""
        cif_file = Path(cif_path)
        if not cif_file.exists():
            raise FileNotFoundError(f"CIF file not found: {cif_path}")

        # Read CIF content
        with open(cif_file, encoding="utf-8") as f:
            cif_content = f.read()

        # Parse CIF data
        cif_data = self.parse_cif_data(cif_content)

        # Determine output filename
        if output_path is None:
            output_path = cif_file.parent / f"{cif_file.stem}_visualization.html"

        # Generate HTML
        html_content = self.create_individual_html(cif_content, cif_data, cif_file.name)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ HTML visualization created: {output_path}")
        return str(output_path)

    def create_gallery(self, cif_directory: str, output_dir: str | None = None) -> str:
        """Create a gallery of all CIF files in a directory."""
        cif_dir = Path(cif_directory)
        if not cif_dir.is_dir():
            raise NotADirectoryError(f"Directory not found: {cif_directory}")

        if output_dir is None:
            output_dir = cif_dir / "crystal_gallery"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True)

        # Find all CIF files
        cif_files = list(cif_dir.glob("*.cif"))
        if not cif_files:
            print("No CIF files found in the directory.")
            return str(output_dir)

        print(f"Found {len(cif_files)} CIF files. Processing...")

        structures = []

        for i, cif_file in enumerate(cif_files, 1):
            print(f"[{i}/{len(cif_files)}] Processing: {cif_file.name}")

            try:
                with open(cif_file, encoding="utf-8") as f:
                    cif_content = f.read()

                cif_data = self.parse_cif_data(cif_content)

                # Create individual HTML file
                html_filename = f"{cif_file.stem}.html"
                html_path = output_dir / html_filename

                html_content = self.create_individual_html(
                    cif_content, cif_data, cif_file.name, gallery_mode=True
                )

                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                structures.append(
                    {
                        "filename": html_filename,
                        "original_filename": cif_file.name,
                        "formula": cif_data["formula"],
                        "space_group": cif_data["space_group"],
                        "crystal_system": cif_data["crystal_system"],
                        "volume": cif_data["volume"] or "N/A",
                    }
                )

            except Exception as e:
                print(f"   ⚠️  Error processing {cif_file.name}: {e}")

        # Generate index page
        print("\\nGenerating gallery index...")
        self.create_gallery_index(structures, output_dir)

        print("\\n✅ Gallery created successfully!")
        print(f"📁 Output directory: {output_dir}")
        print(f"🌐 Open {output_dir}/index.html to view the gallery")

        return str(output_dir)

    def parse_cif_data(self, cif_content: str) -> dict[str, Any]:
        """Parse CIF content and extract key structural information."""
        data = {
            "formula": "Unknown",
            "cell_a": None,
            "cell_b": None,
            "cell_c": None,
            "angle_alpha": None,
            "angle_beta": None,
            "angle_gamma": None,
            "space_group": "Unknown",
            "crystal_system": "Unknown",
            "volume": None,
            "density": None,
        }

        # Parse cell parameters
        patterns = {
            "cell_a": r"_cell_length_a\s+([\d.]+)",
            "cell_b": r"_cell_length_b\s+([\d.]+)",
            "cell_c": r"_cell_length_c\s+([\d.]+)",
            "angle_alpha": r"_cell_angle_alpha\s+([\d.]+)",
            "angle_beta": r"_cell_angle_beta\s+([\d.]+)",
            "angle_gamma": r"_cell_angle_gamma\s+([\d.]+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, cif_content, re.IGNORECASE)
            if match:
                data[key] = float(match.group(1))

        # Parse space group with more comprehensive patterns
        space_group_patterns = [
            r'_space_group_name_H-M_alt\s+["\']([^"\']+)["\']',
            r'_symmetry_space_group_name_H-M\s+["\']([^"\']+)["\']',
            r'_space_group_name_H-M\s+["\']([^"\']+)["\']',
            r'_space_group_name_Hall\s+["\']([^"\']+)["\']',
            r"_space_group_IT_number\s+(\d+)",
            # Handle cases without quotes
            r"_space_group_name_H-M_alt\s+([^\s]+)",
            r"_symmetry_space_group_name_H-M\s+([^\s]+)",
            r"_space_group_name_H-M\s+([^\s]+)",
        ]

        for pattern in space_group_patterns:
            match = re.search(pattern, cif_content, re.IGNORECASE)
            if match:
                space_group_value = match.group(1).strip()
                if space_group_value and space_group_value.lower() not in ["unknown", "n/a", ""]:
                    data["space_group"] = space_group_value
                    break

        # Determine crystal system with comprehensive logic
        crystal_system_patterns = [
            r"_space_group_crystal_system\s+(\w+)",
            r"_symmetry_cell_setting\s+(\w+)",
            r"_space_group_lattice_type\s+(\w+)",
        ]

        for pattern in crystal_system_patterns:
            match = re.search(pattern, cif_content, re.IGNORECASE)
            if match:
                system = match.group(1).lower()
                if system in [
                    "cubic",
                    "tetragonal",
                    "orthorhombic",
                    "hexagonal",
                    "trigonal",
                    "monoclinic",
                    "triclinic",
                ]:
                    data["crystal_system"] = system
                    break

        # If crystal system not found, infer from space group
        if data["crystal_system"] == "Unknown" and data["space_group"] != "Unknown":
            data["crystal_system"] = self._infer_crystal_system_from_space_group(
                data["space_group"]
            )

        # If still unknown, try to infer from cell parameters
        if data["crystal_system"] == "Unknown":
            data["crystal_system"] = self._infer_crystal_system_from_cell_parameters(data)

        # Extract chemical formula with better patterns
        formula_patterns = [
            r'_chemical_formula_sum\s+["\']([^"\']+)["\']',
            r'_chemical_formula_structural\s+["\']([^"\']+)["\']',
            r'_chemical_formula_analytical\s+["\']([^"\']+)["\']',
            # Handle cases without quotes
            r"_chemical_formula_sum\s+([^\s]+)",
            r"_chemical_formula_structural\s+([^\s]+)",
        ]

        for pattern in formula_patterns:
            match = re.search(pattern, cif_content, re.IGNORECASE)
            if match:
                formula = match.group(1).strip()
                if formula and formula.lower() not in ["unknown", "n/a", ""]:
                    data["formula"] = formula
                    break

        # If no formula found, try to derive from atom sites
        if data["formula"] == "Unknown":
            data["formula"] = self._derive_formula_from_atom_sites(cif_content)

        # Calculate volume
        if all(
            data[k] is not None
            for k in ["cell_a", "cell_b", "cell_c", "angle_alpha", "angle_beta", "angle_gamma"]
        ):
            a, b, c = data["cell_a"], data["cell_b"], data["cell_c"]
            alpha = math.radians(data["angle_alpha"])
            beta = math.radians(data["angle_beta"])
            gamma = math.radians(data["angle_gamma"])

            volume = (
                a
                * b
                * c
                * math.sqrt(
                    1
                    - math.cos(alpha) ** 2
                    - math.cos(beta) ** 2
                    - math.cos(gamma) ** 2
                    + 2 * math.cos(alpha) * math.cos(beta) * math.cos(gamma)
                )
            )
            data["volume"] = round(volume, 2)

        # Parse density if available
        density_patterns = [
            r"_exptl_crystal_density_diffrn\s+([\d.]+)",
            r"_exptl_crystal_density_meas\s+([\d.]+)",
            r"_exptl_crystal_density\s+([\d.]+)",
        ]

        for pattern in density_patterns:
            match = re.search(pattern, cif_content, re.IGNORECASE)
            if match:
                data["density"] = float(match.group(1))
                break

        # Calculate density from atomic composition and volume if not provided
        if data["density"] is None and data["volume"] is not None:
            data["density"] = self._calculate_density_from_composition(cif_content, data["volume"])

        return data

    def _calculate_density_from_composition(self, cif_content: str, volume: float) -> float:
        """Calculate density from atomic composition and volume."""
        # Standard atomic masses (in amu)
        atomic_masses = {
            "H": 1.008,
            "He": 4.003,
            "Li": 6.941,
            "Be": 9.012,
            "B": 10.811,
            "C": 12.011,
            "N": 14.007,
            "O": 15.999,
            "F": 18.998,
            "Ne": 20.180,
            "Na": 22.990,
            "Mg": 24.305,
            "Al": 26.982,
            "Si": 28.086,
            "P": 30.974,
            "S": 32.065,
            "Cl": 35.453,
            "Ar": 39.948,
            "K": 39.098,
            "Ca": 40.078,
            "Sc": 44.956,
            "Ti": 47.867,
            "V": 50.942,
            "Cr": 51.996,
            "Mn": 54.938,
            "Fe": 55.845,
            "Co": 58.933,
            "Ni": 58.693,
            "Cu": 63.546,
            "Zn": 65.38,
            "Ga": 69.723,
            "Ge": 72.64,
            "As": 74.922,
            "Se": 78.96,
            "Br": 79.904,
            "Kr": 83.798,
            "Rb": 85.468,
            "Sr": 87.62,
            "Y": 88.906,
            "Zr": 91.224,
            "Nb": 92.906,
            "Mo": 95.96,
            "Tc": 98.0,
            "Ru": 101.07,
            "Rh": 102.906,
            "Pd": 106.42,
            "Ag": 107.868,
            "Cd": 112.411,
            "In": 114.818,
            "Sn": 118.710,
            "Sb": 121.760,
            "Te": 127.60,
            "I": 126.904,
            "Xe": 131.293,
            "Cs": 132.905,
            "Ba": 137.327,
            "La": 138.905,
            "Ce": 140.116,
            "Pr": 140.908,
            "Nd": 144.242,
            "Pm": 145.0,
            "Sm": 150.36,
            "Eu": 151.964,
            "Gd": 157.25,
            "Tb": 158.925,
            "Dy": 162.500,
            "Ho": 164.930,
            "Er": 167.259,
            "Tm": 168.934,
            "Yb": 173.054,
            "Lu": 174.967,
            "Hf": 178.49,
            "Ta": 180.948,
            "W": 183.84,
            "Re": 186.207,
            "Os": 190.23,
            "Ir": 192.217,
            "Pt": 195.084,
            "Au": 196.967,
            "Hg": 200.592,
            "Tl": 204.383,
            "Pb": 207.2,
            "Bi": 208.980,
            "Po": 209.0,
            "At": 210.0,
            "Rn": 222.0,
            "Fr": 223.0,
            "Ra": 226.0,
            "Ac": 227.0,
            "Th": 232.038,
            "Pa": 231.036,
            "U": 238.029,
            "Np": 237.0,
            "Pu": 244.0,
            "Am": 243.0,
            "Cm": 247.0,
            "Bk": 247.0,
            "Cf": 251.0,
            "Es": 252.0,
            "Fm": 257.0,
            "Md": 258.0,
            "No": 259.0,
            "Lr": 262.0,
        }

        # Parse atom site data from CIF
        atom_counts = {}

        # Look for atom site data in CIF
        atom_site_pattern = r"^\s*([A-Z][a-z]?)\d*\s+[A-Z][a-z]?\d*\s+[\d.]+\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s*(?:[\d.]+)?"
        matches = re.findall(atom_site_pattern, cif_content, re.MULTILINE)

        for match in matches:
            element = match
            if element in atomic_masses:
                atom_counts[element] = atom_counts.get(element, 0) + 1

        # If no atom site data found, try to parse from formula
        if not atom_counts:
            # Look for chemical formula
            formula_patterns = [
                r'_chemical_formula_sum\s+["\']([^"\']+)["\']',
                r'_chemical_formula_structural\s+["\']([^"\']+)["\']',
            ]

            for pattern in formula_patterns:
                match = re.search(pattern, cif_content, re.IGNORECASE)
                if match:
                    formula = match.group(1)
                    # Parse formula like "Cu2 Zn1 Sn1 Se4"
                    element_matches = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
                    for element, count in element_matches:
                        count = int(count) if count else 1
                        atom_counts[element] = atom_counts.get(element, 0) + count
                    break

        # Calculate total mass
        total_mass = 0.0
        for element, count in atom_counts.items():
            if element in atomic_masses:
                total_mass += atomic_masses[element] * count

        if total_mass > 0 and volume > 0:
            # Convert from amu/Å³ to g/cm³
            # 1 amu = 1.66054e-24 g
            # 1 Å³ = 1e-24 cm³
            amu_to_g = 1.66053906660e-24
            angstrom3_to_cm3 = 1e-24

            density = (total_mass * amu_to_g) / (volume * angstrom3_to_cm3)
            return round(density, 3)

        return None

    def _infer_crystal_system_from_space_group(self, space_group: str) -> str:
        """Infer crystal system from space group symbol."""
        space_group = space_group.strip().upper()

        # Cubic systems (195-230)
        cubic_patterns = [
            r"^P\s*2\d\d?3?$",
            r"^I\s*2\d\d?3?$",
            r"^F\s*2\d\d?3?$",
            r"^P\s*M\s*-?\s*3$",
            r"^I\s*M\s*-?\s*3$",
            r"^F\s*M\s*-?\s*3$",
            r"^P\s*N\s*-?\s*3$",
            r"^I\s*A\s*-?\s*3$",
            r"^F\s*D\s*-?\s*3$",
        ]

        # Tetragonal systems (75-142)
        tetragonal_patterns = [
            r"^P\s*4/?",
            r"^I\s*4/?",
            r"^P\s*4\d",
            r"^I\s*4\d",
            r"^P\s*-?\s*4",
            r"^I\s*-?\s*4",
            r"^P\s*4/M",
            r"^I\s*4/M",
        ]

        # Orthorhombic systems (16-74)
        orthorhombic_patterns = [
            r"^P\s*2\d\d\d$",
            r"^C\s*2\d\d\d$",
            r"^I\s*2\d\d\d$",
            r"^F\s*2\d\d\d$",
            r"^P\s*M\s*M\s*2",
            r"^C\s*M\s*M\s*2",
            r"^P\s*N\s*N\s*2",
            r"^P\s*M\s*A\s*2",
            r"^C\s*M\s*C\s*2",
            r"^I\s*M\s*M\s*2",
        ]

        # Hexagonal systems (168-194)
        hexagonal_patterns = [
            r"^P\s*6/?",
            r"^P\s*6\d",
            r"^P\s*-?\s*6",
            r"^P\s*6/M",
            r"^P\s*6\d\d",
            r"^P\s*-?\s*6\d\d",
        ]

        # Trigonal systems (143-167)
        trigonal_patterns = [
            r"^P\s*3/?",
            r"^R\s*3/?",
            r"^P\s*3\d",
            r"^R\s*3\d",
            r"^P\s*-?\s*3",
            r"^R\s*-?\s*3",
            r"^P\s*3\d\d",
            r"^R\s*3\d\d",
        ]

        # Monoclinic systems (3-15)
        monoclinic_patterns = [
            r"^P\s*2/?",
            r"^C\s*2/?",
            r"^P\s*M$",
            r"^C\s*M$",
            r"^P\s*2/M",
            r"^C\s*2/M",
            r"^P\s*2\d/M",
            r"^C\s*2\d/M",
        ]

        # Triclinic systems (1-2)
        triclinic_patterns = [r"^P\s*1$", r"^P\s*-?\s*1$"]

        # Check patterns in order
        pattern_systems = [
            (cubic_patterns, "cubic"),
            (tetragonal_patterns, "tetragonal"),
            (orthorhombic_patterns, "orthorhombic"),
            (hexagonal_patterns, "hexagonal"),
            (trigonal_patterns, "trigonal"),
            (monoclinic_patterns, "monoclinic"),
            (triclinic_patterns, "triclinic"),
        ]

        for patterns, system in pattern_systems:
            for pattern in patterns:
                if re.match(pattern, space_group, re.IGNORECASE):
                    return system

        # Special cases for common space groups
        common_space_groups = {
            "P1": "triclinic",
            "P-1": "triclinic",
            "P21/C": "monoclinic",
            "P21/N": "monoclinic",
            "C2/C": "monoclinic",
            "PNMA": "orthorhombic",
            "CMCM": "orthorhombic",
            "PBCA": "orthorhombic",
            "P4/MMM": "tetragonal",
            "I4/MMM": "tetragonal",
            "P42/MMM": "tetragonal",
            "PM-3M": "cubic",
            "IM-3M": "cubic",
            "FM-3M": "cubic",
            "P63/MMC": "hexagonal",
            "P6/MMM": "hexagonal",
            "R-3M": "trigonal",
            "P-3M1": "trigonal",
        }

        space_group_clean = space_group.replace(" ", "").replace("-", "-")
        for sg, system in common_space_groups.items():
            if space_group_clean.upper() == sg.upper():
                return system

        return "Unknown"

    def _infer_crystal_system_from_cell_parameters(self, data: dict[str, Any]) -> str:
        """Infer crystal system from cell parameters."""
        if not all(
            data[k] is not None
            for k in ["cell_a", "cell_b", "cell_c", "angle_alpha", "angle_beta", "angle_gamma"]
        ):
            return "Unknown"

        a, b, c = data["cell_a"], data["cell_b"], data["cell_c"]
        alpha, beta, gamma = data["angle_alpha"], data["angle_beta"], data["angle_gamma"]

        # Define tolerance for comparisons
        tol = 0.01

        # Check if angles are 90 degrees
        angles_90 = [abs(angle - 90) < tol for angle in [alpha, beta, gamma]]

        # Check if cell parameters are equal
        a_eq_b = abs(a - b) < tol
        b_eq_c = abs(b - c) < tol
        a_eq_c = abs(a - c) < tol

        # Triclinic: a≠b≠c, α≠β≠γ≠90°
        if not all(angles_90):
            return "triclinic"

        # If all angles are 90°
        if all(angles_90):
            # Cubic: a=b=c, α=β=γ=90°
            if a_eq_b and b_eq_c:
                return "cubic"
            # Tetragonal: a=b≠c, α=β=γ=90°
            elif a_eq_b and not b_eq_c:
                return "tetragonal"
            # Orthorhombic: a≠b≠c, α=β=γ=90°
            elif not a_eq_b and not b_eq_c and not a_eq_c:
                return "orthorhombic"

        # Monoclinic: a≠b≠c, α=γ=90°≠β
        if angles_90[0] and angles_90[2] and not angles_90[1]:
            return "monoclinic"

        # Hexagonal/Trigonal: a=b≠c, α=β=90°, γ=120°
        if a_eq_b and not b_eq_c and angles_90[0] and angles_90[1]:
            if abs(gamma - 120) < tol:
                return "hexagonal"
            elif abs(gamma - 60) < tol or abs(gamma - 120) < tol:
                return "trigonal"

        return "Unknown"

    def _derive_formula_from_atom_sites(self, cif_content: str) -> str:
        """Derive chemical formula from atom site data."""
        # Look for atom site loops
        atom_patterns = [
            r"^\s*([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # Standard format
            r"^\s*([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # With occupancy
            r"_atom_site_label\s+([A-Z][a-z]?)\d*",  # From label field
        ]

        atom_counts = {}
        for pattern in atom_patterns:
            matches = re.findall(pattern, cif_content, re.MULTILINE)
            for match in matches:
                atom = match.strip()
                if len(atom) <= 2 and atom.isalpha():  # Valid element symbol
                    atom_counts[atom] = atom_counts.get(atom, 0) + 1

        if not atom_counts:
            return "Unknown"

        # Sort by element symbol and create formula
        formula_parts = []
        for atom in sorted(atom_counts.keys()):
            count = atom_counts[atom]
            if count > 1:
                formula_parts.append(f"{atom}{count}")
            else:
                formula_parts.append(atom)

        return "".join(formula_parts) if formula_parts else "Unknown"

    def _get_point_group_from_space_group(self, space_group: str) -> str:
        """Get point group from space group symbol."""
        if space_group == "Unknown":
            return "Unknown"

        # Common space group to point group mappings
        point_group_map = {
            "P1": "1",
            "P-1": "-1",
            "P21/C": "2/m",
            "P21/N": "2/m",
            "C2/C": "2/m",
            "PNMA": "mmm",
            "CMCM": "mmm",
            "PBCA": "mmm",
            "P4/MMM": "4/mmm",
            "I4/MMM": "4/mmm",
            "P42/MMM": "4/mmm",
            "PM-3M": "m-3m",
            "IM-3M": "m-3m",
            "FM-3M": "m-3m",
            "P63/MMC": "6/mmm",
            "P6/MMM": "6/mmm",
            "R-3M": "-3m",
            "P-3M1": "-3m",
        }

        space_group_clean = space_group.replace(" ", "").replace("-", "-").upper()

        # Look for exact match first
        for sg, pg in point_group_map.items():
            if space_group_clean == sg.upper():
                return pg

        # Try to derive from space group symbol patterns
        sg_upper = space_group.upper().strip()

        # Cubic point groups
        if any(pattern in sg_upper for pattern in ["M-3M", "M3M"]):
            return "m-3m"
        elif any(pattern in sg_upper for pattern in ["M-3", "M3"]):
            return "m-3"
        elif "23" in sg_upper:
            return "23"

        # Hexagonal/Trigonal point groups
        elif "6/MMM" in sg_upper or "6MMM" in sg_upper:
            return "6/mmm"
        elif "6/M" in sg_upper or "6M" in sg_upper:
            return "6/m"
        elif "6" in sg_upper:
            return "6"
        elif "-3M" in sg_upper or "3M" in sg_upper:
            return "-3m"
        elif "-3" in sg_upper:
            return "-3"
        elif "3" in sg_upper:
            return "3"

        # Tetragonal point groups
        elif "4/MMM" in sg_upper or "4MMM" in sg_upper:
            return "4/mmm"
        elif "4/M" in sg_upper or "4M" in sg_upper:
            return "4/m"
        elif "4" in sg_upper:
            return "4"

        # Orthorhombic point groups
        elif "MMM" in sg_upper:
            return "mmm"
        elif "MM2" in sg_upper:
            return "mm2"
        elif "222" in sg_upper:
            return "222"

        # Monoclinic point groups
        elif "2/M" in sg_upper or "2M" in sg_upper:
            return "2/m"
        elif "2" in sg_upper:
            return "2"
        elif "M" in sg_upper:
            return "m"

        # Triclinic point groups
        elif sg_upper == "P1":
            return "1"
        elif sg_upper == "P-1":
            return "-1"

        return "Unknown"

    def _format_cell_parameter(self, value: float, units: str = "", decimal_places: int = 3) -> str:
        """Format cell parameter with proper units and decimal places."""
        if value is None:
            return "N/A"
        return f"{value:.{decimal_places}f} {units}".strip()

    def _format_density(self, value: float) -> str:
        """Format density value."""
        if value is None:
            return "N/A"
        return f"{value:.2f} g/cm³"

    def _format_volume(self, value: float) -> str:
        """Format volume value."""
        if value is None:
            return "N/A"
        return f"{value:.2f} Å³"

    def create_individual_html(
        self, cif_content: str, cif_data: dict[str, Any], filename: str, gallery_mode: bool = False
    ) -> str:
        """Create HTML visualization for individual crystal structure."""
        formula_html = re.sub(r"(\d+)", r"<sub>\1</sub>", cif_data["formula"])
        escaped_cif = cif_content.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

        back_link = ""
        if gallery_mode:
            back_link = '<a href="index.html" class="back-link">← Back to Gallery</a>'

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Crystal Structure: {cif_data["formula"]}</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .header p {{
            margin: 5px 0;
            font-size: 1.1em;
        }}
        .crystalyse-logo {{
            font-size: 1.5em;
            float: right;
            margin-top: -10px;
        }}
        .back-link {{
            color: #fff;
            text-decoration: none;
            margin-bottom: 10px;
            display: inline-block;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .structure-container {{
            margin: 20px 0;
            border: 1px solid #ddd;
            padding: 20px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}
        .structure-container h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        .structure-grid {{
            display: grid;
            grid-template-columns: minmax(350px, 1fr) 1fr;
            gap: 30px;
            margin-top: 15px;
            align-items: start;
        }}
        .viewer-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .viewer-section h3 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        .viewer-container {{
            position: relative;
            width: 100%;
            height: 400px;
            border: 1px solid #ccc;
            border-radius: 5px;
            overflow: hidden;
            background: white;
        }}
        .viewer-container #viewer {{
            width: 100%;
            height: 100%;
        }}
        .viewer-container canvas {{
            position: absolute !important;
            inset: 0;
            width: 100% !important;
            height: 100% !important;
        }}
        .analysis-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .analysis-section h3 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        .analysis-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            background: white;
            border-radius: 5px;
            overflow: hidden;
        }}
        .analysis-table td {{
            border: 1px solid #e9ecef;
            padding: 12px;
            text-align: left;
            vertical-align: top;
        }}
        .analysis-table td:first-child {{
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
            width: 30%;
        }}
        .analysis-table td:last-child {{
            background-color: white;
            color: #212529;
        }}
        .controls {{
            margin-top: 20px;
            padding: 15px;
            background: #e9ecef;
            border-radius: 5px;
            font-size: 0.9em;
        }}
        .controls h4 {{
            margin-top: 0;
            margin-bottom: 10px;
            color: #495057;
        }}
        .controls ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .controls li {{
            margin-bottom: 5px;
            color: #6c757d;
        }}
        .crystal-badge {{
            background: #28a745;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .color-legend {{
            margin-top: 20px;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .color-legend h3 {{
            margin-top: 0;
            margin-bottom: 15px;
            color: #495057;
            font-size: 1.1em;
        }}
        .legend-items {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 5px 0;
        }}
        .color-box {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #ccc;
            flex-shrink: 0;
        }}
        .element-info {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.9em;
        }}
        .element-name {{
            font-weight: bold;
            color: #333;
        }}
        .element-symbol {{
            color: #666;
            font-weight: normal;
        }}
        .element-color {{
            color: #888;
            font-family: monospace;
            font-size: 0.85em;
        }}
        @media (max-width: 768px) {{
            .structure-grid {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 1.5em;
            }}
            .crystalyse-logo {{
                float: none;
                margin-top: 10px;
            }}
            .legend-items {{
                max-height: 200px;
                overflow-y: auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        {back_link}
        <div class="crystalyse-logo">🔬</div>
        <h1>Crystal Structure Analysis: {formula_html}</h1>
        <p>Generated by Crystalyse with Chemeleon CSP</p>
    </div>

    <div class="structure-container">
        <h2>📊 Structure 1</h2>
        <div class="structure-grid">
            <div class="viewer-section">
                <h3>🧊 3D Visualization</h3>
                <div class="viewer-container">
                    <div id="viewer"></div>
                </div>
                <div class="controls">
                    <h4>Controls:</h4>
                    <ul>
                        <li>Mouse drag: Rotate structure</li>
                        <li>Mouse wheel: Zoom in/out</li>
                        <li>Right-click drag: Pan</li>
                    </ul>
                </div>
                {self._create_color_legend_html(cif_content)}
            </div>

            <div class="analysis-section">
                <h3>🧪 Structural Analysis</h3>
                <table class="analysis-table">
                    <tbody>
                        <tr><td>Formula</td><td><strong>{formula_html}</strong></td></tr>
                        <tr><td>Volume</td><td>{self._format_volume(cif_data["volume"])}</td></tr>
                        <tr><td>Density</td><td>{self._format_density(cif_data["density"])}</td></tr>
                        <tr><td>a</td><td>{self._format_cell_parameter(cif_data["cell_a"], "Å")}</td></tr>
                        <tr><td>b</td><td>{self._format_cell_parameter(cif_data["cell_b"], "Å")}</td></tr>
                        <tr><td>c</td><td>{self._format_cell_parameter(cif_data["cell_c"], "Å")}</td></tr>
                        <tr><td>α</td><td>{self._format_cell_parameter(cif_data["angle_alpha"], "°", 2)}</td></tr>
                        <tr><td>β</td><td>{self._format_cell_parameter(cif_data["angle_beta"], "°", 2)}</td></tr>
                        <tr><td>γ</td><td>{self._format_cell_parameter(cif_data["angle_gamma"], "°", 2)}</td></tr>
                        <tr><td>Space Group</td><td><strong>{cif_data["space_group"]}</strong></td></tr>
                        <tr><td>Crystal System</td><td><span class="crystal-badge">{cif_data["crystal_system"]}</span></td></tr>
                        <tr><td>Point Group</td><td>{self._get_point_group_from_space_group(cif_data["space_group"])}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Initialize 3Dmol.js viewer
        function initViewer() {{
            const viewer = $3Dmol.createViewer("viewer");

            // Add CIF structure
            const cifData = `{escaped_cif}`;
            viewer.addModel(cifData, "cif");

            // Apply custom colors BEFORE setting style (important for color precedence)
            {self._generate_3dmol_colors()}

            // Set visualization style
            viewer.setStyle({{}}, {{
                stick: {{ radius: 0.15 }},
                sphere: {{ scale: 0.3 }}
            }});

            // Add unit cell
            viewer.addUnitCell();

            // Optimize view
            viewer.zoomTo();
            viewer.render();
        }}

        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initViewer);
    </script>
</body>
</html>"""

        return html_template

    def _generate_3dmol_colors(self) -> str:
        """Generate 3dmol.js color configuration."""
        if not self.element_colors:
            return ""

        color_commands = []
        for element, (r, g, b) in self.element_colors.items():
            # Convert RGB 0-1 to hex (pymatviz uses 0-1 range)
            hex_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
            color_commands.append(f'viewer.setColorByElement("{element}", "{hex_color}");')

        return "\n            ".join(color_commands)

    def create_gallery_index(self, structures: list[dict], output_dir: Path) -> None:
        """Generate index page with all crystal structures."""
        cards_html = ""

        for structure in structures:
            formula_html = re.sub(r"(\d+)", r"<sub>\1</sub>", structure["formula"])

            cards_html += f'''
        <div class="crystal-card">
            <a href="{structure["filename"]}" class="card-link">
                <div class="card-header">
                    <h3>{formula_html}</h3>
                    <span class="crystal-system">{structure["crystal_system"]}</span>
                </div>
                <div class="card-body">
                    <p><strong>Space Group:</strong> {structure["space_group"]}</p>
                    <p><strong>Volume:</strong> {structure["volume"]} Å³</p>
                    <p class="filename">{structure["original_filename"]}</p>
                </div>
            </a>
        </div>'''

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Crystal Structure Gallery - Crystalyse</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .stats {{
            margin-top: 15px;
            font-size: 1.2em;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .crystal-card {{
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .crystal-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
        }}
        .card-link {{
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        .card-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            position: relative;
        }}
        .card-header h3 {{
            margin: 0;
            font-size: 1.5em;
        }}
        .crystal-system {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 255, 255, 0.2);
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            text-transform: capitalize;
        }}
        .card-body {{
            padding: 15px;
        }}
        .card-body p {{
            margin: 5px 0;
        }}
        .filename {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px !important;
            font-style: italic;
        }}
        .filter-bar {{
            background: #fff;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}
        .filter-bar input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }}
        .no-results {{
            text-align: center;
            color: #666;
            font-size: 1.2em;
            margin-top: 50px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Crystal Structure Gallery</h1>
        <div class="stats">
            {len(structures)} structures • Generated by Crystalyse • {datetime.now().strftime("%Y-%m-%d %H:%M")}
        </div>
    </div>

    <div class="filter-bar">
        <input type="text" id="searchInput" placeholder="Search by formula, space group, or filename..." />
    </div>

    <div class="gallery" id="gallery">
        {cards_html}
    </div>

    <div class="no-results" id="noResults" style="display: none;">
        No structures found matching your search.
    </div>

    <script>
        const searchInput = document.getElementById('searchInput');
        const gallery = document.getElementById('gallery');
        const noResults = document.getElementById('noResults');
        const cards = document.querySelectorAll('.crystal-card');

        searchInput.addEventListener('input', (e) => {{
            const searchTerm = e.target.value.toLowerCase();
            let visibleCount = 0;

            cards.forEach(card => {{
                const text = card.textContent.toLowerCase();
                if (text.includes(searchTerm)) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }});
    </script>
</body>
</html>"""

        with open(output_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(index_html)

    def _get_universal_viewer_template(self) -> str:
        """Get the universal CIF viewer HTML template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Universal Crystal Structure Viewer - Crystalyse</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        /* General styles */
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        /* File Upload */
        .upload-container {
            margin: 20px 0;
            padding: 20px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .file-input-wrapper {
            display: inline-block;
            position: relative;
            overflow: hidden;
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .file-input-wrapper:hover {
            background-color: #45a049;
        }

        .file-input-wrapper input[type="file"] {
            position: absolute;
            left: -9999px;
        }

        /* Containers */
        .structure-container {
            margin: 20px 0;
            border: 1px solid #ddd;
            padding: 20px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            display: none;
        }

        .structure-grid {
            display: grid;
            grid-template-columns: minmax(320px, 1fr) 1fr;
            gap: 20px;
            margin-top: 15px;
            align-items: start;
        }

        /* 3D Viewer */
        .viewer-container {
            position: relative;
            width: 100%;
            height: 400px;
            border: 1px solid #ccc;
            border-radius: 5px;
            overflow: hidden;
        }

        .viewer-container .viewer {
            width: 100%;
            height: 100%;
        }

        .viewer-container canvas {
            position: absolute !important;
            inset: 0;
            width: 100% !important;
            height: 100% !important;
        }

        /* Table */
        .analysis-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .analysis-table th,
        .analysis-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }

        .analysis-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }

        /* Utility */
        .formula {
            font-family: "Courier New", monospace;
            background-color: #e9ecef;
            padding: 2px 5px;
            border-radius: 3px;
        }

        .error {
            color: #d32f2f;
            margin-top: 10px;
        }

        /* Direct Input */
        .input-method {
            margin: 10px 0;
        }

        .cif-textarea {
            width: 100%;
            height: 200px;
            font-family: monospace;
            font-size: 12px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 10px 0;
        }

        .load-button {
            background-color: #2196F3;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .load-button:hover {
            background-color: #1976D2;
        }

        .tab-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab-button {
            padding: 10px 20px;
            border: 1px solid #ddd;
            background-color: #f5f5f5;
            cursor: pointer;
            border-radius: 5px 5px 0 0;
            transition: all 0.3s;
        }

        .tab-button.active {
            background-color: #fff;
            border-bottom: 1px solid #fff;
            font-weight: bold;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>🔬 Universal Crystal Structure Viewer</h1>
        <p>Load any CIF file to visualise crystal structures | Powered by Crystalyse</p>
    </div>

    <!-- Input Section -->
    <div class="upload-container">
        <h2>📂 Load Crystal Structure</h2>

        <div class="tab-buttons">
            <div class="tab-button active" onclick="switchTab('file')">Upload File</div>
            <div class="tab-button" onclick="switchTab('text')">Paste CIF Data</div>
        </div>

        <div id="file-tab" class="tab-content active">
            <div class="file-input-wrapper">
                <span>Choose CIF File</span>
                <input type="file" id="fileInput" accept=".cif" onchange="handleFileSelect(event)">
            </div>
            <p style="margin-top: 10px; color: #666;">Supported format: .cif</p>
        </div>

        <div id="text-tab" class="tab-content">
            <textarea id="cifTextarea" class="cif-textarea" placeholder="Paste your CIF data here..."></textarea>
            <button class="load-button" onclick="loadFromText()">Load CIF Data</button>
        </div>

        <div id="error-message" class="error"></div>
    </div>

    <!-- Structure Section -->
    <div id="structureContainer" class="structure-container">
        <h2>📊 Crystal Structure</h2>
        <div class="structure-grid">
            <!-- 3D Viewer Column -->
            <div>
                <h3>🧊 3D Visualisation</h3>
                <div class="viewer-container">
                    <div id="viewer" class="viewer"></div>
                </div>
            </div>

            <!-- Analysis Column -->
            <div>
                <h3>📋 Structural Analysis</h3>
                <table class="analysis-table">
                    <tbody id="analysisTableBody">
                        <!-- Data will be populated here -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- JavaScript -->
    <script>
        let viewer = null;

        function switchTab(tab) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            if (tab === 'file') {
                document.querySelector('.tab-button:nth-child(1)').classList.add('active');
                document.getElementById('file-tab').classList.add('active');
            } else {
                document.querySelector('.tab-button:nth-child(2)').classList.add('active');
                document.getElementById('text-tab').classList.add('active');
            }
        }

        function parseCIF(cifContent) {
            const data = {
                cell_length_a: null,
                cell_length_b: null,
                cell_length_c: null,
                cell_angle_alpha: null,
                cell_angle_beta: null,
                cell_angle_gamma: null,
                space_group: null,
                formula: null,
                volume: null,
                atoms: []
            };

            // Parse cell parameters
            const cellParams = {
                '_cell_length_a': 'cell_length_a',
                '_cell_length_b': 'cell_length_b',
                '_cell_length_c': 'cell_length_c',
                '_cell_angle_alpha': 'cell_angle_alpha',
                '_cell_angle_beta': 'cell_angle_beta',
                '_cell_angle_gamma': 'cell_angle_gamma'
            };

            for (const [cifKey, dataKey] of Object.entries(cellParams)) {
                const regex = new RegExp(`${cifKey}\\\\s+([\\\\d.]+)`, 'i');
                const match = cifContent.match(regex);
                if (match) {
                    data[dataKey] = parseFloat(match[1]);
                }
            }

            // Parse space group
            const spaceGroupRegex = /_space_group_name_H-M_alt\\s+'([^']+)'|_symmetry_space_group_name_H-M\\s+'([^']+)'/i;
            const spaceGroupMatch = cifContent.match(spaceGroupRegex);
            if (spaceGroupMatch) {
                data.space_group = spaceGroupMatch[1] || spaceGroupMatch[2];
            }

            // Calculate volume if we have all cell parameters
            if (data.cell_length_a && data.cell_length_b && data.cell_length_c) {
                const a = data.cell_length_a;
                const b = data.cell_length_b;
                const c = data.cell_length_c;
                const alpha = data.cell_angle_alpha * Math.PI / 180;
                const beta = data.cell_angle_beta * Math.PI / 180;
                const gamma = data.cell_angle_gamma * Math.PI / 180;

                data.volume = a * b * c * Math.sqrt(
                    1 - Math.cos(alpha)**2 - Math.cos(beta)**2 - Math.cos(gamma)**2
                    + 2 * Math.cos(alpha) * Math.cos(beta) * Math.cos(gamma)
                );
            }

            // Extract unique atom types for formula
            const atomTypes = new Set();
            const atomLines = cifContent.match(/^[A-Z][a-z]?\\d*\\s+[\\d.-]+\\s+[\\d.-]+\\s+[\\d.-]+/gm);
            if (atomLines) {
                atomLines.forEach(line => {
                    const atomType = line.match(/^([A-Z][a-z]?)/)[1];
                    atomTypes.add(atomType);
                });
            }

            if (atomTypes.size > 0) {
                data.formula = Array.from(atomTypes).sort().join('');
            }

            return data;
        }

        function updateAnalysisTable(cifData) {
            const tbody = document.getElementById('analysisTableBody');
            tbody.innerHTML = '';

            const rows = [
                { label: 'Formula', value: cifData.formula || 'N/A' },
                { label: 'Volume', value: cifData.volume ? `${cifData.volume.toFixed(2)} Å³` : 'N/A' },
                { label: 'a', value: cifData.cell_length_a ? `${cifData.cell_length_a.toFixed(3)} Å` : 'N/A' },
                { label: 'b', value: cifData.cell_length_b ? `${cifData.cell_length_b.toFixed(3)} Å` : 'N/A' },
                { label: 'c', value: cifData.cell_length_c ? `${cifData.cell_length_c.toFixed(3)} Å` : 'N/A' },
                { label: 'α', value: cifData.cell_angle_alpha ? `${cifData.cell_angle_alpha.toFixed(2)}°` : 'N/A' },
                { label: 'β', value: cifData.cell_angle_beta ? `${cifData.cell_angle_beta.toFixed(2)}°` : 'N/A' },
                { label: 'γ', value: cifData.cell_angle_gamma ? `${cifData.cell_angle_gamma.toFixed(2)}°` : 'N/A' },
                { label: 'Space Group', value: cifData.space_group ? `<strong>${cifData.space_group}</strong>` : 'N/A' }
            ];

            rows.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${row.label}</td><td>${row.value}</td>`;
                tbody.appendChild(tr);
            });
        }

        function visualiseCIF(cifContent) {
            // Clear any existing viewer
            if (viewer) {
                viewer.clear();
            }

            // Create new viewer
            viewer = $3Dmol.createViewer("viewer");

            // Add the CIF model
            viewer.addModel(cifContent, "cif");

            // Set visualisation style
            viewer.setStyle({
                stick: { radius: 0.15 },
                sphere: { scale: 0.3 }
            });

            // Add unit cell
            viewer.addUnitCell();

            // Zoom and render
            viewer.zoomTo();
            viewer.render();

            // Parse CIF data and update table
            const cifData = parseCIF(cifContent);
            updateAnalysisTable(cifData);

            // Show the structure container
            document.getElementById('structureContainer').style.display = 'block';
            document.getElementById('error-message').textContent = '';
        }

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    visualiseCIF(e.target.result);
                } catch (error) {
                    document.getElementById('error-message').textContent =
                        'Error loading CIF file: ' + error.message;
                }
            };
            reader.readAsText(file);
        }

        function loadFromText() {
            const cifContent = document.getElementById('cifTextarea').value.trim();
            if (!cifContent) {
                document.getElementById('error-message').textContent = 'Please paste CIF data first';
                return;
            }

            try {
                visualiseCIF(cifContent);
            } catch (error) {
                document.getElementById('error-message').textContent =
                    'Error parsing CIF data: ' + error.message;
            }
        }
    </script>
</body>
</html>"""

    def _get_element_colors_from_cif(self, cif_content: str) -> dict[str, str]:
        """Extract elements from CIF and get their colors."""
        # Extract unique elements from the CIF
        elements = set()

        # Look for atom site data
        atom_patterns = [
            r"^\s*([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # Standard format
            r"^\s*([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # With occupancy
            r"^\s*([A-Z][a-z]?)\s+([A-Z][a-z]?\d*)\s+[\d.]+\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+",  # With label
        ]

        for pattern in atom_patterns:
            matches = re.findall(pattern, cif_content, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    element = match[0]
                else:
                    element = match

                if len(element) <= 2 and element.isalpha():
                    elements.add(element)

        # If no elements found, try to extract from formula
        if not elements:
            formula_patterns = [
                r'_chemical_formula_sum\s+["\']([^"\']+)["\']',
                r'_chemical_formula_structural\s+["\']([^"\']+)["\']',
            ]

            for pattern in formula_patterns:
                match = re.search(pattern, cif_content, re.IGNORECASE)
                if match:
                    formula = match.group(1)
                    # Extract elements from formula (e.g., "P2 Si1 Zn1" -> P, Si, Zn)
                    element_matches = re.findall(r"([A-Z][a-z]?)", formula)
                    elements.update(element_matches)
                    break

        # Get colors for each element
        element_colors = {}
        for element in sorted(elements):
            if self.element_colors and element in self.element_colors:
                # Convert RGB 0-1 to hex
                r, g, b = self.element_colors[element]
                hex_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
                element_colors[element] = hex_color
            else:
                # Default colors for common elements if no color scheme
                default_colors = {
                    "H": "#FFFFFF",  # White
                    "C": "#909090",  # Gray
                    "N": "#3050F8",  # Blue
                    "O": "#FF0D0D",  # Red
                    "P": "#FF1493",  # Deep Pink
                    "Si": "#DAA520",  # Goldenrod
                    "Zn": "#7FFFD4",  # Aquamarine
                    "Na": "#AB5CF2",  # Purple
                    "Cl": "#1FF01F",  # Green
                    "Ti": "#BFC2C7",  # Gray
                    "Fe": "#E06633",  # Orange
                    "Ca": "#3DFF00",  # Lime
                    "Mg": "#8AFF00",  # Yellow-green
                    "Al": "#BFA6A6",  # Light gray
                    "K": "#8F40D4",  # Purple
                    "S": "#FFFF30",  # Yellow
                    "Cu": "#C88033",  # Copper
                    "Ni": "#50D050",  # Green
                    "Co": "#F090A0",  # Pink
                    "Mn": "#9C7AC7",  # Purple
                    "Cr": "#8A99C7",  # Blue-gray
                    "Li": "#CC80FF",  # Light purple
                    "Be": "#C2FF00",  # Yellow-green
                    "B": "#FFB5B5",  # Light pink
                    "F": "#90E050",  # Light green
                    "Ne": "#B3E3F5",  # Light blue
                    "Ar": "#80D1E3",  # Light blue
                    "Br": "#A62929",  # Dark red
                    "I": "#940094",  # Purple
                    "He": "#D9FFFF",  # Very light cyan
                    "Pb": "#575961",  # Dark gray
                    "Sn": "#668080",  # Blue-gray
                    "Ge": "#668F8F",  # Gray-green
                    "As": "#BD80E3",  # Light purple
                    "Se": "#FFA100",  # Orange
                    "Cd": "#FFD98F",  # Light yellow
                    "Hg": "#B8B8D0",  # Light gray
                    "Au": "#FFD123",  # Gold
                    "Ag": "#C0C0C0",  # Silver
                    "Pt": "#D0D0E0",  # Light gray
                    "Pd": "#006985",  # Dark blue
                    "Ru": "#248F8F",  # Teal
                    "Rh": "#0A7D8C",  # Dark teal
                    "Ir": "#175487",  # Dark blue
                    "Os": "#266696",  # Blue
                    "Re": "#267DAB",  # Blue
                    "W": "#2194D6",  # Blue
                    "Ta": "#4DA6FF",  # Light blue
                    "Hf": "#4DC2FF",  # Light blue
                    "Lu": "#00BFC2",  # Cyan
                    "Yb": "#00C957",  # Green
                    "Tm": "#00D452",  # Green
                    "Er": "#00E675",  # Green
                    "Ho": "#00F778",  # Green
                    "Dy": "#1FFFC7",  # Cyan
                    "Tb": "#30FFC7",  # Cyan
                    "Gd": "#45FFC7",  # Cyan
                    "Eu": "#61FFC7",  # Cyan
                    "Sm": "#8FFFC7",  # Light cyan
                    "Pm": "#A3FFC7",  # Light cyan
                    "Nd": "#C7FFC7",  # Light cyan
                    "Pr": "#D9FFC7",  # Light cyan
                    "Ce": "#FFFFC7",  # Light yellow
                    "La": "#70D4FF",  # Light blue
                    "Ba": "#00C900",  # Green
                    "Cs": "#57178F",  # Purple
                    "Xe": "#429EB0",  # Blue-green
                    "Kr": "#5CB8D1",  # Blue
                    "Rb": "#702EB0",  # Purple
                    "Sr": "#00FF00",  # Green
                    "Y": "#94FFFF",  # Cyan
                    "Zr": "#94E0E0",  # Light cyan
                    "Nb": "#73C2C9",  # Cyan
                    "Mo": "#54B5B5",  # Cyan
                    "Tc": "#3B9E9E",  # Cyan
                    "V": "#A6A6AB",  # Gray
                    "Sc": "#E6E6E6",  # Light gray
                }
                element_colors[element] = default_colors.get(element, "#CCCCCC")  # Default gray

        return element_colors

    def _get_element_name(self, symbol: str) -> str:
        """Get full element name from symbol."""
        element_names = {
            "H": "Hydrogen",
            "He": "Helium",
            "Li": "Lithium",
            "Be": "Beryllium",
            "B": "Boron",
            "C": "Carbon",
            "N": "Nitrogen",
            "O": "Oxygen",
            "F": "Fluorine",
            "Ne": "Neon",
            "Na": "Sodium",
            "Mg": "Magnesium",
            "Al": "Aluminum",
            "Si": "Silicon",
            "P": "Phosphorus",
            "S": "Sulfur",
            "Cl": "Chlorine",
            "Ar": "Argon",
            "K": "Potassium",
            "Ca": "Calcium",
            "Sc": "Scandium",
            "Ti": "Titanium",
            "V": "Vanadium",
            "Cr": "Chromium",
            "Mn": "Manganese",
            "Fe": "Iron",
            "Co": "Cobalt",
            "Ni": "Nickel",
            "Cu": "Copper",
            "Zn": "Zinc",
            "Ga": "Gallium",
            "Ge": "Germanium",
            "As": "Arsenic",
            "Se": "Selenium",
            "Br": "Bromine",
            "Kr": "Krypton",
            "Rb": "Rubidium",
            "Sr": "Strontium",
            "Y": "Yttrium",
            "Zr": "Zirconium",
            "Nb": "Niobium",
            "Mo": "Molybdenum",
            "Tc": "Technetium",
            "Ru": "Ruthenium",
            "Rh": "Rhodium",
            "Pd": "Palladium",
            "Ag": "Silver",
            "Cd": "Cadmium",
            "In": "Indium",
            "Sn": "Tin",
            "Sb": "Antimony",
            "Te": "Tellurium",
            "I": "Iodine",
            "Xe": "Xenon",
            "Cs": "Cesium",
            "Ba": "Barium",
            "La": "Lanthanum",
            "Ce": "Cerium",
            "Pr": "Praseodymium",
            "Nd": "Neodymium",
            "Pm": "Promethium",
            "Sm": "Samarium",
            "Eu": "Europium",
            "Gd": "Gadolinium",
            "Tb": "Terbium",
            "Dy": "Dysprosium",
            "Ho": "Holmium",
            "Er": "Erbium",
            "Tm": "Thulium",
            "Yb": "Ytterbium",
            "Lu": "Lutetium",
            "Hf": "Hafnium",
            "Ta": "Tantalum",
            "W": "Tungsten",
            "Re": "Rhenium",
            "Os": "Osmium",
            "Ir": "Iridium",
            "Pt": "Platinum",
            "Au": "Gold",
            "Hg": "Mercury",
            "Tl": "Thallium",
            "Pb": "Lead",
            "Bi": "Bismuth",
            "Po": "Polonium",
            "At": "Astatine",
            "Rn": "Radon",
            "Fr": "Francium",
            "Ra": "Radium",
            "Ac": "Actinium",
            "Th": "Thorium",
            "Pa": "Protactinium",
            "U": "Uranium",
            "Np": "Neptunium",
            "Pu": "Plutonium",
            "Am": "Americium",
            "Cm": "Curium",
            "Bk": "Berkelium",
            "Cf": "Californium",
            "Es": "Einsteinium",
            "Fm": "Fermium",
            "Md": "Mendelevium",
            "No": "Nobelium",
            "Lr": "Lawrencium",
        }
        return element_names.get(symbol, symbol)

    def _create_color_legend_html(self, cif_content: str) -> str:
        """Create HTML for the color legend panel."""
        element_colors = self._get_element_colors_from_cif(cif_content)

        if not element_colors:
            return ""

        legend_items = []
        for element, color in element_colors.items():
            element_name = self._get_element_name(element)
            legend_items.append(f"""
                <div class="legend-item">
                    <div class="color-box" style="background-color: {color};"></div>
                    <div class="element-info">
                        <span class="element-name">{element_name}</span>
                        <span class="element-symbol">({element})</span>
                        <span class="element-color">{color.upper()}</span>
                    </div>
                </div>
            """)

        return f"""
            <div class="color-legend">
                <h3>🎨 Color Legend</h3>
                <div class="legend-items">
                    {"".join(legend_items)}
                </div>
            </div>
        """


def main():
    """Command line interface for the universal CIF visualizer."""
    parser = argparse.ArgumentParser(description="Universal CIF Visualizer for Crystalyse")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create universal viewer command
    viewer_parser = subparsers.add_parser(
        "create-viewer", help="Create universal CIF viewer HTML file"
    )
    viewer_parser.add_argument("output", help="Output HTML file path")

    # Convert single CIF command
    convert_parser = subparsers.add_parser("convert", help="Convert single CIF file to HTML")
    convert_parser.add_argument("cif_file", help="Input CIF file path")
    convert_parser.add_argument("--output", "-o", help="Output HTML file path")

    # Create gallery command
    gallery_parser = subparsers.add_parser(
        "gallery", help="Create gallery from directory of CIF files"
    )
    gallery_parser.add_argument("directory", help="Directory containing CIF files")
    gallery_parser.add_argument("--output", "-o", help="Output directory for gallery")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    visualizer = UniversalCIFVisualizer()

    try:
        if args.command == "create-viewer":
            visualizer.create_universal_viewer(args.output)

        elif args.command == "convert":
            visualizer.convert_cif_to_html(args.cif_file, args.output)

        elif args.command == "gallery":
            visualizer.create_gallery(args.directory, args.output)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
