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

### Model Selection

| Model | Speed | Accuracy | Use When |
|-------|-------|----------|----------|
| `small` | Fast (3x) | Lower | Quick screening of 100+ candidates |
| `medium` | Balanced | Good | Default for most work |
| `large` | Slow | Best | Final calculations, publications |

**Rule of thumb**: Use `small` for screening, `medium` for exploration, `large` for final numbers.

```bash
python scripts/formation_energy.py structure.json --model-size medium
```

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

## Critical: float32 vs float64

| dtype | Speed | Use Case |
|-------|-------|----------|
| `float32` | ~2x faster | Molecular dynamics, screening |
| `float64` | Accurate | Geometry optimization, final energies |

**Default**: Scripts use `float32`. For geometry optimization, add `--dtype float64`.

## Gotchas

**Stress + torch.compile incompatible**: When `--compile` is enabled, stress computation is silently disabled. If you need stress tensors, don't compile.

**Formation energy calculation**: Uses model's internal atomic reference energies (`atomic_energies_fn`), NOT external databases. This is correct - different models have different references.

**Committee models for uncertainty**: Load multiple models with wildcard patterns:
```bash
python scripts/formation_energy.py structure.json --model "mace_*.model"
# Returns energy_var, forces_comm for uncertainty estimation
```

**Foundation model sizes**:
- `small`: Fast, less accurate
- `medium`: Balanced (default)
- `large`: Most accurate, slowest

## When to Override Defaults

**Use `--no-gpu` if**:
- GPU gives OOM errors
- Testing on different hardware
- Reproducibility with CPU reference

**Use larger `--fmax` (e.g., 0.05) if**:
- Quick screening (not final structure)
- Structure far from minimum (pre-relax)

**Use smaller `--fmax` (e.g., 0.001) if**:
- Final production calculation
- Phonon/vibrational analysis
- High-precision property extraction

## Limitations

**MACE CANNOT compute:**
- Band gaps (gives total energies, not electronic structure)
- Phonons (requires DFPT, not classical potential)
- Carrier mobility
- Optical properties
- Magnetic ordering

**If asked for these:** Query databases, cite literature, or state "cannot compute without DFT."

## Provenance

When reporting results, always include:
- Input structure source (predicted, experimental, etc.)
- MACE model version and size
- Energy values with units (eV)
- Whether structure was relaxed
- Convergence criteria used (fmax, steps)
- **dtype used** (float32 or float64)
- **If stress needed**: Note whether compile was disabled

## For Workers

If you're a worker subagent executing this skill:
1. Follow the task instructions from the lead agent
2. Write full results (energies, structures) to the artifact path if specified
3. Return a summary with: formation energy, convergence status, any warnings
4. Report any errors or gaps clearly (e.g., "failed to converge after 500 steps")
