# Crystalyse

**Version 1.0.0**

Crystalyse is an open, provenance-enforced scientific agent for computational materials design of inorganic crystals. The system orchestrates tools for compositional screening, crystal structure generation, and machine-learning force-field evaluation through a reasoning language model.

> **Published Package**: The stable v1.0.1 release is available on PyPI as [`crystalyse`](https://pypi.org/project/crystalyse/).
> **Development Version**: This repository contains v1.0.0-dev with ongoing improvements.

## Overview

Crystalyse integrates four computational backends through Model Context Protocol (MCP) endpoints:

- **SMACT** - Compositional screening via charge balance and electronegativity checks
- **Chemeleon** - Crystal structure generation using denoising diffusion models
- **MACE-MP0** - Formation energy calculation via machine learning force fields
- **PyMatGen** - Phase diagram analysis and crystallographic tools

The agent operates through the OpenAI Agents SDK, supporting three modes that balance exploration breadth against validation depth:

- **Creative** - Rapid exploration (~50s per query) with fewer candidate structures
- **Rigorous** - Thorough validation (2-5min per query) with extensive polymorph sampling
- **Adaptive** - Dynamic routing based on query complexity

Anti-hallucination mechanisms enforce provenance tracking: every numerical property must trace to explicit tool invocations rather than model estimation.

## Quick Start

### Installation

**From PyPI (Stable v1.0.1)**:
```bash
pip install crystalyse
export OPENAI_API_KEY="sk-your-key-here"
crystalyse --help
```

**From Source (Development v1.0.0-dev)**:
```bash
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI/dev

# Install core package
pip install -e .

# Install MCP servers
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server

# Configure
export OPENAI_API_KEY="sk-your-key-here"
crystalyse --help
```

### First Run

On first execution, Crystalyse automatically downloads:
- Chemeleon model checkpoints (~600 MB, cached in `~/.cache/crystalyse/`)
- Materials Project phase diagrams (~170 MB, 271,617 entries)

### Basic Usage

```bash
# Non-interactive analysis
crystalyse discover "Find stable perovskite materials" --mode creative

# Interactive session
crystalyse chat -u researcher -s project_name

# Resume previous session

```

## Operational Modes

| Mode | Duration | Structures/Composition | Use Case |
|------|----------|------------------------|----------|
| Creative | ~50s | ~3 candidates | Rapid exploration, broad screening |
| Rigorous | 2-5min | 30+ candidates | Final validation, publication-ready |
| Adaptive | Variable | Context-dependent | Dynamic routing based on query |

Mode selection affects:
- Number of crystal structures generated per composition
- Depth of stability validation
- Computational resource allocation

## Example Tasks

**Quaternary Oxide Discovery**:
```bash
crystalyse discover "Predict five new stable quaternary compositions formed of K, Y, Zr and O" --mode rigorous
```
Result: K₃Y₃Zr₃O₁₂ with energy above hull of 51 meV/atom (metastable).

**Sodium-Ion Battery Cathode**:
```bash
crystalyse discover "Suggest a new Na-ion battery cathode" --mode creative
```
Result: Na₃V₂(PO₄)₂F₃ with predicted capacity of 193 mAh/g at 3.7 V.

**Lead-Free Photovoltaics**:
```bash
crystalyse discover "Alternative to CsPbI3 for indoor photovoltaics" --mode rigorous
```
Result: Cs₂AgBiBr₆ with 0.54 meV/atom above hull and 1.95 eV bandgap.

## Provenance System

The system enforces computational honesty through three layers:

1. **Prompt Guidance** - Instructs compute-or-decline behaviour
2. **Runtime Tracking** - Captures all tool outputs with (value, unit, source_tool, artifact_hash, timestamp)
3. **Render Gate** - Blocks unprovenanced numerical claims from display

All reported material properties originate from explicit tool invocations. Derived values (e.g., battery capacity = 26801/*M*) are calculated from provenanced inputs. JSONL audit trails enable full reproducibility.

## Performance

Computational requirements:
- **Python**: 3.11+
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: ~2GB for installation and cache
- **GPU**: Optional, accelerates MACE calculations
- **Network**: Required for first-run downloads

Timing benchmarks (Intel i7, 16GB RAM):
- Simple query: Creative 50s, Rigorous 2-3min
- Complex analysis: Creative 1-2min, Rigorous 3-5min
- Batch processing (10 materials): Creative 5-10min, Rigorous 15-30min

## Documentation

- **[User Guide](dev/docs/guides/cli_usage.md)** - Command reference and workflows
- **[Installation Guide](dev/docs/guides/installation.md)** - Detailed setup instructions
- **[Analysis Modes](dev/docs/concepts/analysis_modes.md)** - Mode selection strategies
- **[Provenance System](dev/docs/concepts/provenance.md)** - Anti-hallucination architecture
- **[Tool Documentation](dev/docs/tools/)** - SMACT, Chemeleon, MACE, PyMatGen

## Architecture

The system uses a single-agent architecture with modular MCP servers:

```
User Prompt → Clarification Engine → Mode Selection (Creative/Adaptive/Rigorous)
                                                    ↓
                              Reasoning LLM (OpenAI o3/o4-mini)
                                                    ↓
                        MCP Toolkit (SMACT, Chemeleon, MACE, PyMatGen)
                                                    ↓
                              Provenance Tracking & Validation
                                                    ↓
                            Results with Complete Audit Trail
```

Memory system provides four layers:
- Session memory (conversation history, tool traces)
- Discovery cache (computed materials, 24hr TTL)
- User preference memory (expertise level, clarification depth)
- Cross-session context (research themes, successful strategies)

## Safety and Sustainability

The agent implements three-tier safety filtering:

**Tier 1** (Automatic refusal) - Explosive materials, toxic heavy metals, chemical weapon precursors

**Tier 2** (Context review) - Ambiguous requests requiring additional clarification

**Tier 3** (Safe execution) - Legitimate safety applications (fire-resistant ceramics, biocompatible implants)

Sustainability awareness includes earth-abundant element prioritisation (Fe, Al, Si over rare earths) and critical element flagging (Co, In, Ga dependencies).

## Citation

If you use Crystalyse in your research, please cite the underlying tools:

```bibtex
@article{Davies2019,
  doi = {10.21105/joss.01361},
  url = {https://doi.org/10.21105/joss.01361},
  year = {2019},
  publisher = {The Open Journal},
  volume = {4},
  number = {38},
  pages = {1361},
  author = {Davies, Daniel W. and Butler, Keith T. and Jackson, Adam J. and Skelton, Jonathan M. and Morita, Kazuki and Walsh, Aron},
  title = {SMACT: Semiconducting Materials by Analogy and Chemical Theory},
  journal = {Journal of Open Source Software}
}

@article{park2025chemeleon,
  title={Exploration of crystal chemical space using text-guided generative artificial intelligence},
  author={Park, Hyun and Onwuli, Adaeze and Walsh, Aron},
  journal={Nature Communications},
  volume={16},
  pages={4379},
  year={2025},
  doi={10.1038/s41467-025-59636-y}
}

@article{batatia2025foundation,
  title={A foundation model for atomistic materials chemistry},
  author={Batatia, Ilyes and others},
  journal={The Journal of Chemical Physics},
  volume={163},
  number={18},
  pages={184110},
  year={2025},
  doi={10.1063/5.0297006}
}

@article{ong2013pymatgen,
  title={Python Materials Genomics (pymatgen): A robust, open-source python library for materials analysis},
  author={Ong, Shyue Ping and Richards, William Davidson and Jain, Anubhav and Hautier, Geoffroy and Kocher, Michael and Cholia, Shreyas and Gunter, Dan and Chevrier, Vincent L and Persson, Kristin A and Ceder, Gerbrand},
  journal={Computational Materials Science},
  volume={68},
  pages={314--319},
  year={2013},
  doi={10.1016/j.commatsci.2012.10.028}
}

@software{riebesell_pymatviz_2022,
  title={Pymatviz: visualization toolkit for materials informatics},
  author={Riebesell, Janosh and Yang, Haoyu and Goodall, Rhys and Baird, Sterling G.},
  year={2022},
  doi={10.5281/zenodo.7486816},
  url={https://github.com/janosh/pymatviz},
  version={0.8.2}
}

@article{seshadri20203dmol,
  title={The 3Dmol.js Learning Environment: A Classroom Response System for 3D Chemical Structures},
  author={Seshadri, Keshavan and Liu, Peng and Koes, David Ryan},
  journal={Journal of Chemical Education},
  volume={97},
  number={10},
  pages={3872--3876},
  year={2020},
  doi={10.1021/acs.jchemed.0c00580}
}
```


## Acknowledgements

Crystalyse builds on open-source tools from the materials science community:

- **SMACT** - Cheminformatics tools for highthrouput screening
- **Chemeleon** - AI-powered crystal structure prediction
- **MACE** - Foundation models for atomistic materials chemistry
- **PyMatGen** - Robust, open-source Python library for materials analysis
- **Pymatviz** - A toolkit for visualisations in materials informatics.
- **3Dmol.js** - A capable visualisation package for 3D Chemical Structures.
- **OpenAI Agents SDK** - Agent orchestration framework

This work was supported by EPSRC project EP/X037754/1 and the AIchemy hub (grants EP/Y028775/1, EP/Y028759/1).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ryannduma/CrystaLyse.AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ryannduma/CrystaLyse.AI/discussions)
- **Email**: napo.nduma22@imperial.ac.uk

---

*Built by Ryan Nduma, Hyunsoo Park, and Aron Walsh with support and inspiration from the AI4SCIENCE community and especially the Materials Design Group at Imperial College London*
