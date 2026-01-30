---
name: optimade-search
description: >
  Query materials databases via OPTIMADE API. Use when: (1) checking if a
  composition exists in databases, (2) finding competing phases for hull
  distance, (3) getting reference structures for comparison, (4) validating
  predictions against known materials, (5) grounding recommendations in data.
---

# OPTIMADE Database Search

Query 20+ materials databases with a single interface via the OPTIMADE API.

## Available Providers

| Provider | Description | Strengths |
|----------|-------------|-----------|
| `mp` | Materials Project | DFT properties, large coverage |
| `aflow` | AFLOW database | Automated workflows, symmetry |
| `cod` | Crystallography Open Database | Experimental structures, XRD |
| `oqmd` | Open Quantum Materials Database | Formation energies, stability |
| `nomad` | NOMAD Repository | Raw data, reproducibility |

## Quick Usage

Use the `query_optimade` tool:

```python
query_optimade(
    filter_query='elements HAS ALL "Li","Fe","P","O"',
    provider="mp",
    page_limit=10
)
```

## Filter Syntax

OPTIMADE uses a specific filter language:

| Pattern | Meaning | Example |
|---------|---------|---------|
| `nelements=N` | Exactly N elements | `nelements=3` |
| `elements HAS "X"` | Contains element X | `elements HAS "Li"` |
| `elements HAS ALL "X","Y"` | Contains X and Y | `elements HAS ALL "Li","O"` |
| `chemical_formula_reduced="X"` | Exact reduced formula | `chemical_formula_reduced="TiO2"` |
| `nsites<N` | Unit cells with <N atoms | `nsites<100` |
| `_mp_bandgap>N` | MP-specific: band gap | `_mp_bandgap>1` |

## When to Use OPTIMADE

### Before Predicting a Structure

```python
# Check if composition exists before running Chemeleon
result = query_optimade('chemical_formula_reduced="Sr2TiO4"', provider="mp")

if result["count"] > 0:
    print("Known compound - use database structure as reference")
    # Compare predicted structure to known phase
else:
    print("Novel composition - proceed with prediction")
```

### Finding Competing Phases for Hull Distance

```python
# Get all phases in Li-Fe-P-O space for hull calculation
result = query_optimade(
    'elements HAS ALL "Li","Fe","P","O"',
    provider="mp",
    page_limit=50
)

# Use these as input to hull_distance calculation
```

### Cross-Database Validation

```python
# Check if prediction matches known phases across databases
for provider in ["mp", "aflow", "oqmd"]:
    result = query_optimade(
        'chemical_formula_reduced="BiVO4"',
        provider=provider
    )
    print(f"{provider}: {result['count']} entries")
```

## When NOT to Use OPTIMADE

| Situation | Better Alternative |
|-----------|-------------------|
| Need computed properties (band gap, elastic) | Use Materials Project API directly |
| Need high-quality reference structures | Use pymatgen's MP interface |
| Need synthesis conditions | Use web_search for literature |
| Checking formula validity | Use SMACT validation first |

## Provenance Requirements

Every OPTIMADE result includes provenance information. When using database structures, **always record**:

1. Provider name (mp, aflow, cod, etc.)
2. Entry ID (mp-12345, oqmd-67890)
3. Query filter used
4. Number of results found

Example provenance note:
```
Structure source: Materials Project mp-1234
Query: elements HAS ALL "Li","Fe","O"
Retrieved: 2024-01-15
```

## Common Workflows

### Workflow 1: Validate Prediction Against Known Phases

```
1. Predict structure with Chemeleon
2. Query OPTIMADE for same composition
3. If matches exist:
   - Calculate RMSD to nearest known phase
   - If RMSD < 0.1: "Matches known phase"
   - If RMSD > 0.1: "Possible new polymorph"
4. Report with database provenance
```

### Workflow 2: Composition Space Exploration

```
1. Define element set (e.g., Li, Mn, O)
2. Query OPTIMADE: 'elements HAS ALL "Li","Mn","O"'
3. Analyze gap in coverage (stoichiometries not in DB)
4. Target gaps for novel material prediction
```

### Workflow 3: Competing Phase Analysis

```
1. For target composition Li2MnO3
2. Query all binaries: Li-O, Mn-O, Li-Mn
3. Query all ternaries in Li-Mn-O space
4. Build convex hull with these entries
5. Calculate e_above_hull for target
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Connection error" | Provider down | Try different provider |
| "Invalid filter syntax" | Malformed query | Check OPTIMADE spec |
| "No results" | Composition not in DB | Confirm novel, proceed |
| "Rate limited" | Too many requests | Wait and retry |

## Tips for Best Results

1. **Start specific, broaden if needed**: `chemical_formula_reduced="TiO2"` before `elements HAS ALL "Ti","O"`
2. **Use multiple providers**: MP and AFLOW have different coverage
3. **Check `nsites`**: Small cells are more likely to be well-characterized
4. **Cross-reference**: Same formula may have multiple polymorphs

## For Workers

If you're a worker subagent executing this skill:

1. Follow the task instructions from the lead agent (filter, providers, fields)
2. Write full query results (all entries) to artifact path if specified
3. Return a summary with: total count, top entries with IDs, any gaps in coverage
4. Report any provider errors or rate limits encountered
