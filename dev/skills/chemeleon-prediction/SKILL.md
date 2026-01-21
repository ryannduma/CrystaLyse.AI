---
name: chemeleon-prediction
description: >
  Predict crystal structures using Chemeleon machine learning models. Use when:
  (1) user provides a composition and wants to find its crystal structure,
  (2) de novo generation of new materials with desired properties,
  (3) exploring the structural space of a chemical system,
  (4) generating CIF files for DFT calculations or further analysis.
---

# Chemeleon Structure Prediction

Predict crystal structures using the Chemeleon CSP (Crystal Structure Prediction)
and DNG (De Novo Generation) models.

## Quick Usage

**Predict structure for a composition:**
```bash
python scripts/predict_csp.py "BaTiO3"
```

**Generate new materials in a chemical system:**
```bash
python scripts/predict_dng.py "Ba-Ti-O" --num-structures 5
```

## Modes

### CSP (Crystal Structure Prediction)
Given a composition, predict the most likely crystal structure(s).
- Input: Chemical formula (e.g., "BaTiO3", "LiFePO4")
- Output: Predicted structures with confidence scores

### DNG (De Novo Generation)
Generate new materials within a chemical system.
- Input: Element set (e.g., "Ba-Ti-O", "Li-Fe-P-O")
- Output: Novel compositions and structures

## Output Format

Both modes return structures as JSON with:
```json
{
  "formula": "BaTiO3",
  "confidence": 0.85,
  "structure": {
    "numbers": [56, 22, 8, 8, 8],
    "positions": [[0.0, 0.0, 0.0], ...],
    "cell": [[4.0, 0, 0], [0, 4.0, 0], [0, 0, 4.0]],
    "symbols": ["Ba", "Ti", "O", "O", "O"],
    "volume": 64.0
  }
}
```

## Workflow Integration

**Typical workflow with other skills:**

1. **Validate composition first** (use $smact-validation)
   ```bash
   python ../smact-validation/scripts/validate.py "BaTiO3"
   ```

2. **Predict structure**
   ```bash
   python scripts/predict_csp.py "BaTiO3"
   ```

3. **Calculate energy** (use $mace-calculation)
   ```bash
   python ../mace-calculation/scripts/formation_energy.py structure.json
   ```

4. **Visualize** (use $visualization)
   ```bash
   python ../visualization/scripts/structure_3d.py structure.json
   ```

## Model Checkpoints

Chemeleon models auto-download on first use (~600 MB total).
- Stored in: `~/.cache/crystalyse/chemeleon_checkpoints/`
- CSP model: `chemeleon_csp_alex_mp_20_v0.0.2.ckpt` (141 MB)
- DNG model: `chemeleon_dng_alex_mp_20_v0.0.2.ckpt` (161 MB)

Custom checkpoint directory:
```bash
export CHEMELEON_CHECKPOINT_DIR=/path/to/checkpoints
```

## Options

**CSP options:**
```bash
python scripts/predict_csp.py "BaTiO3" \
    --num-structures 3 \
    --temperature 1.0 \
    --output structures.json
```

**DNG options:**
```bash
python scripts/predict_dng.py "Ba-Ti-O" \
    --num-structures 10 \
    --max-atoms 20 \
    --output candidates.json
```

## Provenance

When reporting results, always include:
- Input composition or element set
- Model used (CSP vs DNG)
- Confidence score for each structure
- Checkpoint version used
