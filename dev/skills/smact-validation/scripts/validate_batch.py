#!/usr/bin/env python3
"""
SMACT Batch Composition Validator

Validates multiple chemical compositions from a file.

Usage:
    python validate_batch.py formulas.txt
    python validate_batch.py formulas.txt --output results.json
    python validate_batch.py formulas.txt --filter valid
"""

import argparse
import json
import sys
from pathlib import Path

# Import from sibling module
from validate import validate_composition


def main():
    parser = argparse.ArgumentParser(
        description="Batch validate chemical compositions"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="File with formulas (one per line)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--filter",
        choices=["valid", "invalid", "all"],
        default="all",
        help="Filter results by validity"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary statistics"
    )

    args = parser.parse_args()

    # Read formulas
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    formulas = []
    with open(input_path) as f:
        for line in f:
            formula = line.strip()
            if formula and not formula.startswith("#"):
                formulas.append(formula)

    if not formulas:
        print("No formulas found in input file", file=sys.stderr)
        sys.exit(1)

    # Validate all
    results = []
    valid_count = 0
    invalid_count = 0

    for formula in formulas:
        result = validate_composition(formula)
        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1

        # Apply filter
        if args.filter == "all":
            results.append(result)
        elif args.filter == "valid" and result["valid"]:
            results.append(result)
        elif args.filter == "invalid" and not result["valid"]:
            results.append(result)

    # Output
    output_data = {
        "total": len(formulas),
        "valid": valid_count,
        "invalid": invalid_count,
        "results": results
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results written to {args.output}")
    else:
        print(json.dumps(output_data, indent=2))

    # Summary
    if args.summary:
        print(f"\n--- Summary ---", file=sys.stderr)
        print(f"Total:   {len(formulas)}", file=sys.stderr)
        print(f"Valid:   {valid_count} ({100*valid_count/len(formulas):.1f}%)", file=sys.stderr)
        print(f"Invalid: {invalid_count} ({100*invalid_count/len(formulas):.1f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
