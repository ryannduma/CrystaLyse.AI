# Tools Overview

Crystalyse integrates several powerful computational chemistry tools to enable autonomous materials design.

## Available Tools

### [SMACT](smact.md)
**Semiconducting Materials by Analogy and Chemical Theory**
- Composition generation and screening
- Charge neutrality validation
- Electronegativity checks
- Dopant prediction and band gap estimation

### [Chemeleon](chemeleon.md)
**Crystal Structure Prediction**
- Structure prediction from composition
- Space group determination
- Lattice parameter estimation
- Checkpoint management for ML models

### [MACE](mace.md)
**Machine Learning Force Fields**
- Fast and accurate machine learning interatomic potentials
- Energy and force calculations
- Structure relaxation and stability analysis
- Stress tensor calculation and EOS fitting

### [Visualisation](visualisation.md)
**Interactive 3D Structure Viewing**
- 3Dmol.js integration
- Structure rendering and CIF export
- Analysis plots (XRD, RDF, Coordination) via server

## Integration

These tools are orchestrated by the Crystalyse agents to perform complex workflows:

- **Creative Mode**: Uses Chemeleon and MACE for rapid structure generation and ranking.
- **Rigorous Mode**: Adds SMACT for initial screening and performs comprehensive analysis.

See the [Analysis Modes](../concepts/analysis_modes.md) documentation for more details on how these tools are used in different workflows.
