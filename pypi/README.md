# CrystaLyse.AI

> **⚠️ DEPRECATED - This package has been replaced by [`crystalyse`](https://pypi.org/project/crystalyse/)**
>
> **The `crystalyse-ai` package is no longer maintained. Please migrate to the new `crystalyse` package (v1.0.0+) which includes:**
> - Complete provenance system for computational honesty
> - Auto-download of checkpoints and data files
> - Enhanced PyMatGen integration with Materials Project database
> - Streamlined architecture with 90% code reduction
> - Better performance and reliability
>
> **Migration**: Simply `pip uninstall crystalyse-ai && pip install crystalyse`
>
> **See**: [Migration Guide](https://github.com/ryannduma/CrystaLyse.AI/blob/master/pypi-v2/CHANGELOG.md#migration-guide)

---

**CrystaLyse.AI - Autonomous AI agents for accelerated inorganic materials design through natural language interfaces**

[![PyPI version](https://badge.fury.io/py/crystalyse-ai.svg)](https://badge.fury.io/py/crystalyse-ai)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Status: DEPRECATED - Use [`crystalyse`](https://pypi.org/project/crystalyse/) instead**

CrystaLyse.AI is a computational materials design platform that accelerates materials exploration through AI-powered analysis and validation. Built on the OpenAI Agents framework with Model Context Protocol (MCP) integration, it provides a dual-mode system for rapid materials design workflows.

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI
pip install crystalyse-ai

# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# Verify installation
crystalyse --help
```

### Basic Usage

```bash
# Creative mode (fast exploration ~50 seconds)
crystalyse analyse "Find stable perovskite materials for solar cells" --mode creative

# Rigorous mode (complete validation 2-5 minutes)
crystalyse analyse "Analyse CsSnI3 for photovoltaic applications" --mode rigorous

# Interactive session
crystalyse chat
```

## ✨ Key Features

### 🔄 Dual-Mode Analysis System
- **Creative Mode**: Fast exploration (~50 seconds) using Chemeleon + MACE
- **Rigorous Mode**: Complete validation (2-5 minutes) with SMACT + Chemeleon + MACE + Analysis Suite
- Real-time mode switching with unified interface

### 🧪 Complete Materials Pipeline
- **Composition Validation**: SMACT screening for chemically reasonable materials
- **Structure Prediction**: Chemeleon crystal structure generation with multiple candidates
- **Energy Calculations**: MACE formation energy evaluation with uncertainty quantification
- **Comprehensive Analysis**: XRD patterns, RDF analysis, coordination studies
- **3D Visualisation**: CIF file generation and professional analysis plots

### 💻 Advanced Interface Options
- **Unified CLI**: Single command interface with `/mode` and `/agent` switching
- **Session Management**: Persistent conversation history across multi-day projects
- **Interactive Chat**: Research-grade session-based workflows
- **Batch Processing**: High-throughput materials screening capabilities

## 🔬 Scientific Applications

### Energy Materials
- Battery cathodes and anodes (Li-ion, Na-ion, solid-state)
- Solid electrolytes and ion conductors
- Photovoltaic semiconductors and perovskites
- Thermoelectric materials

### Electronic Materials
- Ferroelectric and multiferroic materials
- Magnetic materials and spintronics
- Semiconductor devices and memory materials
- Superconductors and quantum materials

## 📊 Performance Characteristics

| Operation | Creative Mode | Rigorous Mode |
|-----------|---------------|---------------|
| Simple query | ~50 seconds | 2-3 minutes |
| Complex analysis | 1-2 minutes | 3-5 minutes |
| Batch processing | 5-10 minutes | 15-30 minutes |

## 🛠️ Advanced Usage

### Interactive Research Sessions

```bash
# Start a research session
crystalyse chat -u researcher -s solar_project -m creative

# Resume previous work
crystalyse resume solar_project -u researcher

# List all sessions
crystalyse sessions -u researcher
```

### In-Session Commands

```bash
/mode creative     # Switch to creative mode
/mode rigorous     # Switch to rigorous mode
/agent chat        # Switch to chat agent
/agent analyse     # Switch to analysis agent
/help              # Show available commands
/exit              # Exit interface
```

## 📈 Example Output

### Creative Mode Results
```
╭─────────────────────── Discovery Results ────────────────────────────╮
│ Generated 5 perovskite candidates with formation energies:            │
│                                                                        │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)           │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                         │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                         │
│ 4. RbPbI₃ - Formation energy: -2.503 eV/atom                         │
│ 5. RbSnI₃ - Formation energy: -2.488 eV/atom                         │
│                                                                        │
│ CIF files created: CsGeI3.cif, CsPbI3.cif, CsSnI3.cif               │
╰────────────────────────────────────────────────────────────────────────╯
```

### Rigorous Mode Output
- Complete SMACT composition validation
- Multiple structure candidates per composition
- Professional analysis plots (XRD, RDF, coordination analysis)
- CIF file generation for all structures
- Publication-ready results

## 🔬 Scientific Integrity

CrystaLyse.AI maintains computational honesty:

- **100% Traceability**: Every result traces to actual tool calculations
- **Zero Fabrication**: No estimated or hallucinated numerical values
- **Complete Transparency**: Clear distinction between AI reasoning and computational validation
- **Anti-Hallucination System**: Response validation prevents fabricated results

## 🖥️ System Requirements

- Python 3.11+
- 8GB RAM minimum (16GB recommended)
- OpenAI API key
- Optional: NVIDIA GPU for MACE acceleration

## 🔧 Development Installation

For development or advanced usage:

```bash
# Clone repository
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI

# Create conda environment
conda create -n crystalyse python=3.11
conda activate crystalyse

# Install in development mode
pip install -e .
```

## 🤝 Acknowledgments

CrystaLyse.AI builds upon exceptional open-source tools:

- **SMACT**: Semiconducting Materials by Analogy and Chemical Theory
- **Chemeleon**: Crystal structure prediction with AI
- **MACE**: Machine learning ACE force fields
- **Pymatviz**: Materials visualisation toolkit
- **OpenAI Agents SDK**: Production-ready agent framework

## 📚 Citation

If you use CrystaLyse.AI in your research, please cite the underlying tools:

- **SMACT**: Davies et al., "SMACT: Semiconducting Materials by Analogy and Chemical Theory" JOSS 4, 1361 (2019)
- **Chemeleon**: Park et al., "Exploration of crystal chemical space using text-guided generative artificial intelligence" Nature Communications (2025)
- **MACE**: Batatia et al., "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields" NeurIPS (2022)
- **Pymatviz**: Riebesell et al., "Pymatviz: visualization toolkit for materials informatics" (2022)

## 📄 License

MIT License - see LICENSE for details.

## 🐛 Issues & Support

Report issues on [GitHub Issues](https://github.com/ryannduma/CrystaLyse.AI/issues)

## 🔗 Links

- [Homepage](https://github.com/ryannduma/CrystaLyse.AI)
- [Documentation](https://crystalyse-ai.readthedocs.io/)
- [Changelog](https://github.com/ryannduma/CrystaLyse.AI/blob/main/CHANGELOG.md)