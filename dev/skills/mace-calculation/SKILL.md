---
name: mace-calculation
description: >
  Calculate energies, forces, and relax crystal structures using MACE machine
  learning interatomic potentials. Use when: (1) calculating formation energy
  of a structure, (2) relaxing/optimizing crystal structures, (3) checking
  if a predicted structure is reasonable, (4) computing forces on atoms,
  (5) preparing structures for further DFT calculations.
---

# MACE Calculations

Calculate energies and relax structures using MACE (Multi-Atomic Cluster Expansion)
machine learning potentials.

## Quick Usage

**Calculate formation energy:**
```bash
python scripts/formation_energy.py structure.json
```

**Relax a structure:**
```bash
python scripts/relax.py structure.json --output relaxed.json
```

## Input Format

Structures can be provided as JSON:
```json
{
  "numbers": [56, 22, 8, 8, 8],
  "positions": [[0.0, 0.0, 0.0], [2.0, 2.0, 2.0], ...],
  "cell": [[4.0, 0, 0], [0, 4.0, 0], [0, 0, 4.0]],
  "pbc": [true, true, true]
}
```

Or as a CIF file:
```bash
python scripts/formation_energy.py structure.cif
```

## Available Calculations

### Formation Energy
Calculate the formation energy (energy relative to elemental references):
```bash
python scripts/formation_energy.py structure.json
```

Output:
```json
{
  "formula": "BaTiO3",
  "total_energy": -45.23,
  "formation_energy": -3.15,
  "energy_per_atom": -9.046,
  "units": "eV"
}
```

### Structure Relaxation
Optimize atomic positions and cell parameters:
```bash
python scripts/relax.py structure.json --output relaxed.json
```

Options:
- `--fmax 0.01`: Force convergence threshold (eV/Å)
- `--steps 500`: Maximum optimization steps
- `--cell`: Also relax cell parameters

### Forces
Calculate forces on each atom:
```bash
python scripts/forces.py structure.json
```

## MACE Models

Uses the MACE-MP-0 foundation model by default (trained on Materials Project).

Custom model:
```bash
python scripts/formation_energy.py structure.json --model /path/to/model.pt
```

## Workflow Integration

**After Chemeleon prediction:**
```bash
# 1. Predict structure
python ../chemeleon-prediction/scripts/predict_csp.py "BaTiO3" --output predicted.json

# 2. Calculate energy
python scripts/formation_energy.py predicted.json

# 3. Relax structure
python scripts/relax.py predicted.json --output relaxed.json
```

**Check thermodynamic stability** (use $phase-diagram):
```bash
# After getting formation energy, check hull distance
python ../phase-diagram/scripts/hull_distance.py relaxed.json
```

## Provenance

When reporting results, always include:
- Input structure source (predicted, experimental, etc.)
- MACE model version
- Energy values with units (eV)
- Whether structure was relaxed
- Convergence criteria used
