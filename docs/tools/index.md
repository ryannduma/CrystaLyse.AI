# Tools Overview

Crystalyse integrates several powerful computational chemistry tools to enable autonomous materials design.

The tools reach the agent as MCP tools. Three servers are shipped, exposing 29 tools in
total: `chemistry_unified` (20), `chemistry_creative` (4) and `visualization` (5).

## Available Tools

### [SMACT](smact.md)
**Semiconducting Materials by Analogy and Chemical Theory**
- Composition validity checks (`smact_validity`) with a selectable oxidation-state dataset
- Charge neutrality and Pauling electronegativity screening
- Composition enumeration (`filter_compositions`) and 103-element ML representations
- Dopant prediction and electronegativity-based band gap estimation

### [Chemeleon](chemeleon.md)
**Crystal Structure Prediction**
- Structure prediction from composition via a denoising diffusion model
- In-memory output: cell, Cartesian positions, atomic numbers, symbols, volume
- Multiple samples per formula
- Checkpoint management with auto-download from Figshare

### [MACE](mace.md)
**Machine Learning Force Fields**
- Fast and accurate machine learning interatomic potentials
- Energy and force calculations
- Structure relaxation (atomic positions) and stability analysis
- Stress tensor calculation and EOS fitting

### PyMatgen Analysis
**Structure and thermodynamic analysis** (part of the unified server)
- `analyze_space_group` - symmetry analysis of a predicted or supplied structure
- `analyze_coordination` - coordination environments (Voronoi by default)
- `validate_oxidation_states` - oxidation state assignment checks
- `calculate_energy_above_hull` - convex-hull distance from a phase-diagram dataset

The phase-diagram dataset is downloaded on demand to `~/.cache/crystalyse/`
(~178 MB, 271617 entries). Run `crystalyse setup` to fetch it ahead of time.

### [Visualisation](visualisation.md)
**Structure files and analysis plots**
- CIF export (3dmol.js interactive viewing is disabled for v2.0-alpha)
- Analysis plots as Plotly-generated PDFs: 3D structure, XRD, RDF, coordination

## Integration

These tools are orchestrated by the Crystalyse agents to perform complex workflows.
Each mode selects one chemistry server:

- **explore** → `chemistry_creative`: Chemeleon and MACE for rapid structure generation
  and energy ranking. No SMACT, deliberately, for speed.
- **validate** → `chemistry_unified`: the full pipeline, adding SMACT screening and the
  PyMatgen analysis tools.
- **auto** → `chemistry_unified`: the same server as validate, with a shorter timeout
  budget. This is the CLI default.

The legacy mode names `creative`, `rigorous` and `adaptive` still resolve to
`explore`, `validate` and `auto` respectively, but emit a `DeprecationWarning`.
Note that the MCP server *directory* is still named `chemistry-creative-server`;
that is a package name and is unchanged.

See the [Analysis Modes](../concepts/analysis_modes.md) documentation for more details on how these tools are used in different workflows.
