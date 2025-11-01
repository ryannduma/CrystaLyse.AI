# Crystalyse v1.0

**Intelligent Scientific AI Agent for Inorganic Materials Design**

[![PyPI version](https://badge.fury.io/py/crystalyse.svg)](https://badge.fury.io/py/crystalyse)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Version 1.0.0**
> Research tool combining composition validation (SMACT), structure prediction (Chemeleon), energy calculations (MACE), and materials analysis (PyMatGen)

## What's New in v1.0

Version 1.0 includes significant architectural changes focused on computational traceability and simplified setup:

### Key Features

**Provenance System**
- Every numerical value traces to actual calculations
- Render gate prevents unprovenanced values from being displayed
- Full audit trail of all operations
- No fabricated or hallucinated numbers

**Automated Setup**
- Chemeleon checkpoints auto-download on first use (~600 MB)
- Materials Project phase diagrams auto-download (~170 MB, 271,617 entries)
- Files cached in `~/.cache/crystalyse/`
- Environment variables are optional

**PyMatGen Integration**
- Energy above hull calculations using 271,617 Materials Project entries
- Phase diagram construction
- Decomposition product analysis
- Stability assessment (stable/metastable/unstable)

**Adaptive Clarification System**
- Learns user expertise level over time
- Adjusts question complexity accordingly
- Fewer interruptions for experienced users
- More guidance for new users

**Analysis Modes**
- **Creative Mode**: Fast exploration (~50s) with Chemeleon + MACE
- **Rigorous Mode**: Full validation (2-5min) with SMACT + Chemeleon + MACE + analysis
- **Adaptive Mode**: Automatic mode selection based on query complexity

**Simplified Architecture**
- Modular tool implementations
- Python packaging for MCP servers
- Cleaner separation of concerns

## Quick Start

### Installation

```bash
# Install from PyPI (includes all dependencies and MCP servers)
pip install crystalyse

# Optional: visualization tools
pip install crystalyse[visualization]

# Set your OpenAI API key
export OPENAI_MDG_API_KEY="sk-your-key-here"

# Verify installation
crystalyse --help
```

### First Run

On first run, CrystaLyse will automatically download:
- Chemeleon model checkpoints (~600 MB, one-time)
- Materials Project phase diagrams (~170 MB, one-time)

These are cached in `~/.cache/crystalyse/` and never downloaded again.

### Basic Usage

```bash
# Creative mode (fast exploration)
crystalyse analyse "Find stable perovskite materials for solar cells" --mode creative

# Rigorous mode (complete validation)
crystalyse analyse "Analyze LiCoO2 for battery applications" --mode rigorous

# Interactive session with memory
crystalyse chat -u researcher -s battery_project

# Resume previous session
crystalyse resume battery_project -u researcher
```

## Scientific Capabilities

### Materials Discovery Pipeline

1. **Composition Validation** (SMACT)
   - Chemical plausibility screening
   - Charge balancing
   - Electronegative balance
   - Quick filtering of impossible compositions

2. **Structure Prediction** (Chemeleon)
   - AI-powered crystal structure generation
   - Multiple polymorph candidates
   - Confidence scores for each structure
   - Text-guided generation

3. **Energy Calculations** (MACE)
   - Formation energy evaluation
   - Structure relaxation
   - Uncertainty quantification
   - GPU-accelerated calculations

4. **Stability Analysis** (PyMatGen)
   - Energy above hull calculations
   - Phase diagram construction
   - Decomposition products
   - Competing phases analysis

5. **Visualization** (Optional)
   - 3D crystal structures
   - XRD patterns
   - Radial distribution functions
   - Coordination environment analysis

### Research Applications

**Energy Materials**
- Battery cathodes and anodes (Li-ion, Na-ion, solid-state)
- Solid electrolytes and fast ion conductors
- Photovoltaic semiconductors and perovskites
- Thermoelectric materials

**Electronic Materials**
- Ferroelectric and multiferroic materials
- Magnetic materials and spintronics
- Semiconductor devices
- Quantum materials

**Structural Materials**
- High-temperature ceramics
- Hard coatings and superhard materials
- Transparent conductors

## Performance

| Operation | Creative Mode | Rigorous Mode |
|-----------|---------------|---------------|
| Simple query (single material) | ~50 seconds | 2-3 minutes |
| Complex analysis (multiple candidates) | 1-2 minutes | 3-5 minutes |
| Batch screening (10+ materials) | 5-10 minutes | 15-30 minutes |

## Advanced Usage

### Interactive Sessions

```bash
# Start research session
crystalyse chat -u researcher -s solar_cells -m creative

# In-session commands
/mode rigorous          # Switch to rigorous mode
/mode creative          # Switch to creative mode
/help                   # Show commands
/exit                   # Exit session
```

### Custom Data Paths

```bash
# Use custom checkpoint directory
export CHEMELEON_CHECKPOINT_DIR=/path/to/checkpoints
crystalyse analyse "BaTiO3"

# Use custom phase diagram data
export CRYSTALYSE_PPD_PATH=/path/to/ppd.pkl.gz
crystalyse analyse "LiCoO2"
```

### Programmatic API

```python
from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import CrystaLyseConfig

# Initialize agent
config = CrystaLyseConfig()
agent = EnhancedCrystaLyseAgent(config=config, mode="rigorous")

# Run analysis
result = agent.query(
    "Analyze CsSnI3 perovskite for photovoltaic applications",
    user_id="researcher"
)

print(result.response)
```

## Computational Honesty

Crystalyse implements a provenance system to track the origin of all computed values:

- **Traceability**: Every numerical value traces to actual tool calculations
- **Render Gate**: Blocks unprovenanced values from being displayed
- **Audit Trail**: Full JSONL logs of all operations
- **Uncertainty**: Predictions include confidence scores when available

If Crystalyse reports a formation energy, it was calculated by MACE. If it reports an energy above hull, it came from PyMatGen with Materials Project data. The LLM interprets results but doesn't fabricate numbers.

## Migration from crystalyse-ai

If you're upgrading from the old `crystalyse-ai` package:

### Breaking Changes

1. **Package name**: `pip install crystalyse` (not `crystalyse-ai`)
2. **Import name**: `from crystalyse import ...` (not `from crystalyse_ai import ...`)
3. **MCP servers**: Now bundled automatically (no separate installation)
4. **Auto-download**: Checkpoints and data files download automatically
5. **Environment variables**: Custom checkpoint/data paths are now optional

### Migration Steps

```bash
# Uninstall old version
pip uninstall crystalyse-ai

# Install new version
pip install crystalyse

# Update imports in your code
# OLD: from crystalyse_ai.agents import ...
# NEW: from crystalyse.agents import ...

# Remove manual checkpoint/data management
# Everything auto-downloads now
```

### What Stays the Same

- CLI interface (mostly compatible)
- Core workflow concepts
- Analysis modes (creative/rigorous/adaptive)
- Session management

## System Requirements

- **Python**: 3.11 or higher
- **Memory**: 8GB minimum, 16GB recommended
- **Disk**: 2GB for checkpoints and cache
- **GPU**: Optional, accelerates MACE calculations
- **Network**: Required for first-time setup (auto-downloads)

## Documentation

- [Installation Guide](https://github.com/ryannduma/CrystaLyse.AI/blob/master/docs/installation.md)
- [User Guide](https://github.com/ryannduma/CrystaLyse.AI/blob/master/docs/user-guide.md)
- [API Documentation](https://github.com/ryannduma/CrystaLyse.AI/blob/master/docs/api.md)
- [Provenance System](https://github.com/ryannduma/CrystaLyse.AI/blob/master/docs/provenance.md)
- [CLAUDE.md](https://github.com/ryannduma/CrystaLyse.AI/blob/master/CLAUDE.md) - Developer guide

## Acknowledgments

Crystalyse builds on open-source tools from the materials science community:

- **SMACT** - Semiconducting Materials by Analogy and Chemical Theory
- **Chemeleon** - AI-powered crystal structure prediction
- **MACE** - Machine learning ACE force fields
- **PyMatGen** - Python Materials Genomics
- **Pymatviz** - Materials visualization toolkit
- **OpenAI Agents SDK** - Agent orchestration framework

## Citation

If you use CrystaLyse in your research, please cite the underlying tools:

```bibtex
@article{davies2019smact,
  title={SMACT: Semiconducting Materials by Analogy and Chemical Theory},
  author={Davies, Daniel W and Butler, Keith T and Jackson, Adam J and others},
  journal={Journal of Open Source Software},
  volume={4},
  number={38},
  pages={1361},
  year={2019}
}

@article{park2025chemeleon,
  title={Exploration of crystal chemical space using text-guided generative artificial intelligence},
  author={Park, Hyun Seo and others},
  journal={Nature Communications},
  year={2025}
}

@article{batatia2022mace,
  title={MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields},
  author={Batatia, Ilyes and others},
  journal={NeurIPS},
  year={2022}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ryannduma/CrystaLyse.AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ryannduma/CrystaLyse.AI/discussions)
- **Email**: ryannduma@gmail.com

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with computational honesty by [Ryan Nduma](https://github.com/ryannduma)**
