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

## Critical Gotchas

**Heavy elements silently broken**: Atoms with Z > 101 (Mendelevium) are **silently converted to Z=0**. If working with actinides beyond Md, verify output CIF files manually.

**Checkpoint task mismatch crashes**: Using a CSP checkpoint with `--task dng` (or vice versa) raises an assertion error. The checkpoint's task must match the requested task.

**Batch size defaults to num_samples**: For large generations, explicitly set `--batch-size` smaller to avoid OOM:
```bash
python scripts/predict_csp.py "BaTiO3" --num-structures 100 --batch-size 20
```

**JSON conversion may fail for some structures**: Check the warning count - some CIF files may not convert to pymatgen Structure objects.

## When to Use CSP vs DNG

| You have... | Use | Why |
|-------------|-----|-----|
| Specific formula (BaTiO3) | CSP | Predicts structures FOR that composition |
| Element set (Ba-Ti-O) | DNG | Explores entire chemical space |
| Novel material discovery | DNG | No composition constraint |
| Known compound structure | CSP | More targeted prediction |

**CSP requires**: Exact formula → atomic numbers list
**DNG ignores**: atom_types parameter (only uses num_atoms distribution)

## Interpreting Confidence Scores

| Score | Interpretation | Action |
|-------|----------------|--------|
| > 0.9 | High confidence | Trust prediction |
| 0.7 - 0.9 | Moderate | Validate against known phases |
| 0.5 - 0.7 | Low | Multiple polymorphs likely, check all |
| < 0.5 | Very low | Structure may be unreliable |

**If confidence < 0.7**: Generate multiple structures (`--num-structures 5`) and compare.

## Limitations

**Chemeleon CANNOT compute:**

- Band gaps or electronic properties
- Formation energies (use MACE after prediction)
- Thermodynamic stability
- Mechanical properties
- Defect formation energies

**Chemeleon only predicts structure geometry.** For properties, use other skills after prediction.

## Provenance

When reporting results, always include:

- Input composition or element set
- Model used (CSP vs DNG)
- Confidence score for each structure
- Checkpoint version used
- **If Z > 101 elements present**: Note potential data corruption

## For Workers

If you're a worker subagent executing this skill:

1. Follow the task instructions from the lead agent
2. Write predicted structures (CIF/JSON) to the artifact path if specified
3. Return a summary with: formula, space group, confidence score, structure file path
4. Report any errors or low-confidence warnings clearly
