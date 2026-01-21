#!/usr/bin/env python3
"""
MACE Structure Relaxation

Relaxes a crystal structure to a local energy minimum using MACE
machine learning interatomic potentials.

Usage:
    python relax.py structure.json
    python relax.py structure.json --output relaxed.json
    python relax.py structure.cif --fmax 0.01 --steps 500
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
    parser = argparse.ArgumentParser(description="Relax structure using MACE")
    parser.add_argument("structure", type=str, help="Structure file (JSON or CIF)")
    parser.add_argument(
        "--fmax",
        type=float,
        default=0.01,
        help="Force convergence threshold in eV/Å (default: 0.01)",
    )
    parser.add_argument(
        "--steps", type=int, default=500, help="Maximum optimization steps (default: 500)"
    )
    parser.add_argument(
        "--optimizer",
        type=str,
        default="BFGS",
        choices=["BFGS", "FIRE", "LBFGS"],
        help="Optimization algorithm (default: BFGS)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="medium",
        choices=["small", "medium", "large"],
        help="MACE model size (default: medium)",
    )
    parser.add_argument("--no-gpu", action="store_true", help="Force CPU computation")
    parser.add_argument(
        "--output", "-o", type=str, help="Output file for relaxed structure (default: stdout)"
    )
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

        # Run relaxation
        result = calc.relax_structure_sync(
            structure, fmax=args.fmax, steps=args.steps, optimizer=args.optimizer
        )

        # Format output
        output = {
            "success": result.success,
            "converged": result.converged,
            "initial_energy": result.initial_energy,
            "final_energy": result.final_energy,
            "energy_change": result.energy_change,
            "max_displacement": result.max_displacement,
            "n_steps": result.n_steps,
            "fmax_threshold": args.fmax,
            "optimizer": args.optimizer,
            "model": f"mace_mp_{args.model}",
        }

        if result.relaxed_structure:
            output["relaxed_structure"] = result.relaxed_structure

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
            print(f"Relaxed structure written to {args.output}")
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
