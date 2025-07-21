# API Reference

Complete reference documentation for CrystaLyse.AI's interfaces, commands, and configuration options.

## Overview

CrystaLyse.AI provides multiple interfaces for materials design and analysis:

- **Command Line Interface (CLI)**: Primary interface for interactive and batch analysis
- **Configuration System**: Flexible configuration for customising behaviour
- **Session Management**: Persistent conversation and research tracking
- **Error Handling**: Comprehensive error reporting and debugging

## Interface Reference

### [CLI Commands](cli/index.md)
Complete reference for all command-line interface commands:

- [`crystalyse analyse`](cli/analyse.md) - One-shot materials analysis
- [`crystalyse chat`](cli/chat.md) - Interactive session-based conversations
- [`crystalyse resume`](cli/resume.md) - Resume previous sessions
- [`crystalyse sessions`](cli/sessions.md) - Session management and listing
- [`crystalyse config`](cli/config.md) - Configuration management
- [`crystalyse demo`](cli/demo.md) - Demonstration and testing
- [Unified Interface](cli/unified.md) - Interactive mode with real-time switching

### [Configuration Reference](config/index.md)
Configuration options and settings:

- [Environment Variables](config/environment.md) - Environment-based configuration
- [Configuration Files](config/files.md) - YAML and JSON configuration files
- [MCP Server Configuration](config/mcp.md) - Model Context Protocol server settings
- [Performance Tuning](config/performance.md) - Optimisation settings

### [Error Reference](errors/index.md)
Error codes, messages, and troubleshooting:

- [Common Errors](errors/common.md) - Frequently encountered issues
- [API Errors](errors/api.md) - OpenAI API related errors
- [MCP Server Errors](errors/mcp.md) - Server connection and tool errors
- [Installation Errors](errors/installation.md) - Setup and dependency issues

## Quick Reference

### Essential Commands

```bash
# Basic analysis
crystalyse analyse "query" --mode [creative|rigorous]

# Interactive session
crystalyse chat -u username -s session_name -m mode

# Configuration
crystalyse config show
export OPENAI_API_KEY="sk-..."

# Session management
crystalyse sessions -u username
crystalyse resume session_name -u username
```

### Common Patterns

#### One-shot Analysis
```bash
# Creative mode (fast)
crystalyse analyse "Find battery cathode materials" --mode creative

# Rigorous mode (complete)
crystalyse analyse "Analyse LiCoO2 stability" --mode rigorous
```

#### Session-based Research
```bash
# Start new research session
crystalyse chat -u researcher -s battery_project -m rigorous

# Continue previous work
crystalyse resume battery_project -u researcher

# Review session history
crystalyse sessions -u researcher
```

#### Unified Interface
```bash
# Launch interactive interface
crystalyse

# In-session commands
/mode creative     # Switch to creative mode
/mode rigorous     # Switch to rigorous mode
/agent chat        # Switch to chat agent
/agent analyse     # Switch to analysis agent
/help              # Show commands
/exit              # Exit interface
```

## Response Formats

### Analysis Results

CrystaLyse.AI returns structured results in multiple formats:

#### Creative Mode Output
```
╭─────────────────────── Discovery Results ────────────────────────────╮
│ Generated 5 candidates with formation energies:                      │
│                                                                       │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)          │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                        │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                        │
│                                                                       │
│ 3D visualisations: CsGeI3_3dmol.html, CsPbI3_3dmol.html            │
╰───────────────────────────────────────────────────────────────────────╯
```

#### Rigorous Mode Output
```
╭──────────────────── Comprehensive Analysis Results ─────────────────────╮
│ SMACT Validation: 5 compositions validated, 3 passed screening          │
│                                                                          │
│ Structure Generation: 3 candidates per validated composition             │
│ Energy Ranking: Formation energies with uncertainty quantification      │
│                                                                          │
│ Analysis Suite Generated:                                                │
│ ├── XRD_Pattern_CsGeI3.pdf                                             │
│ ├── RDF_Analysis_CsGeI3.pdf                                            │
│ └── Coordination_Analysis_CsGeI3.pdf                                   │
╰──────────────────────────────────────────────────────────────────────────╯
```

### File Outputs

#### 3D Visualisations
- **Format**: Interactive HTML files
- **Naming**: `{formula}_3dmol.html`
- **Content**: 3D molecular viewer with controls

#### Analysis Plots (Rigorous Mode)
- **XRD Patterns**: `XRD_Pattern_{formula}.pdf`
- **RDF Analysis**: `RDF_Analysis_{formula}.pdf`  
- **Coordination Analysis**: `Coordination_Analysis_{formula}.pdf`
- **Structure Files**: `{formula}.cif`

## Analysis Modes

### Creative Mode
- **Purpose**: Fast exploration and ideation
- **Tools**: Chemeleon + MACE + Basic Visualisation
- **Speed**: ~50 seconds
- **Output**: Structure generation + energy ranking + 3D visualisation

### Rigorous Mode  
- **Purpose**: Complete validation and characterisation
- **Tools**: SMACT + Chemeleon + MACE + Comprehensive Analysis
- **Speed**: 2-5 minutes
- **Output**: Full validation pipeline + professional analysis plots

## Integration Patterns

### Workflow Integration

#### Research Pipeline
```bash
# 1. Initial exploration
crystalyse analyse "broad materials query" --mode creative

# 2. Focused investigation
crystalyse chat -m creative -s exploration_phase

# 3. Detailed validation
crystalyse analyse "specific material" --mode rigorous

# 4. Final characterisation
crystalyse chat -m rigorous -s validation_phase
```

#### Batch Processing
```bash
# Process multiple queries
for material in "LiCoO2" "LiFePO4" "LiMn2O4"; do
    crystalyse analyse "Analyse $material cathode properties" \
        --mode rigorous --user-id battery_study
done

# Review all results
crystalyse sessions -u battery_study
```

## Performance Characteristics

### Execution Times
| Operation | Creative Mode | Rigorous Mode |
|-----------|---------------|---------------|
| Simple query | ~50 seconds | 2-3 minutes |
| Complex analysis | 1-2 minutes | 3-5 minutes |
| Batch processing | 5-10 minutes | 15-30 minutes |

### Resource Requirements
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8GB | 16GB |
| CPU Cores | 2 | 4+ |
| Storage | 5GB | 10GB |
| GPU | Optional | NVIDIA (CUDA) |

## Version Information

This documentation covers CrystaLyse.AI v1.0.0 (Research Preview).

For specific version requirements and compatibility:
- Python 3.11+
- OpenAI API access
- Internet connection for tool downloads

## See Also

- [Installation Guide](../guides/installation.md) - Setup and installation
- [Quickstart Guide](../quickstart.md) - Getting started
- [CLI Usage Guide](../guides/cli_usage.md) - Comprehensive CLI examples
- [Tool Documentation](../tools/) - Individual tool references