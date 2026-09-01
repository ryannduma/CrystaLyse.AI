# Crystalyse Documentation

Welcome to Crystalyse - a computational materials design platform that accelerates materials exploration through AI-powered analysis and validation.

## Overview

Crystalyse is a computational materials design platform that combines large language models with rigorous computational chemistry tools. Built on the OpenAI Agents framework and integrated with advanced materials science tools via the Model Context Protocol (MCP), it gives researchers a mode-driven system for exploring chemical space and analysing materials properties.

**Key Features**: Crystalyse bridges the gap between AI creativity and scientific rigour, taking researchers from materials concepts to validated computational analysis in a single conversation.

## Core Capabilities

### Three Analysis Modes

Modes are defined in `crystalyse/config/modes.py`; each selects an MCP server and a timeout
budget.

| Mode | MCP Server | Tools | Timeout budget |
|------|-----------|-------|----------------|
| `explore` | `chemistry_creative` | Chemeleon + MACE (no SMACT, for speed) | 120 s |
| `validate` | `chemistry_unified` | Full pipeline: SMACT, Chemeleon, MACE, PyMatgen | 300 s |
| `auto` | `chemistry_unified` | Full pipeline, balanced budget - **the CLI default** | 180 s |

The timeouts are budgets the agent runs within, not measured runtimes. The legacy names
`creative`, `rigorous` and `adaptive` still resolve to `explore`, `validate` and `auto`,
emitting a `DeprecationWarning`; they are slated for removal in v2.0.

### Materials Analysis Pipeline
1. **Query Processing**: Natural language materials requirements and specifications
2. **Composition Analysis**: SMACT-validated chemical compositions and feasibility screening
3. **Structure Generation**: Chemeleon crystal structure prediction with multiple candidates
4. **Energy Evaluation**: MACE force field calculations for formation energies and stability
5. **Visualisation**: CIF export plus analysis plots (3D structure, XRD, RDF, coordination) as PDFs

### Interface Options
- **Command-line Tools**: `crystalyse discover` (single-shot query), `crystalyse setup`
  (download the phase-diagram dataset), `crystalyse chat` (interactive session),
  `crystalyse analyse-provenance` (read back a past session's audit trail), and the
  `crystalyse models` group (`list`, `check`)
- **Global Options**: `--mode`, `--model`, `--project`, placed *before* the subcommand
- **Interactive Slash Commands**: `/help`, `/tools`, `/mcp`, `/stats`, `/memory`, `/mode`,
  `/model`, `/about`, `/clear`, `/quit`, `/exit` - so mode and model can both be switched
  mid-session
- **Session Management**: Persistent conversation history and context across multi-day projects

## Documentation Structure

### Getting Started
- [Quickstart Guide](quickstart.md) - Get up and running with Crystalyse
- [Installation](guides/installation.md) - Detailed installation instructions
- [CLI Usage Guide](guides/cli_usage.md) - Complete command-line interface reference

### Core Concepts
- [Analysis Modes](concepts/analysis_modes.md) - explore, validate and auto workflows and MCP server mapping
- [Agent Types](concepts/agents.md) - Chat vs Analyse agent operations
- [Session Management](concepts/sessions.md) - Persistent conversation and research tracking
- [Memory Systems](concepts/memory.md) - Computational caching and context preservation (Experimental Preview)


### Chemistry Tools
- [SMACT Integration](tools/smact.md) - Materials validation and composition screening
- [Chemeleon CSP](tools/chemeleon.md) - Crystal structure prediction and generation
- [MACE Energy](tools/mace.md) - Machine learning force field calculations
- [Visualisation Tools](tools/visualisation.md) - CIF export and analysis plots

### How-To Guides
- [CLI Usage Guide](guides/cli_usage.md) - Master the command-line interface
- [Session-Based Research](guides/session_based_usage.md) - Long-running design projects


### API Reference
- [Python API](reference/index.md) - Programmatic access to Crystalyse
- [CLI Commands](reference/cli/index.md) - Complete command reference
- [Configuration](reference/config/index.md) - Configuration options and settings
- [Error Handling](reference/errors/index.md) - Error codes and troubleshooting

## Key Features

### Advanced Materials Design
- **Significant Speed**: minutes of computation in place of months of experimental iteration
- **Dual Validation**: AI creativity + computational rigour
- **Complete Pipeline**: Composition → Structure → Energy → Recommendations
- **Full Provenance**: every `discover` query writes a complete audit trail

### Multi-Provider Model Support
- **Model Registry**: named backbones in `crystalyse/config/models.py`, each a `ModelConfig`
  carrying `backend`, `model_id`, `api_key_env_var`, `context_window`, `reasoning_effort`,
  `thinking_budget_tokens` and `supported_modes`
- **Backends**: `openai`, `litellm` and `openai-compat`, covering OpenAI (`openai_o4_mini`,
  `openai_o3`, `openai_gpt4o_mini`), Anthropic (`anthropic_claude_opus`,
  `anthropic_claude_sonnet`, `anthropic_claude_haiku`), OpenRouter
  (`openrouter_claude_opus`, `openrouter_llama3_70b`), Mistral (`mistral_large`) and a
  local Ollama endpoint (`ollama_llama3_70b_direct`)
- **Per-Mode Defaults**: explore and auto use `openai_o4_mini`; validate uses `openai_o3`
- **Selection**: the global `--model` flag, `/model` mid-session, or `default_model` in
  `.crystalyse/config.toml`
- **Inspection**: `crystalyse models list` prints the effective registry (Name, Backend,
  Model ID, Context, Modes, Env Var, Source, Usable); `crystalyse models check` validates
  the required API keys and exits non-zero if any are missing
- **Reasoning Effort**: declared on the registry entry and forwarded to the provider in its
  own wire format
- **Configuration File**: `.crystalyse/config.toml` in the project overrides
  `~/.crystalyse/config.toml`; `[models.<name>]` tables may override the value-like fields
  of a built-in entry or define a new one
- **OpenAI Agents Framework**: Production-ready agent architecture
- **Anti-Hallucination**: computational honesty enforced by response validation

### Professional Tool Integration
- **SMACT Validation**: Semiconducting Materials from Analogy and Chemical Theory
- **Chemeleon CSP**: State-of-the-art crystal structure prediction
- **MACE Energy**: Machine learning force fields for energy calculations
- **MCP Protocol**: Seamless tool integration with persistent connections

### Research-Grade Features
- **Session Persistence**: SQLite conversation storage via the OpenAI Agents SDK's
  `SQLiteSession`, at `~/.crystalyse/sessions/{project_name}_{mode}.db`
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

Crystalyse maintains the highest standards of computational honesty:

- **Traceability**: Every numerical result traces to an actual tool call, recorded in the
  provenance trail
- **Zero Fabrication**: No estimated or fabricated energies, structures, or properties
- **Complete Transparency**: Clear distinction between AI reasoning and computational validation
- **Validation Pipeline**: Response validation system prevents hallucinations

## Performance Characteristics

### Timeout Budgets
Crystalyse contains no timing benchmark, so no measured execution times are quoted here.
What the code does define is a per-mode timeout budget:

| Mode | Budget |
|------|--------|
| `explore` | 120 s |
| `auto` | 180 s |
| `validate` | 300 s |

Actual runtime depends on the query, the model backbone, and whether a GPU is available for
Chemeleon and MACE.

### What Is Validated
- **SMACT Validation**: charge neutrality, Pauling electronegativity, oxidation-state
  consistency against a chosen dataset - a boolean verdict per composition
- **Structure Prediction**: crystal structures from a diffusion model, exported as CIF
- **Energy Calculations**: MACE-MP formation energies, with residual forces reported. No
  uncertainty is quantified
- **Discovery Pipeline**: end-to-end from composition to properties, with a full provenance
  trail

## Prerequisites

- Python 3.12 is what the project is developed and tested on
- An API key for whichever backbone you use, set as a **real environment variable**:
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` or `MISTRAL_API_KEY`. There
  is **no `.env` file support** anywhere in the codebase. On zsh, put exports in
  `~/.zshenv` rather than `~/.zshrc` so non-interactive shells see them too. Run
  `crystalyse models check` to confirm what is visible
- 8GB RAM recommended (4GB minimum)
- Internet connection for API calls and first-run downloads:
  - Chemeleon checkpoints from Figshare, a 523 MB archive expanding to ~604 MB in
    `~/.cache/crystalyse/chemeleon_checkpoints/`
  - Phase-diagram data (~178 MB, 271617 entries) in `~/.cache/crystalyse/` - fetch it ahead
    of time with `crystalyse setup`
  - MACE foundation models, cached by mace-torch in `~/.cache/mace/`

> **Note on packaging metadata**: `pyproject.toml` declares
> `requires-python = ">=3.9"`, which is wrong - the code uses 3.11+ features such as
> `StrEnum`. Treat 3.12 as the supported version regardless of what the metadata says.

## Next Steps

1. Follow the [Quickstart Guide](quickstart.md) to begin using Crystalyse
2. Read the [CLI Usage Guide](guides/cli_usage.md) to master the interface
3. Explore [Analysis Modes](concepts/analysis_modes.md) to understand the discovery workflow
4. Check the [SMACT Integration](tools/smact.md) documentation for detailed capabilities
5. Review the [Python API](reference/index.md) for programmatic usage

## Support and Community

Crystalyse is actively developed and welcomes community engagement:
- **Issues**: Report bugs and request features on GitHub
- **Documentation**: Comprehensive guides and API reference
- **Examples**: Practical usage examples and tutorials
- **Updates**: Regular improvements and new features

## Acknowledgments

Crystalyse builds upon exceptional open-source tools:
- **SMACT**: Semiconducting Materials from Analogy and Chemical Theory
- **Chemeleon**: Crystal structure prediction and analysis
- **MACE**: Machine learning ACE force fields
- **OpenAI Agents SDK**: Production-ready agent framework
- **Model Context Protocol**: Seamless tool integration

---

**Ready to accelerate your materials design?** Start with the [Quickstart Guide](quickstart.md) to begin using computational materials science tools.