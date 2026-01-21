#!/usr/bin/env python3
"""
Chemeleon Crystal Structure Prediction (CSP)

Predicts crystal structures for a given chemical composition using
the Chemeleon CSP model.

Usage:
    python predict_csp.py "BaTiO3"
    python predict_csp.py "LiFePO4" --num-structures 3
    python predict_csp.py "NaCl" --output structure.json --no-gpu
"""

import argparse
import json
import sys
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


def main():
    parser = argparse.ArgumentParser(
        description="Predict crystal structure using Chemeleon CSP model"
    )
    parser.add_argument("formula", type=str, help="Chemical formula (e.g., 'BaTiO3', 'LiFePO4')")
    parser.add_argument(
        "--num-structures",
        "-n",
        type=int,
        default=1,
        help="Number of structures to generate (default: 1)",
    )
    parser.add_argument(
        "--temperature", "-t", type=float, default=1.0, help="Sampling temperature (default: 1.0)"
    )
    parser.add_argument("--output", "-o", type=str, help="Output file (default: stdout)")
    parser.add_argument("--no-gpu", action="store_true", help="Force CPU computation")
    parser.add_argument("--checkpoint", type=str, help="Path to specific checkpoint file")
    parser.add_argument("--compact", action="store_true", help="Output compact JSON")

    args = parser.parse_args()

    try:
        # Import after argument parsing to avoid slow imports for --help
        from crystalyse.tools.chemeleon import ChemeleonPredictor

        # Initialize predictor
        predictor = ChemeleonPredictor()

        # Run prediction
        result = predictor.predict_structure_sync(
            formula=args.formula,
            num_samples=args.num_structures,
            checkpoint_path=args.checkpoint,
            prefer_gpu=not args.no_gpu,
        )

        # Format output
        if result.success:
            output = {
                "formula": result.formula,
                "success": True,
                "num_structures": len(result.predicted_structures),
                "computation_time": result.computation_time,
                "method": result.method,
                "checkpoint": result.checkpoint_used,
                "structures": [
                    {
                        "formula": s.formula,
                        "confidence": s.confidence,
                        "volume": s.volume,
                        "structure": {
                            "numbers": s.numbers,
                            "positions": s.positions,
                            "cell": s.cell,
                            "symbols": s.symbols,
                        },
                    }
                    for s in result.predicted_structures
                ],
            }
        else:
            output = {"formula": result.formula, "success": False, "error": result.error}

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

        # Exit with appropriate code
        sys.exit(0 if result.success else 1)

    except ImportError as e:
        print(
            json.dumps(
                {
                    "error": f"Missing required package: {e}",
                    "hint": "Install with: pip install chemeleon-dng torch",
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
