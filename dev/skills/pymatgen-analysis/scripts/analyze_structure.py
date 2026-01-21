#!/usr/bin/env python3
"""
Structure Analysis Tool

Analyzes a crystal structure: symmetry, composition, oxidation states.

Usage:
    python analyze_structure.py structure.cif
    python analyze_structure.py POSCAR --guess-oxi
    python analyze_structure.py structure.json --merge-tol 0.01
"""

import argparse
import json
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


def main():
    parser = argparse.ArgumentParser(description="Analyze crystal structure properties")
    parser.add_argument("structure", type=str, help="Structure file (CIF, POSCAR, JSON, etc.)")
    parser.add_argument(
        "--merge-tol",
        type=float,
        default=None,
        help="Merge tolerance for duplicate atoms (use 0.01 for DFT CIFs)",
    )
    parser.add_argument("--guess-oxi", action="store_true", help="Guess oxidation states")
    parser.add_argument("--primitive", action="store_true", help="Convert to primitive cell")
    parser.add_argument("--output", "-o", type=str, help="Output file (default: stdout)")

    args = parser.parse_args()

    try:
        from pymatgen.core import Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        # Load structure
        load_kwargs = {}
        if args.merge_tol is not None:
            load_kwargs["merge_tol"] = args.merge_tol

        struct = Structure.from_file(args.structure, **load_kwargs)

        # Convert to primitive if requested
        if args.primitive:
            sga = SpacegroupAnalyzer(struct)
            struct = sga.get_primitive_standard_structure()

        # Basic info
        comp = struct.composition

        # Symmetry analysis
        sga = SpacegroupAnalyzer(struct)

        output = {
            "formula": comp.reduced_formula,
            "num_atoms": struct.num_sites,
            "volume": round(struct.volume, 4),
            "density": round(struct.density, 4),
            "lattice": {
                "a": round(struct.lattice.a, 4),
                "b": round(struct.lattice.b, 4),
                "c": round(struct.lattice.c, 4),
                "alpha": round(struct.lattice.alpha, 2),
                "beta": round(struct.lattice.beta, 2),
                "gamma": round(struct.lattice.gamma, 2),
            },
            "space_group": {
                "symbol": sga.get_space_group_symbol(),
                "number": sga.get_space_group_number(),
                "crystal_system": sga.get_crystal_system(),
                "point_group": sga.get_point_group_symbol(),
            },
            "elements": [str(el) for el in comp.elements],
            "element_fractions": {
                str(el): round(frac, 4) for el, frac in comp.fractional_composition.items()
            },
        }

        # Oxidation state guessing
        if args.guess_oxi:
            oxi_guesses = comp.oxi_state_guesses(all_oxi_states=False)
            if oxi_guesses:
                output["oxidation_states"] = {str(el): oxi for el, oxi in oxi_guesses[0].items()}
                output["oxi_state_confidence"] = (
                    "high" if len(oxi_guesses) == 1 else "multiple_possibilities"
                )
                output["num_oxi_possibilities"] = len(oxi_guesses)
            else:
                output["oxidation_states"] = None
                output["oxi_state_confidence"] = "none"
                output["oxi_state_note"] = "No valid charge-balanced oxidation states found"

        # Check for potential issues
        issues = []
        if struct.is_ordered is False:
            issues.append("Structure has disordered sites")
        if struct.volume < 10:
            issues.append("Very small unit cell volume")
        if any(struct.lattice.angles[i] < 30 or struct.lattice.angles[i] > 150 for i in range(3)):
            issues.append("Unusual lattice angles")

        if issues:
            output["warnings"] = issues

        json_str = json.dumps(output, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(json_str)
            print(f"Results written to {args.output}")
        else:
            print(json_str)

    except ImportError as e:
        print(
            json.dumps(
                {
                    "error": f"Missing required package: {e}",
                    "hint": "Install with: pip install pymatgen",
                },
                indent=2,
            )
        )
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
