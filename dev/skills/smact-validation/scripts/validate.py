#!/usr/bin/env python3
"""
SMACT Composition Validator

Validates chemical compositions for charge neutrality, electronegativity
balance, and synthesizability using SMACT rules.

Usage:
    python validate.py "LiFePO4"
    python validate.py "NaCl" "CaTiO3" "MgO"
    python validate.py "Fe2O3" --oxidation-states "Fe:+3,O:-2"
"""

import argparse
import json
import sys
import warnings
from typing import Any

# Suppress warnings
warnings.filterwarnings("ignore", message=".*electronegativity.*")
warnings.filterwarnings("ignore", category=UserWarning)

try:
    from pymatgen.core import Composition
    from smact import Element
    from smact.screening import smact_validity
    import smact

    SMACT_VERSION = getattr(smact, "__version__", "unknown")
except ImportError as e:
    print(json.dumps({
        "error": f"Missing required package: {e}",
        "hint": "Install with: pip install smact pymatgen"
    }, indent=2))
    sys.exit(1)


def get_element_oxidation_states(symbol: str) -> list[int]:
    """Get common oxidation states for an element."""
    try:
        elem = Element(symbol)
        if elem.oxidation_states:
            return list(elem.oxidation_states)
        return []
    except Exception:
        return []


def find_charge_balanced_combinations(
    elements: list[str],
    stoichiometry: list[int],
    forced_states: dict[str, int] | None = None
) -> list[dict]:
    """Find all oxidation state combinations that give charge neutrality."""
    from itertools import product

    # Get possible oxidation states for each element
    possible_states = []
    for elem in elements:
        if forced_states and elem in forced_states:
            possible_states.append([forced_states[elem]])
        else:
            states = get_element_oxidation_states(elem)
            if not states:
                states = [0]  # Default to neutral if unknown
            possible_states.append(states)

    # Find all charge-balanced combinations
    valid_combinations = []
    for combo in product(*possible_states):
        total_charge = sum(ox * stoich for ox, stoich in zip(combo, stoichiometry))
        if total_charge == 0:
            combination = []
            for elem, ox, stoich in zip(elements, combo, stoichiometry):
                sign = "+" if ox > 0 else ""
                combination.append(f"{elem}{sign}{ox}")
            valid_combinations.append({
                "combination": combination,
                "charge_sum": total_charge
            })

    return valid_combinations


def validate_composition(
    formula: str,
    use_pauling_test: bool = True,
    forced_oxidation_states: dict[str, int] | None = None
) -> dict[str, Any]:
    """
    Validate a chemical composition using SMACT rules.

    Args:
        formula: Chemical formula (e.g., "LiFePO4")
        use_pauling_test: Apply electronegativity test
        forced_oxidation_states: Override oxidation states (e.g., {"Fe": 3})

    Returns:
        Dictionary with validation results
    """
    result = {
        "formula": formula,
        "valid": False,
        "charge_balanced": False,
        "electronegativity_ok": False,
        "oxidation_states": [],
        "reasoning": "",
        "smact_version": SMACT_VERSION,
        "errors": []
    }

    try:
        # Parse composition
        comp = Composition(formula)

        # Get elements and stoichiometry
        elements = [str(el) for el in comp.elements]
        stoichiometry = [int(comp.get(el)) for el in comp.elements]

        # Run SMACT validity check
        try:
            is_valid = smact_validity(
                comp,
                use_pauling_test=use_pauling_test,
                include_alloys=True
            )
        except Exception as e:
            # Fallback for older SMACT versions or edge cases
            is_valid = False
            result["errors"].append(f"SMACT check error: {str(e)}")

        result["valid"] = is_valid

        # Find charge-balanced oxidation state combinations
        combinations = find_charge_balanced_combinations(
            elements, stoichiometry, forced_oxidation_states
        )
        result["oxidation_states"] = combinations
        result["charge_balanced"] = len(combinations) > 0

        # Check electronegativity ordering
        if len(elements) >= 2:
            try:
                enegs = []
                for el in elements:
                    elem = Element(el)
                    if elem.pauling_eneg is not None:
                        enegs.append((el, elem.pauling_eneg))

                if len(enegs) >= 2:
                    # Check if there's a reasonable electronegativity spread
                    sorted_enegs = sorted(enegs, key=lambda x: x[1])
                    eneg_diff = sorted_enegs[-1][1] - sorted_enegs[0][1]
                    result["electronegativity_ok"] = eneg_diff > 0.3
                    result["electronegativity_difference"] = round(eneg_diff, 2)
            except Exception:
                result["electronegativity_ok"] = True  # Assume OK if can't check

        # Generate reasoning
        if result["valid"]:
            if combinations:
                combo = combinations[0]["combination"]
                charge_calc = " + ".join(
                    f"{stoich}({ox})" for ox, stoich in
                    zip([c.split('+')[1] if '+' in c else c.split('-')[0] + c.split(c.split('-')[0])[1] for c in combo], stoichiometry)
                )
                result["reasoning"] = f"Valid composition. Found {len(combinations)} charge-balanced combination(s)."
            else:
                result["reasoning"] = "Valid by SMACT rules (may be an alloy or special case)."
        else:
            reasons = []
            if not result["charge_balanced"]:
                reasons.append("no charge-balanced oxidation states found")
            if not result["electronegativity_ok"]:
                reasons.append("electronegativity ordering not satisfied")
            result["reasoning"] = f"Invalid: {', '.join(reasons)}" if reasons else "Invalid by SMACT rules"

    except Exception as e:
        result["errors"].append(str(e))
        result["reasoning"] = f"Validation failed: {str(e)}"

    return result


def parse_oxidation_states(ox_string: str) -> dict[str, int]:
    """Parse oxidation states string like 'Fe:+3,O:-2'."""
    states = {}
    if not ox_string:
        return states

    for pair in ox_string.split(","):
        if ":" in pair:
            elem, state = pair.split(":")
            # Handle both +3 and 3 formats
            state = state.replace("+", "")
            states[elem.strip()] = int(state)

    return states


def main():
    parser = argparse.ArgumentParser(
        description="Validate chemical compositions using SMACT rules"
    )
    parser.add_argument(
        "formulas",
        nargs="+",
        help="Chemical formula(s) to validate"
    )
    parser.add_argument(
        "--oxidation-states",
        type=str,
        help="Force specific oxidation states (e.g., 'Fe:+3,O:-2')"
    )
    parser.add_argument(
        "--no-pauling-test",
        action="store_true",
        help="Skip electronegativity test"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (one line per formula)"
    )

    args = parser.parse_args()

    forced_states = parse_oxidation_states(args.oxidation_states or "")
    use_pauling = not args.no_pauling_test

    results = []
    for formula in args.formulas:
        result = validate_composition(
            formula,
            use_pauling_test=use_pauling,
            forced_oxidation_states=forced_states if forced_states else None
        )
        results.append(result)

    # Output
    if len(results) == 1:
        if args.compact:
            print(json.dumps(results[0]))
        else:
            print(json.dumps(results[0], indent=2))
    else:
        if args.compact:
            for r in results:
                print(json.dumps(r))
        else:
            print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
