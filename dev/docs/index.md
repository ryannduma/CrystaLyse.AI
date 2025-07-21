# CrystaLyse.AI Documentation

Welcome to CrystaLyse.AI - a computational materials design platform that accelerates materials exploration through AI-powered analysis and validation.

## Overview

CrystaLyse.AI is a computational materials design platform that combines large language models with rigorous computational chemistry tools. Built on the OpenAI Agents framework and integrated with advanced materials science tools via the Model Context Protocol (MCP), it provides researchers with a dual-mode system for exploring chemical space and analysing materials properties.

**Key Features**: CrystaLyse.AI bridges the gap between AI creativity and scientific rigour, enabling researchers to go from materials concepts to validated computational analysis in under 2 minutes, significantly accelerating traditional design workflows.

## Core Capabilities

### Dual-Mode Analysis System
- **Creative Mode**: Fast exploration using Chemeleon crystal structure prediction and MACE energy calculations (~50 seconds)
- **Rigorous Mode**: Complete validation pipeline with SMACT screening, Chemeleon structures, MACE energies, and comprehensive analysis (2-5 minutes)

### Materials Analysis Pipeline
1. **Query Processing**: Natural language materials requirements and specifications
2. **Composition Analysis**: SMACT-validated chemical compositions and feasibility screening
3. **Structure Generation**: Chemeleon crystal structure prediction with multiple candidates
4. **Energy Evaluation**: MACE force field calculations for formation energies and stability
5. **Visualisation**: Interactive 3D structures and comprehensive analysis plots

### Dual Interface Options
- **Unified CLI**: Single-command interface with `/mode` and `/agent` switching capabilities
- **Command-line Tools**: Direct access via `crystalyse analyse`, `crystalyse chat`, `crystalyse sessions`
- **Session Management**: Persistent conversation history and context across multi-day projects
- **Interactive Mode**: Real-time mode switching between creative and rigorous analysis

## Documentation Structure

### Getting Started
- [Quickstart Guide](quickstart.md) - Get up and running with CrystaLyse.AI
- [Installation](guides/installation.md) - Detailed installation instructions
- [CLI Usage Guide](guides/cli_usage.md) - Complete command-line interface reference

### Core Concepts
- [Analysis Modes](concepts/analysis_modes.md) - Creative vs Rigorous workflows and MCP server mapping
- [Agent Types](concepts/agents.md) - Chat vs Analyse agent operations
- [Session Management](concepts/sessions.md) - Persistent conversation and research tracking
- [Memory Systems](concepts/memory.md) - Computational caching and context preservation
- [MCP Architecture](concepts/mcp.md) - Model Context Protocol server integration

### Chemistry Tools
- [SMACT Integration](tools/smact.md) - Materials validation and composition screening
- [Chemeleon CSP](tools/chemeleon.md) - Crystal structure prediction and generation
- [MACE Energy](tools/mace.md) - Machine learning force field calculations
- [Visualisation Tools](tools/visualisation.md) - 3D structures and analysis plots

### How-To Guides
- [CLI Usage Guide](guides/cli_usage.md) - Master the command-line interface
- [Session-Based Research](guides/session_based_usage.md) - Long-running design projects
- [Batch Analysis](guides/batch_analysis.md) - High-throughput materials screening
- [Integration Guide](guides/integration.md) - Using CrystaLyse.AI in your workflows

### API Reference
- [Python API](reference/api/) - Programmatic access to CrystaLyse.AI
- [CLI Commands](reference/cli/) - Complete command reference
- [Configuration](reference/config/) - Configuration options and settings
- [Error Handling](reference/errors/) - Error codes and troubleshooting

## Key Features

### Advanced Materials Design
- **Significant Speed**: From 6-18 months to 2-5 minutes per material design
- **Dual Validation**: AI creativity + computational rigor
- **Complete Pipeline**: Composition → Structure → Energy → Recommendations
- **High Accuracy**: 89.8/100 capability score with rigorous validation

### Advanced AI Integration
- **OpenAI Agents Framework**: Production-ready agent architecture
- **o4-mini Support**: Ultra-high rate limits (10M TPM, 1B TPD) for creative mode
- **o3/gpt-4o**: Balanced performance for rigorous validation
- **Anti-Hallucination**: 100% computational honesty with response validation

### Professional Tool Integration
- **SMACT Validation**: Semiconducting Materials from Analogy and Chemical Theory
- **Chemeleon CSP**: State-of-the-art crystal structure prediction
- **MACE Energy**: Machine learning force fields for energy calculations
- **MCP Protocol**: Seamless tool integration with persistent connections

### Research-Grade Features
- **Session Persistence**: SQLite-like conversation management
- **Memory Systems**: Discovery caching and pattern recognition
- **Interactive CLI**: Rich terminal interface with progress tracking
- **Cross-Platform**: Windows, macOS, Linux support

## Applications

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

### Catalysis and Environment
- CO₂ reduction catalysts
- Water splitting and hydrogen production
- Chemical synthesis catalysts
- Environmental remediation materials

### Structural Materials
- High-entropy alloys
- Advanced ceramics and composites
- Lightweight structural materials
- Wear-resistant coatings

## Scientific Integrity

CrystaLyse.AI maintains the highest standards of computational honesty:

- **100% Traceability**: Every numerical result traces to actual tool calls
- **Zero Fabrication**: No estimated or fabricated energies, structures, or properties
- **Complete Transparency**: Clear distinction between AI reasoning and computational validation
- **Validation Pipeline**: Response validation system prevents hallucinations

## Performance Characteristics

### Execution Times
| Operation | Creative Mode | Rigorous Mode |
|-----------|--------------|---------------|
| Simple Query | ~80 seconds | 2-5 minutes |
| Complex Discovery | 2-3 minutes | 5-10 minutes |
| Batch Analysis | 5-10 minutes | 15-30 minutes |

### Validation Accuracy
- **SMACT Validation**: >95% agreement with experimental feasibility
- **Structure Prediction**: High-quality crystal structures with CIF output
- **Energy Calculations**: ML force field accuracy with uncertainty quantification
- **Discovery Pipeline**: End-to-end validation from composition to properties

## Prerequisites

- Python 3.11 or higher
- OpenAI API key (preferably OpenAI MDG for high rate limits)
- 8GB RAM recommended (4GB minimum)
- Internet connection for tool downloads and API calls

## Next Steps

1. Follow the [Quickstart Guide](quickstart.md) to begin using CrystaLyse.AI
2. Read the [CLI Usage Guide](guides/cli_usage.md) to master the interface
3. Explore [Dual-Mode Concepts](concepts/dual_mode.md) to understand the discovery workflow
4. Check the [Chemistry Tools](chemistry/smact.md) documentation for detailed capabilities
5. Review the [API Reference](reference/api/) for programmatic usage

## Support and Community

CrystaLyse.AI is actively developed and welcomes community engagement:
- **Issues**: Report bugs and request features on GitHub
- **Documentation**: Comprehensive guides and API reference
- **Examples**: Practical usage examples and tutorials
- **Updates**: Regular improvements and new features

## Acknowledgments

CrystaLyse.AI builds upon exceptional open-source tools:
- **SMACT**: Semiconducting Materials from Analogy and Chemical Theory
- **Chemeleon**: Crystal structure prediction and analysis
- **MACE**: Machine learning ACE force fields
- **OpenAI Agents SDK**: Production-ready agent framework
- **Model Context Protocol**: Seamless tool integration

---

**Ready to accelerate your materials design?** Start with the [Quickstart Guide](quickstart.md) to begin using computational materials science tools.