---
name: python-analysis
description: >
  Write and execute custom Python code for materials analysis. Use when:
  (1) CLI scripts don't cover the analysis needed, (2) custom data processing,
  (3) combining multiple analyses, (4) debugging or inspecting intermediate
  results, (5) plotting or visualization. Has access to numpy, scipy, pandas,
  pymatgen, and ase.
---

# Custom Python Analysis

Write and execute Python code for materials science analysis when pre-built
CLI tools don't cover your needs.

## Available Libraries

The Python execution environment includes:

| Library | Import | Use For |
|---------|--------|---------|
| numpy | `np` | Numerical operations |
| pandas | `pd` | Data manipulation |
| scipy | `scipy` | Scientific computing |
| pymatgen | `Structure`, `Composition`, `Lattice` | Materials structures |
| ase | `Atoms`, `ase` | Atomic simulations |
| json | `json` | Data serialization |
| math | `math` | Math functions |
| pathlib | `Path` | File paths |

## Quick Usage

Use the `execute_python` tool:

```python
execute_python(code='''
from pymatgen.core import Structure

# Load a structure
struct = Structure.from_file("structure.cif")

# Custom analysis
result = {
    "formula": struct.composition.reduced_formula,
    "volume": struct.volume,
    "density": struct.density
}
print(result)
''')
```

## When to Use Python vs CLI Scripts

| Situation | Use CLI | Use Python |
|-----------|---------|------------|
| Standard validation | `validate.py "LiFePO4"` | - |
| Standard hull distance | `hull_distance.py ...` | - |
| Custom bond analysis | - | Write code |
| Combining multiple analyses | - | Write code |
| Data filtering/transformation | - | Write code |
| Debugging failures | - | Inspect objects |
| One-off calculations | - | Quick code |

## Common Analysis Patterns

### Pattern 1: Bond Length Analysis

```python
from pymatgen.core import Structure
from pymatgen.analysis.local_env import CrystalNN

struct = Structure.from_file("structure.cif")
nn = CrystalNN()

# Find all Fe-O bonds
fe_sites = [i for i, site in enumerate(struct) if site.specie.symbol == "Fe"]

fe_o_distances = []
for i in fe_sites:
    neighbors = nn.get_nn_info(struct, i)
    for neighbor in neighbors:
        if neighbor['site'].specie.symbol == "O":
            fe_o_distances.append(struct[i].distance(neighbor['site']))

result = {
    "avg_fe_o": sum(fe_o_distances) / len(fe_o_distances),
    "min_fe_o": min(fe_o_distances),
    "max_fe_o": max(fe_o_distances),
    "n_bonds": len(fe_o_distances)
}
print(result)
```

### Pattern 2: Coordination Number Analysis

```python
from pymatgen.core import Structure
from pymatgen.analysis.local_env import VoronoiNN

struct = Structure.from_file("structure.cif")
voronoi = VoronoiNN()

coord_numbers = {}
for i, site in enumerate(struct):
    cn = voronoi.get_cn(struct, i)
    symbol = site.specie.symbol
    if symbol not in coord_numbers:
        coord_numbers[symbol] = []
    coord_numbers[symbol].append(cn)

result = {
    element: sum(cns) / len(cns)
    for element, cns in coord_numbers.items()
}
print(f"Average coordination numbers: {result}")
```

### Pattern 3: Space Group Determination

```python
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

struct = Structure.from_file("structure.cif")
analyzer = SpacegroupAnalyzer(struct)

result = {
    "space_group": analyzer.get_space_group_symbol(),
    "space_group_number": analyzer.get_space_group_number(),
    "crystal_system": analyzer.get_crystal_system(),
    "point_group": analyzer.get_point_group_symbol()
}
print(result)
```

### Pattern 4: Structure Comparison

```python
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

struct1 = Structure.from_file("predicted.cif")
struct2 = Structure.from_file("reference.cif")

matcher = StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5)

if matcher.fit(struct1, struct2):
    rms_dist = matcher.get_rms_dist(struct1, struct2)
    print(f"Structures match! RMSD: {rms_dist[0]:.3f} Angstrom")
else:
    print("Structures do not match")
```

### Pattern 5: Band Gap Estimation

```python
from pymatgen.core import Structure
from pymatgen.analysis.bond_valence import BVAnalyzer

struct = Structure.from_file("structure.cif")

# Get oxidation states
bv = BVAnalyzer()
try:
    oxi_struct = bv.get_oxi_state_decorated_structure(struct)
    has_metals = any(
        site.specie.oxi_state > 0 and site.specie.is_metal
        for site in oxi_struct
    )
    result = {
        "oxidation_states": str([str(s.specie) for s in oxi_struct]),
        "likely_insulator": not has_metals
    }
except Exception as e:
    result = {"error": str(e)}

print(result)
```

## Safety and Best Practices

### Do:
- Use try/except for error handling
- Print results as JSON for easy parsing
- Keep code focused on one analysis
- Comment complex calculations

### Don't:
- Modify files without user approval
- Run infinite loops
- Make network requests (use dedicated tools)
- Install packages (environment is fixed)

## Error Handling Pattern

```python
try:
    from pymatgen.core import Structure
    struct = Structure.from_file("structure.cif")

    # Your analysis here
    result = {"success": True, "data": {...}}

except FileNotFoundError:
    result = {"success": False, "error": "Structure file not found"}
except Exception as e:
    result = {"success": False, "error": str(e)}

print(json.dumps(result))
```

## Combining with Other Skills

Python analysis often follows other skills:

```
1. [smact-validation] Validate composition
2. [chemeleon-prediction] Predict structure
3. [python-analysis] Custom bond analysis on predicted structure
4. [mace-calculation] Calculate energy
```

Example workflow:
```python
# After Chemeleon prediction, analyze the result
from pymatgen.core import Structure

# Load the predicted structure
struct = Structure.from_file("chemeleon_output.cif")

# Custom analysis not available in CLI
distortion = calculate_octahedral_distortion(struct)
tilting = calculate_tilt_angles(struct)

result = {
    "formula": struct.composition.reduced_formula,
    "octahedral_distortion": distortion,
    "tilt_angles": tilting,
    "volume_per_atom": struct.volume / len(struct)
}
print(json.dumps(result))
```

## Provenance

When reporting Python analysis results, include:
1. The code used (summarized)
2. Input files/data
3. Library versions (if critical)
4. Any assumptions made

Example:
```
Analysis: Fe-O bond lengths
Method: CrystalNN neighbor analysis (pymatgen)
Input: predicted_structure.cif
Result: Average Fe-O = 2.01 Å (range: 1.95-2.08 Å)
```
