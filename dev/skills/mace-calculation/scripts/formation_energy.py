#!/usr/bin/env python3
"""
MACE Formation Energy Calculator

Calculates formation energy of a crystal structure using MACE
machine learning interatomic potentials.

Usage:
    python formation_energy.py structure.json
    python formation_energy.py structure.cif
    python formation_energy.py structure.json --model medium --no-gpu
"""

import argparse
import json
import sys
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


def load_structure(path: str) -> dict:
    """Load structure from JSON or CIF file."""
    if path.endswith(".json"):
        with open(path) as f:
            return json.load(f)
    elif path.endswith(".cif"):
        try:
            from ase.io import read

            atoms = read(path, format="cif")
            return {
                "numbers": atoms.numbers.tolist(),
                "positions": atoms.positions.tolist(),
                "cell": atoms.cell.tolist(),
                "pbc": atoms.pbc.tolist(),
            }
        except ImportError:
            print(
                json.dumps(
                    {"error": "ASE required to read CIF files", "hint": "pip install ase"}, indent=2
                )
            )
            sys.exit(1)
    else:
        # Try to parse as JSON from stdin or raw text
        try:
            return json.loads(path)
        except json.JSONDecodeError:
            print(
                json.dumps(
                    {
                        "error": f"Unknown file format: {path}",
                        "hint": "Supported formats: .json, .cif",
                    },
                    indent=2,
                )
            )
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Calculate formation energy using MACE")
    parser.add_argument("structure", type=str, help="Structure file (JSON or CIF)")
    parser.add_argument(
        "--model",
        type=str,
        default="medium",
        choices=["small", "medium", "large"],
        help="MACE model size (default: medium)",
    )
    parser.add_argument("--no-gpu", action="store_true", help="Force CPU computation")
    parser.add_argument("--output", "-o", type=str, help="Output file (default: stdout)")
    parser.add_argument("--compact", action="store_true", help="Output compact JSON")

    args = parser.parse_args()

    try:
        # Load structure
        structure = load_structure(args.structure)

        # Import MACE calculator
        from crystalyse.tools.mace.energy import MACECalculator as MACECalc

        # Initialize calculator
        device = "cpu" if args.no_gpu else "auto"
        calc = MACECalc(model_type="mace_mp", size=args.model, device=device)

        # Calculate energy
        result = calc.calculate_formation_energy_sync(structure)

        # Format output
        output = {
            "success": result.success,
            "formula": result.formula,
            "formation_energy": result.formation_energy,
            "energy_per_atom": result.energy_per_atom,
            "total_energy": result.total_energy,
            "unit": result.unit,
            "method": result.method,
            "model": f"mace_mp_{args.model}",
        }

        if result.error:
            output["error"] = result.error

        # Write output
        if args.compact:
            json_str = json.dumps(output)
        else:
            json_str = json.dumps(output, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(json_str)
            print(f"Results written to {args.output}")
        else:
            print(json_str)

        sys.exit(0 if result.success else 1)

    except ImportError as e:
        print(
            json.dumps(
                {
                    "error": f"Missing required package: {e}",
                    "hint": "Install with: pip install mace-torch torch ase",
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
