# API Reference

Complete reference documentation for Crystalyse's interfaces, commands, and configuration options.

## Overview

Crystalyse provides multiple interfaces for materials design and analysis:

- **Command Line Interface (CLI)**: Primary interface for interactive and batch analysis
- **Model Registry**: Named backbones across OpenAI, Anthropic, OpenRouter, Mistral and local servers
- **Configuration System**: `.crystalyse/config.toml` plus `CRYSTALYSE_*` environment variables
- **Conversation Memory**: Chat history persisted per project, session and mode
- **Error Handling**: Tool-level retry and fallback, plus fail-fast validation of model overrides

## Interface Reference

### [CLI Commands](cli/index.md)
Complete reference for all command-line interface commands:

- `crystalyse discover QUERY` - Non-interactive, single-shot materials discovery
- `crystalyse chat` - Interactive chat session (also the default when no command is given)
- `crystalyse setup` - Download the phase-diagram data files
- `crystalyse analyse-provenance` - Inspect provenance from previous runs
- `crystalyse models list` - Show the effective model registry
- `crystalyse models check` - Validate the API-key environment variables

Global options (`--project`, `--mode`, `--model`, `--verbose`, `--version`) belong *before* the
command: `crystalyse --mode validate discover "query"`.

### [Configuration Reference](config/index.md)
Configuration options and settings:

- `.crystalyse/config.toml` - project settings, with `~/.crystalyse/config.toml` as the user layer
- `[models.<name>]` tables - override a built-in registry entry or define a new backbone
- API keys - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`
  (real environment variables; the codebase has no `.env` support)
- `CRYSTALYSE_*` variables - provenance, render gate, MCP interpreter and data-path overrides

### [Error Reference](errors/index.md)
Error codes, messages, and troubleshooting:

- Exit codes - Crystalyse itself produces only `0` and `1`; `2` comes from Click's usage handling
- Exception types - `CrystaLyseToolError` and its subclasses, plus `ModelOverrideError` for an
  invalid `[models.*]` table
- Automatic recovery - the `with_retry` decorator and `FallbackChain`

## Quick Reference

### Essential Commands

```bash
# Basic analysis
crystalyse discover "query" --mode [explore|validate|auto]

# Interactive session
crystalyse chat -u username -s session_name

# Mode and model are global options - they precede the command
crystalyse --mode validate --model anthropic_claude_opus chat

# Model selection
crystalyse models list      # every backbone, its backend, and whether its key is set
crystalyse models check     # exits 1 if any required API key is missing

# One-time data download (phase diagrams)
crystalyse setup

# Configuration
export OPENAI_API_KEY="..."
```

### Common Patterns

#### One-shot Analysis
```bash
# Explore mode (fast)
crystalyse discover "Find battery cathode materials" --mode explore

# Validate mode (complete)
crystalyse discover "Analyse LiCoO2 stability" --mode validate
```

#### Session-based Research
```bash
# Start work in a named project and session
crystalyse -p battery_project chat -u researcher -s cathodes

# Continue previous work: the same project, session and mode reuse the same
# conversation memory in ~/.crystalyse/sessions/<project>_<session>_<mode>.db
crystalyse -p battery_project chat -u researcher -s cathodes
```

#### Unified Interface
```bash
# Launch interactive interface (no command given defaults to chat)
crystalyse

# In-session commands
/mode validate     # Switch mode (explore | validate | auto)
/model openai_o3   # Switch backbone (any name from `crystalyse models list`)
/tools             # List MCP tools
/mcp               # MCP server status
/stats             # Session statistics
/memory            # Show, clear or refresh conversation memory
/about             # Version and system information
/help              # Show commands
/clear             # Clear screen
/exit              # Exit interface
```

## Response Formats

### Analysis Results

Crystalyse returns structured results in multiple formats:

#### Explore Mode Output
```
╭─────────────────────── Discovery Results ────────────────────────────╮
│ Generated 5 candidates with formation energies:                      │
│                                                                       │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)          │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                        │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                        │
│                                                                       │
│ Structure files: CsGeI3.cif, CsPbI3.cif                             │
╰───────────────────────────────────────────────────────────────────────╯
```

#### Validate Mode Output
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

#### Structure Files
- **Format**: CIF text files
- **Naming**: `{formula}.cif`
- **Note**: the visualisation tool writes the CIF only - 3dmol.js HTML output is disabled, and
  the tool result reports `"type": "cif_file"`

#### Analysis Plots (Validate Mode)
- **Location**: `{output_dir}/{formula}_analysis/`
- **XRD Patterns**: `XRD_Pattern_{formula}.pdf`
- **RDF Analysis**: `RDF_Analysis_{formula}.pdf`
- **Coordination Analysis**: `Coordination_Analysis_{formula}.pdf`
- **Structure Files**: `{formula}.cif`

## Analysis Modes

Canonical mode names are `explore`, `validate` and `auto`. The legacy names `creative`,
`rigorous` and `adaptive` still resolve to them but emit a `DeprecationWarning` and are slated
for removal in v2.0.

### Explore Mode
- **Purpose**: Fast exploration and ideation
- **MCP server**: `chemistry_creative`
- **Default model**: `openai_o4_mini`
- **Timeout**: 120 s
- **Output**: Structure generation + energy ranking + CIF files

### Validate Mode
- **Purpose**: Complete validation and characterisation
- **MCP server**: `chemistry_unified`
- **Default model**: `openai_o3`
- **Timeout**: 300 s
- **Output**: Full validation pipeline + pymatviz analysis plots

### Auto Mode (CLI default)
- **Purpose**: Balanced runs with intelligent tool selection
- **MCP server**: `chemistry_unified`
- **Default model**: `openai_o4_mini`
- **Timeout**: 180 s

## Integration Patterns

### Workflow Integration

#### Research Pipeline
```bash
# 1. Initial exploration
crystalyse discover "broad materials query" --mode explore

# 2. Focused investigation
crystalyse --mode explore chat -s exploration_phase

# 3. Detailed validation
crystalyse discover "specific material" --mode validate

# 4. Final characterisation
crystalyse --mode validate chat -s validation_phase
```

#### Batch Processing
```bash
# Process multiple queries
for material in "LiCoO2" "LiFePO4" "LiMn2O4"; do
    crystalyse discover "Analyse $material cathode properties" \
        --mode validate --project battery_study
done

# Review the provenance captured along the way
crystalyse analyse-provenance --latest
```

## Performance Characteristics

### Mode Timeouts

Each mode has a hard-coded agent timeout - these are budgets, not typical runtimes:

| Mode | Timeout | MCP server |
|------|---------|------------|
| explore | 120 s | `chemistry_creative` |
| auto | 180 s | `chemistry_unified` |
| validate | 300 s | `chemistry_unified` |

### Resource Requirements
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8GB | 16GB |
| CPU Cores | 2 | 4+ |
| Storage | 5GB | 10GB |
| GPU | Optional | NVIDIA (CUDA) |

## Version Information

This documentation covers Crystalyse v1.0.0-dev (`crystalyse --version` prints
`Crystalyse v1.0.0-dev`).

For specific version requirements and compatibility:
- Python 3.12 (what the project is developed and tested on; the code uses 3.11+ features such as
  `tomllib` and `StrEnum`)
- An API key for whichever backbone you select - `OPENAI_API_KEY` for the OpenAI-backed defaults,
  `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` or `MISTRAL_API_KEY` for the other providers, and no
  key at all for the local Ollama entry
- Internet connection for the first-run data downloads (Chemeleon checkpoints and phase-diagram
  data)

## See Also

- [Installation Guide](../guides/installation.md) - Setup and installation
- [Quickstart Guide](../quickstart.md) - Getting started
- [CLI Usage Guide](../guides/cli_usage.md) - Comprehensive CLI examples
