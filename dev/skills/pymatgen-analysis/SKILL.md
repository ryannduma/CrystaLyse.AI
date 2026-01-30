---
name: pymatgen-analysis
description: >
  Crystal structure manipulation and materials analysis using pymatgen. Use when:
  (1) loading/converting structure files (CIF, POSCAR, JSON), (2) computing phase
  stability and energy above hull, (3) analyzing symmetry and space groups,
  (4) preparing VASP inputs, (5) working with compositions and oxidation states.
---

# Pymatgen Analysis

Core library for structure manipulation and thermodynamic analysis.
Claude already knows pymatgen's API - this skill encodes workflow patterns and gotchas.

## Quick Patterns

**Load any structure format:**
```python
from pymatgen.core import Structure
struct = Structure.from_file("POSCAR")  # Auto-detects format
struct = Structure.from_file("structure.cif", merge_tol=0.01)  # IMPORTANT for DFT CIFs
```

**Get space group:**
```python
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
sga = SpacegroupAnalyzer(struct)
sga.get_space_group_symbol()  # e.g., "Fm-3m"
```

**Check phase stability:**
```python
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
pd = PhaseDiagram(entries)
decomp, e_above_hull = pd.get_decomp_and_e_above_hull(my_entry)
```

## Critical Gotcha: merge_tol for CIF Files

DFT-relaxed structures saved to CIF often have **floating-point artifacts** - atoms at nearly-identical positions due to numerical precision.

```python
# ❌ BAD - may have duplicate atoms
struct = Structure.from_file("relaxed.cif")

# ✅ GOOD - merges atoms within 1% of typical bond length
struct = Structure.from_file("relaxed.cif", merge_tol=0.01)
```

**When to use merge_tol:**
- Loading CIF from DFT output (VASP, QE, etc.)
- Combining structures from different sources
- After any numerical transformation

**When NOT to use merge_tol:**
- Loading pristine experimental CIFs
- When you need exact atom positions preserved

## Three Types of "Energy Above Hull"

PyMatGen's phase diagram has **three different hull distance concepts**:

| Method | Returns | Use When |
|--------|---------|----------|
| `get_e_above_hull(entry)` | Perpendicular distance to hull | Quick stability check |
| `get_decomp_and_e_above_hull(entry)` | Decomposition products + energy | Need reaction products |
| `get_equilibrium_reaction_energy(entry)` | Energy vs neighboring phases | Entry is already stable |

**Typical workflow:**
```python
decomp, e_hull = pd.get_decomp_and_e_above_hull(entry)
if e_hull < 0.025:  # eV/atom
    print("Likely synthesizable")
elif e_hull < 0.1:
    print("Metastable, may exist")
else:
    print("Thermodynamically unstable")
```

## Oxidation State Handling

**Gotcha**: `oxi_state_guesses()` returns a **list** (may be empty!).

```python
from pymatgen.core import Composition

comp = Composition("Fe2O3")
guesses = comp.oxi_state_guesses()

# ❌ BAD - crashes if no valid guesses
struct.add_oxidation_state_by_element(guesses[0])

# ✅ GOOD - handle empty case
if guesses:
    struct.add_oxidation_state_by_element(guesses[0])
else:
    # Fallback: neutral oxidation states
    struct.add_oxidation_state_by_element({e.symbol: 0 for e in comp})
```

**Two guessing modes:**
- `all_oxi_states=False` (default): Uses ICSD-validated states → **more reliable**
- `all_oxi_states=True`: All possible states → "can produce nonsensical results"

## Structure Sanitization Warning

`struct.copy(sanitize=True)` reorders sites by electronegativity.

**This breaks indexed property arrays!**
```python
# If you have forces[i] corresponding to struct.sites[i]
clean_struct = struct.copy(sanitize=True)
# Now clean_struct.sites[i] may be a DIFFERENT atom!
```

**When to sanitize:**
- Before comparison with reference structures
- Before symmetry analysis
- After combining fragments

**When NOT to sanitize:**
- When you have indexed properties (forces, charges, etc.)
- When site order matters for downstream analysis

## VASP Input Generation

```python
from pymatgen.io.vasp.sets import MPRelaxSet

vasp_input = MPRelaxSet(struct)
vasp_input.write_input("calculation_dir")  # Writes INCAR, POSCAR, POTCAR, KPOINTS
```

**Override parameters:**
```python
custom_set = MPRelaxSet(struct, user_incar_settings={"EDIFFG": -0.01})
```

## When to Deviate from Defaults

**Use primitive cell for:**
- Band structure calculations
- Phonon calculations
- Reducing computational cost

**Use conventional cell for:**
- Surface calculations
- Visualization
- Comparison with literature

```python
sga = SpacegroupAnalyzer(struct)
primitive = sga.get_primitive_standard_structure()
conventional = sga.get_conventional_standard_structure()
```

## Limitations

**Pymatgen analysis CANNOT:**

- Predict new structures (use Chemeleon)
- Calculate formation energies (use MACE)
- Perform band structure calculations (requires DFT)
- Search external databases (use OPTIMADE)

**Pymatgen is for structure manipulation and thermodynamic analysis**, not prediction or computation.

## Provenance

When reporting pymatgen results:

- Structure source and any transformations applied
- Whether merge_tol was used (and value)
- Which hull distance method was used
- Oxidation state assignment method
- PyMatGen version for reproducibility

## For Workers

If you're a worker subagent executing this skill:

1. Follow the task instructions from the lead agent
2. Write transformed structures or analysis results to artifact path if specified
3. Return a summary with: key metrics (hull distance, space group), any warnings
4. Report if oxi_state_guesses returned empty list or merge_tol was needed
