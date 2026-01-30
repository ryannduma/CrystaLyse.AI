# CrystaLyse Skills Index

Quick reference for available skills. Workers should read the relevant SKILL.md
before executing tasks.

## Skills Overview

| Skill | Purpose | Key Tools | Limitations |
|-------|---------|-----------|-------------|
| `smact-validation` | Check charge balance | `validate.py` | No thermodynamic stability |
| `chemeleon-prediction` | Predict crystal structures | `predict_csp.py`, `predict_dng.py` | No properties, just structures |
| `mace-calculation` | Calculate energies, relax structures | `formation_energy.py`, `relax.py` | No band gaps, phonons |
| `optimade-search` | Query materials databases | `query_optimade` tool | No computed properties |
| `pymatgen-analysis` | Structure manipulation, hull distance | Python API | No predictions |
| `python-analysis` | Custom Python code | `execute_python` tool | Fixed environment |
| `web-search` | Literature search | `web_search` tool | No provenance for numbers |
| `provenance` | Track data sources | Validation patterns | - |

## Typical Workflow

```text
User query
    │
    ▼
smact-validation (is composition valid?)
    │
    ▼
optimade-search (does it exist in databases?)
    │
    ▼
chemeleon-prediction (predict structure if novel)
    │
    ▼
mace-calculation (calculate formation energy)
    │
    ▼
pymatgen-analysis (hull distance, stability)
    │
    ▼
web-search (synthesis conditions, literature)
    │
    ▼
provenance (validate all sources)
    │
    ▼
Report with provenance table
```

## What Each Skill CAN and CANNOT Do

### smact-validation

- CAN: Check charge neutrality, electronegativity balance
- CANNOT: Assess thermodynamic stability, synthesizability, properties

### chemeleon-prediction

- CAN: Predict crystal structures for compositions
- CANNOT: Compute band gaps, energies, or any material property

### mace-calculation

- CAN: Calculate formation energy, relax structures, compute forces
- CANNOT: Compute band gaps, phonons, optical properties, magnetic ordering

### optimade-search

- CAN: Query databases for existing materials, get structures and IDs
- CANNOT: Compute properties (only retrieves what's in the database)

### pymatgen-analysis

- CAN: Manipulate structures, compute hull distance, analyze symmetry
- CANNOT: Predict new structures, calculate energies, do DFT

### web-search

- CAN: Find synthesis conditions, experimental reports, literature
- CANNOT: Provide provenanced numerical values (cite source instead)

### python-analysis

- CAN: Custom analysis with numpy, scipy, pymatgen, ase
- CANNOT: Install packages, make network requests, modify system files

## Worker Output Format

All workers should return structured JSON:

```json
{
  "status": "success",
  "summary": "Brief description (max 200 words)",
  "key_findings": [
    {"item": "...", "source": "...", "confidence": "high"}
  ],
  "artifact": "/session/results.json",
  "gaps": ["What couldn't be found"]
}
```

## Quick Decision Tree

```text
Need to validate a formula?
    └─▶ smact-validation

Need to check if material exists?
    └─▶ optimade-search

Need to predict a structure?
    └─▶ chemeleon-prediction

Need to calculate energy?
    └─▶ mace-calculation

Need to check stability (hull distance)?
    └─▶ pymatgen-analysis

Need synthesis conditions?
    └─▶ web-search

Need custom analysis?
    └─▶ python-analysis

Need to track/validate sources?
    └─▶ provenance
```
