#!/usr/bin/env python3
"""
Phase Diagram Hull Distance Calculator

Calculates energy above hull for a structure given its energy and
a database of competing phases.

Usage:
    python hull_distance.py structure.json --energy -5.2
    python hull_distance.py structure.json --energy -5.2 --entries competing_phases.json
"""

import argparse
import json
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate energy above convex hull"
    )
    parser.add_argument(
        "structure",
        type=str,
        help="Structure file (JSON, CIF, or POSCAR)"
    )
    parser.add_argument(
        "--energy", "-e",
        type=float,
        required=True,
        help="Total energy of the structure (eV)"
    )
    parser.add_argument(
        "--entries",
        type=str,
        help="JSON file with competing phase entries (optional, uses MP data if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    try:
        from pymatgen.core import Structure
        from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
        from pymatgen.entries.computed_entries import ComputedEntry

        # Load structure
        struct = Structure.from_file(args.structure)
        comp = struct.composition

        # Create entry for the input structure
        my_entry = ComputedEntry(comp, args.energy)

        # Load or create competing entries
        if args.entries:
            with open(args.entries) as f:
                entries_data = json.load(f)
            entries = [
                PDEntry(e["composition"], e["energy"])
                for e in entries_data
            ]
        else:
            # Fallback: create elemental references only
            # In practice, you'd load from Materials Project
            print("Warning: No competing phases provided. Using elemental references only.",
                  file=sys.stderr)
            entries = []
            for el in comp.elements:
                # Assume 0 eV for elemental reference (placeholder)
                entries.append(PDEntry(el.symbol, 0.0))

        # Add our entry
        entries.append(my_entry)

        # Build phase diagram
        try:
            pd = PhaseDiagram(entries)
        except Exception as e:
            print(json.dumps({
                "error": f"Could not build phase diagram: {e}",
                "hint": "Ensure competing phases cover the composition space"
            }, indent=2))
            sys.exit(1)

        # Calculate hull distance
        decomp, e_above_hull = pd.get_decomp_and_e_above_hull(my_entry)

        # Interpret stability
        if e_above_hull == 0:
            stability = "on_hull"
            interpretation = "Thermodynamically stable"
        elif e_above_hull < 0.025:
            stability = "near_hull"
            interpretation = "Likely synthesizable (metastable)"
        elif e_above_hull < 0.1:
            stability = "metastable"
            interpretation = "Metastable, may exist under specific conditions"
        else:
            stability = "unstable"
            interpretation = "Thermodynamically unstable"

        # Format decomposition products
        decomp_products = [
            {"formula": entry.composition.reduced_formula, "fraction": frac}
            for entry, frac in decomp.items()
        ]

        output = {
            "formula": comp.reduced_formula,
            "energy_above_hull": round(e_above_hull, 6),
            "energy_above_hull_unit": "eV/atom",
            "stability": stability,
            "interpretation": interpretation,
            "decomposition_products": decomp_products,
            "input_energy": args.energy,
            "num_atoms": comp.num_atoms,
        }

        json_str = json.dumps(output, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(json_str)
            print(f"Results written to {args.output}")
        else:
            print(json_str)

    except ImportError as e:
        print(json.dumps({
            "error": f"Missing required package: {e}",
            "hint": "Install with: pip install pymatgen"
        }, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
