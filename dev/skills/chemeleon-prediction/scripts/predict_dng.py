#!/usr/bin/env python3
"""
Chemeleon De Novo Generation (DNG)

Generates novel crystal structures within a chemical system using
the Chemeleon DNG model.

Usage:
    python predict_dng.py "Ba-Ti-O"
    python predict_dng.py "Li-Fe-P-O" --num-structures 5
    python predict_dng.py "Na-Cl" --max-atoms 8 --output candidates.json
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
        description="Generate novel crystal structures using Chemeleon DNG model"
    )
    parser.add_argument(
        "element_set",
        type=str,
        help="Chemical system as hyphen-separated elements (e.g., 'Ba-Ti-O', 'Li-Fe-P-O')"
    )
    parser.add_argument(
        "--num-structures", "-n",
        type=int,
        default=1,
        help="Number of structures to generate (default: 1)"
    )
    parser.add_argument(
        "--max-atoms",
        type=int,
        default=20,
        help="Maximum atoms per structure (default: 20)"
    )
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=1.0,
        help="Sampling temperature (default: 1.0)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Force CPU computation"
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        help="Path to specific checkpoint file"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON"
    )

    args = parser.parse_args()

    # Parse element set
    elements = [e.strip() for e in args.element_set.split("-")]
    if len(elements) < 2:
        print(json.dumps({
            "error": "Element set must contain at least 2 elements",
            "hint": "Use format like 'Ba-Ti-O' or 'Li-Fe-P-O'"
        }, indent=2))
        sys.exit(1)

    try:
        # Import after argument parsing
        from crystalyse.tools.chemeleon import ChemeleonPredictor

        # Initialize predictor
        predictor = ChemeleonPredictor()

        # Note: DNG mode requires different handling - for now we use CSP
        # with element combinations. Full DNG support coming in future version.
        print(json.dumps({
            "warning": "DNG mode is experimental. Using CSP mode for element combinations.",
            "element_set": elements,
            "num_structures": args.num_structures,
            "hint": "For full DNG support, use the MCP server directly"
        }, indent=2))

        # For now, return a placeholder
        output = {
            "element_set": elements,
            "success": False,
            "error": "DNG mode not yet implemented in CLI. Use MCP server or Python API.",
            "alternative": f"Try: python predict_csp.py '<formula>' with a specific composition"
        }

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

        sys.exit(1)

    except ImportError as e:
        print(json.dumps({
            "error": f"Missing required package: {e}",
            "hint": "Install with: pip install chemeleon-dng torch"
        }, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
