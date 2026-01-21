---
name: smact-validation
description: >
  Validate chemical compositions for charge neutrality, electronegativity
  balance, and synthesizability using SMACT rules. Use when: (1) user provides
  a formula to analyze, (2) before structure prediction to filter candidates,
  (3) screening candidate compositions for stability, (4) checking oxidation
  states for a compound, (5) evaluating if a composition is chemically plausible.
---

# SMACT Validation

Validate chemical compositions using the SMACT library (Semiconducting Materials
from Analogy and Chemical Theory).

## Quick Usage

```bash
python scripts/validate.py "LiFePO4"
```

Output: JSON with validity, oxidation states, and reasoning.

## What It Checks

1. **Charge neutrality**: Sum of oxidation states = 0
2. **Electronegativity**: Anion more electronegative than cation
3. **Pauling rules**: Common oxidation states for each element
4. **Element validity**: All elements exist and have known properties

## Workflow

1. Parse the formula into elements and stoichiometry
2. Look up common oxidation states for each element
3. Find combinations where charges sum to zero
4. Verify electronegativity ordering (cations < anions)
5. Return all valid oxidation state assignments

## Example Output

```json
{
  "formula": "LiFePO4",
  "valid": true,
  "charge_balanced": true,
  "electronegativity_ok": true,
  "oxidation_states": [
    {"combination": ["Li+1", "Fe+2", "P+5", "O-2"], "charge_sum": 0}
  ],
  "reasoning": "Charge balanced: 1(+1) + 1(+2) + 1(+5) + 4(-2) = 0",
  "smact_version": "2.7.1"
}
```

## Batch Validation

For multiple formulas:

```bash
python scripts/validate.py "LiFePO4" "NaCl" "CaTiO3" "InvalidXYZ"
```

Or from a file:

```bash
python scripts/validate_batch.py formulas.txt --output results.json
```

## Common Use Cases

**Before structure prediction**:
```bash
# Validate before calling Chemeleon CSP
python scripts/validate.py "Ba2YCu3O7"
# If valid, proceed with structure prediction
```

**Screening compositions**:
```bash
# Screen a list of perovskite candidates
python scripts/validate_batch.py perovskites.txt --filter valid
```

**Checking specific oxidation states**:
```bash
# Force specific oxidation states
python scripts/validate.py "Fe2O3" --oxidation-states "Fe:+3,O:-2"
```

## Provenance Requirements

When reporting results, always include:
- Input formula (exactly as provided)
- SMACT version used (in output JSON)
- Any assumptions about oxidation states
- Whether the result is valid or invalid with reasoning
