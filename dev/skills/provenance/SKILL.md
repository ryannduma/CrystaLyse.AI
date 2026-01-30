---
name: provenance
description: >
  Track and validate data provenance for computational materials science. Use when:
  (1) logging computed values with sources, (2) validating a report has complete
  attribution, (3) generating provenance summary tables, (4) checking if a value
  has a source before reporting it, (5) ensuring no numerical claims are unprovenanced.
---

# Provenance Tracking

Every computed value in CrystaLyse must have provenance. This skill provides
patterns for tracking, validating, and reporting data sources.

## Core Principle

**Every number needs a source.** Values come from:

- Computation (MACE, Chemeleon, SMACT)
- Database (Materials Project, AFLOW, COD via OPTIMADE)
- Literature (papers with DOIs)

**Never**: Estimate, guess, or report values without attribution.

## Provenance Schema

Every provenanced value has these fields:

```json
{
  "property": "formation_energy",
  "value": -2.34,
  "unit": "eV/atom",
  "source": {
    "type": "computation",
    "method": "MACE-MP-0 medium",
    "input": "predicted_Ba2SnO4_001.cif",
    "timestamp": "2025-01-22T10:30:00Z"
  }
}
```

## Source Types

| Type | Required Fields | Example |
|------|-----------------|---------|
| `computation` | method, input, timestamp | MACE energy calculation |
| `database` | database, entry_id, retrieved | Materials Project mp-1234 |
| `literature` | doi, authors, year | Chen et al. 2020 |
| `derived` | source_values, operation | Hull distance from energies |

**NOT ALLOWED**: `unknown`, `estimated`, `typical`, `approximately`

## Quick Validation Pattern

Before reporting any numerical value, check:

```python
def validate_provenance(value, source):
    """Return True if value has valid provenance."""
    if source is None:
        return False

    required_fields = {
        "computation": ["method", "input", "timestamp"],
        "database": ["database", "entry_id"],
        "literature": ["doi", "authors", "year"],
        "derived": ["source_values", "operation"],
    }

    source_type = source.get("type")
    if source_type not in required_fields:
        return False

    for field in required_fields[source_type]:
        if field not in source:
            return False

    return True
```

## Material Property Keywords

These properties MUST have provenance (render gate will block if missing):

**Energy properties:**

- Formation energy, binding energy, cohesive energy
- Energy above hull, decomposition energy
- Any value in eV, eV/atom, kJ/mol

**Electronic properties:**

- Band gap, work function, electron affinity
- Fermi energy, ionization energy

**Structural properties:**

- Lattice parameters (a, b, c, alpha, beta, gamma)
- Cell volume, density
- Bond lengths, coordination numbers

**Thermal/mechanical:**

- Bulk modulus, shear modulus
- Melting point, decomposition temperature

## Allowed Without Provenance

These contextual values don't need explicit sources:

- Stoichiometry (e.g., "LiFePO4 has 4 oxygen atoms")
- Atomic numbers (e.g., "Fe has Z=26")
- Universal constants (e.g., "kB = 8.617e-5 eV/K")
- Counts and statistics (e.g., "found 12 phases")
- Percentages (e.g., "85% of candidates passed")

## Provenance Summary Table

Every report should end with a provenance table:

```markdown
## Provenance

| Value | Source |
|-------|--------|
| E_form = -2.34 eV/atom | MACE-MP-0 medium (this session) |
| E_hull = 0.02 eV/atom | Materials Project convex hull |
| Band gap = 2.4 eV | Chen et al. 2020, DOI:10.1016/... |
| Synthesis temp = 1200°C | Liu et al. 2019, DOI:10.1021/... |
```

## Handling Missing Provenance

When you cannot provide provenance for a requested value:

**Do NOT:**

```text
"The band gap is approximately 2.4 eV"
"The formation energy is around -2 eV/atom"
```

**Do:**

```text
"I cannot compute the band gap (MACE provides energies, not electronic structure).
Literature reports band gap of 2.4 eV for this material (Chen et al. 2020)."
```

Or:

```text
"Band gap: Cannot compute without DFT. Query Materials Project or cite literature."
```

## Artifact Tracking

When workers or the lead agent compute values, save full results to artifacts:

```text
/session/
├── provenance.json          # Central provenance log
├── mace_results.json        # Full MACE output
├── optimade_results.json    # Full database query results
└── literature.json          # Literature search results
```

The provenance.json file aggregates all sources:

```json
{
  "session_id": "abc123",
  "values": [
    {
      "property": "formation_energy",
      "material": "Ba2SnO4",
      "value": -2.34,
      "unit": "eV/atom",
      "source": {
        "type": "computation",
        "method": "MACE-MP-0 medium",
        "artifact": "/session/mace_results.json"
      }
    }
  ]
}
```

## Self-Check Before Reporting

Before generating a final report, the lead agent should:

1. **Scan for numbers with units** (eV, GPa, K, nm, etc.)
2. **Check each has a source** in the provenance log
3. **Flag any unprovenanced values**
4. **Either add source or remove/caveat the value**

```python
def check_report_provenance(report_text, provenance_log):
    """Find values without provenance."""
    # Pattern: number + unit
    pattern = r'\d+\.?\d*\s*(?:eV|GPa|K|°C|nm|Å|meV)'
    values = re.findall(pattern, report_text)

    unprovenanced = []
    for value in values:
        if not has_source(value, provenance_log):
            unprovenanced.append(value)

    return unprovenanced
```

## For Workers

If you're a worker subagent:

1. Every computed value you return must include its source
2. Use the structured output format with source fields
3. If a tool fails, report the failure—don't estimate
4. Write full results to artifacts for the lead agent to verify
