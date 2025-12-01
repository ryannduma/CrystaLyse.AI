# CLI Usage Guide

Complete guide to using CrystaLyse.AI from the command line.

## Overview

CrystaLyse.AI provides a simple command-line interface with three primary commands:

1. **`crystalyse discover`** - Non-interactive materials discovery with provenance tracking
2. **`crystalyse chat`** - Interactive session-based chat with adaptive clarification
3. **`crystalyse user-stats`** - View user learning profile and preferences

## Installation

### From PyPI (Stable)

```bash
pip install crystalyse
export OPENAI_MDG_API_KEY="your-api-key-here"
crystalyse --help
```

### From Source (Development)

```bash
cd dev
pip install -e .
export OPENAI_MDG_API_KEY="your-api-key-here"
crystalyse --help
```

## Global Options

These options apply to all commands and must be specified before the command name:

```bash
crystalyse [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

**Available global options:**

```bash
--project, -p TEXT      Project name for workspace organisation (default: crystalyse_session)
--mode [creative|rigorous|adaptive]   Analysis mode (default: adaptive)
--model TEXT            Language model to use (default: auto-select based on mode)
--verbose, -v           Enable verbose output
--version               Show version and exit
--help                  Show help message
```

**Examples:**

```bash
# Use rigorous mode with custom project name
crystalyse --mode rigorous --project battery_study discover "Find Li-ion cathodes"

# Use specific model
crystalyse --model o3 discover "Analyse CsSnI3 stability"

# Verbose output for debugging
crystalyse --verbose discover "Quick test"
```

## Core Commands

### `crystalyse discover`

Non-interactive materials discovery with automatic provenance tracking. Ideal for scripting, automation, and quick explorations.

**Usage:**

```bash
crystalyse discover QUERY [OPTIONS]
```

**Options:**

```bash
--provenance-dir PATH   Custom directory for provenance output (default: ./provenance_output)
--hide-summary          Hide provenance summary table (data still captured)
```

**Provenance is always enabled** - every query generates a complete audit trail including:
- Materials discovered with computed properties
- MCP tool calls with timestamps
- Performance metrics
- Computational artefacts (structures, visualisations)

**Examples:**

```bash
# Basic discovery (creative mode, ~50 seconds)
crystalyse discover "Find stable perovskite solar cell materials"

# Rigorous mode for comprehensive analysis (2-5 minutes)
crystalyse --mode rigorous discover "Analyse CsSnI3 phase stability"

# Custom provenance directory
crystalyse discover "Li-ion cathodes" --provenance-dir ./my_research

# Hide summary for cleaner output
crystalyse discover "Quick test" --hide-summary

# Adaptive mode (automatically selects creative or rigorous)
crystalyse --mode adaptive discover "Design high-capacity battery materials"
```

**Expected output:**

```bash
$ crystalyse discover "Find perovskite solar cell materials"

[cyan]Starting non-interactive discovery:[/cyan] Find perovskite solar cell materials
[dim]Mode: adaptive | Project: crystalyse_session[/dim]

[Tool execution with progress bars...]

╭─────────────────────── Discovery Results ────────────────────────╮
│ Generated 3 perovskite candidates:                               │
│                                                                   │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)       │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                     │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                     │
│                                                                   │
│ Visualisations: CsGeI3_3dmol.html, CsPbI3_3dmol.html             │
╰───────────────────────────────────────────────────────────────────╯

╭─────────────────── Provenance Summary ───────────────────╮
│ Session: crystalyse_adaptive_20250101_120000             │
│ Materials discovered: 3                                  │
│ Tool calls: 2                                            │
│ Duration: 48.5s                                          │
│                                                          │
│ Output directory:                                        │
│ ./provenance_output/crystalyse_adaptive_20250101_120000 │
╰──────────────────────────────────────────────────────────╯
```

### `crystalyse chat`

Interactive session-based chat with adaptive clarification, user preference learning, and session persistence.

**Usage:**

```bash
crystalyse chat [OPTIONS]
```

**Options:**

```bash
--user, -u TEXT       User ID for personalised experience (default: "default")
--session, -s TEXT    Session name for organisation (auto-generated if not provided)
```

**Features:**

- **Adaptive clarification**: System learns your expertise level and adjusts question complexity
- **Cross-session learning**: Preferences persist across sessions
- **Mode switching**: Switch between creative/rigorous during conversation
- **Session persistence**: SQLite-based conversation storage

**Examples:**

```bash
# Start chat with user ID and session name
crystalyse chat --user researcher1 --session battery_study

# Quick anonymous chat
crystalyse chat

# Chat with global mode option
crystalyse --mode rigorous chat --user scientist --session photovoltaics
```

**In-session slash commands:**

The chat interface does not have built-in slash commands. It's a simple conversational interface where you ask questions naturally.

**Example session:**

```bash
$ crystalyse chat -u researcher -s solar_study

╭──────────────────────────────────────────────────────────╮
│         CrystaLyse.AI - Interactive Chat Session         │
│                                                          │
│ User: researcher                                         │
│ Session: solar_study                                     │
│ Mode: adaptive                                           │
╰──────────────────────────────────────────────────────────╯

You: Find perovskites for solar cells

[Agent processes query with adaptive clarification if needed...]

CrystaLyse: I've analysed several perovskite compositions for
photovoltaic applications. Here are the key findings:

Most Stable Candidates:
1. CsGeI₃: -2.558 eV/atom (excellent stability)
2. CsPbI₃: -2.542 eV/atom (good alternative)

3D visualisations saved for detailed inspection.

You: What about band gaps?

CrystaLyse: Based on the structures generated:

Band Gap Estimates:
- CsGeI₃: ~1.6 eV (excellent for single-junction solar cells)
- CsPbI₃: ~1.5 eV (good for photovoltaics)

These are preliminary estimates from structural analysis.

You: exit

[cyan]Session ended.[/cyan]
```

### `crystalyse user-stats`

Display user learning profile showing detected expertise, preferences, and interaction history.

**Usage:**

```bash
crystalyse user-stats [OPTIONS]
```

**Options:**

```bash
--user, -u TEXT    User ID to show stats for (default: "default")
```

**Example:**

```bash
$ crystalyse user-stats -u researcher1

╭─────────────────── CrystaLyse Learning Profile ───────────────────╮
│ User: researcher1                                                 │
│ Interactions: 15                                                  │
│ Detected Expertise: Expert                                        │
│ Speed Preference: Balanced (0.6)                                  │
│ Successful Modes: rigorous (90%), creative (70%)                  │
│                                                                   │
│ Domain Familiarity:                                               │
│   • Batteries: Expert (0.9)                                       │
│   • Photovoltaics: Intermediate (0.6)                             │
│   • Thermoelectrics: Novice (0.3)                                 │
╰───────────────────────────────────────────────────────────────────╯
```

### `crystalyse analyse-provenance`

Analyse provenance data from previous discovery sessions.

**Usage:**

```bash
crystalyse analyse-provenance [OPTIONS]
```

**Options:**

```bash
--session TEXT    Specific session ID to analyse
--latest          Analyse the most recent session
--dir PATH        Provenance directory to search (default: ./provenance_output)
```

**Examples:**

```bash
# Analyse most recent session
crystalyse analyse-provenance --latest

# Analyse specific session
crystalyse analyse-provenance --session crystalyse_creative_20250101_120000

# Custom provenance directory
crystalyse analyse-provenance --latest --dir ./my_research/provenance
```

## Analysis Modes

CrystaLyse.AI supports three operational modes that control the analysis workflow:

| Mode | Duration | Structures | Tools Used | Use Case |
|------|----------|-----------|------------|----------|
| **Creative** | ~50s | ~3 candidates | Chemeleon + MACE | Rapid exploration, broad screening |
| **Rigorous** | 2-5min | 30+ candidates | SMACT + Chemeleon + MACE + PyMatGen | Final validation, publication-ready |
| **Adaptive** | Variable | Context-dependent | Intelligent routing | Dynamic selection based on query |

**Mode selection:**

```bash
# Explicitly set mode
crystalyse --mode creative discover "Quick exploration"
crystalyse --mode rigorous discover "Thorough validation"
crystalyse --mode adaptive discover "Let system decide"  # Default
```

**Mode behaviour:**

- **Creative**: Fast screening using Chemeleon structure prediction + MACE energy calculations. Returns ~3 most promising candidates with basic visualisation.

- **Rigorous**: Comprehensive analysis using SMACT composition validation, Chemeleon structure generation, MACE calculations, and PyMatGen phase diagram analysis. Returns 30+ candidates with full characterisation.

- **Adaptive**: Analyses query complexity and automatically routes to creative or rigorous mode. High-specificity queries → rigorous; exploratory queries → creative.

## Environment Variables

Configure CrystaLyse.AI behaviour through environment variables:

```bash
# Required
export OPENAI_MDG_API_KEY="your-key-here"

# Optional
export CRYSTALYSE_MODEL="o4-mini"              # Default model
export CRYSTALYSE_PYTHON_PATH="/path/to/python" # Python for MCP servers
export CRYSTALYSE_DEBUG="false"                # Debug mode
export CRYSTALYSE_ENABLE_HTML_VIZ="false"      # HTML visualisation
export CRYSTALYSE_PPD_PATH="/path/to/ppd.pkl"  # Custom phase diagram path
export CHEMELEON_CHECKPOINT_DIR="/path/to/ckpts" # Custom checkpoint directory
```

## Configuration File

Create `~/.crystalyse/config.yaml` for persistent settings:

```yaml
# Model configuration
default_model: "o4-mini"

# MCP server paths (auto-configured for standard installations)
mcp_servers:
  chemistry_unified:
    command: "python"
    args: ["-m", "chemistry_unified.server"]
    cwd: "/path/to/chemistry-unified-server/src"

  chemistry_creative:
    command: "python"
    args: ["-m", "chemistry_creative.server"]
    cwd: "/path/to/chemistry-creative-server/src"

  visualization:
    command: "python"
    args: ["-m", "visualization_mcp.server"]
    cwd: "/path/to/visualization-mcp-server/src"

# Provenance settings
provenance:
  enabled: true  # Always enabled, cannot be disabled
  output_dir: "./provenance_output"
  show_summary: true

# Performance tuning
timeouts:
  creative: 120
  adaptive: 180
  rigorous: 300
```

## First Run Auto-Downloads

On first execution, CrystaLyse automatically downloads required data:

**Chemeleon Model Checkpoints** (~600 MB):
- Downloaded to `~/.cache/crystalyse/chemeleon_checkpoints/`
- One-time download, cached permanently
- No manual setup required

**Materials Project Phase Diagrams** (~170 MB, 271,617 entries):
- Auto-located from multiple fallback paths
- Used for energy-above-hull calculations
- Requires `ppd-mp_all_entries_uncorrected_250409.pkl.gz`

Progress bars show download status. Files are never re-downloaded.

## Troubleshooting

### Command not found

```bash
$ crystalyse: command not found

# Solution: Check installation
pip install -e .  # From dev/ directory
# or
pip install crystalyse
```

### API key errors

```bash
$ Error: OpenAI API key not found

# Solution: Set environment variable
export OPENAI_MDG_API_KEY="your-key-here"

# Verify
echo $OPENAI_MDG_API_KEY
```

### MCP server connection errors

```bash
$ Error: Chemistry server connection failed

# Check Python path
which python

# Set if using conda/venv
export CRYSTALYSE_PYTHON_PATH="/path/to/your/python"

# Verify installation
pip list | grep crystalyse
pip list | grep chemistry
```

### Session database issues

```bash
$ Error: Cannot access session database

# Check permissions
ls -la ~/.crystalyse/conversations.db

# Reset if corrupted
rm ~/.crystalyse/conversations.db
crystalyse chat  # Creates fresh database
```

## Best Practices

### Query optimisation

```bash
# Good: Specific and actionable
crystalyse discover "Find stable perovskites with band gaps 1.2-1.6 eV"

# Better: Include application context
crystalyse discover "Design lead-free perovskite solar cell materials"

# Best: Specify requirements and constraints
crystalyse --mode rigorous discover "Find environmentally friendly perovskite alternatives to MAPbI3 for tandem solar cells"
```

### Workflow recommendations

1. **Start with creative mode** for rapid exploration
2. **Iterate** based on initial results
3. **Validate with rigorous mode** for publication-quality analysis
4. **Use sessions** for complex multi-part investigations
5. **Check provenance** to verify computational integrity

### Session management

```bash
# Use descriptive session names
crystalyse chat -s battery_cathode_screening_2025 -u researcher

# Organise by project
crystalyse chat -s project_solar_perovskites -u team_lead
crystalyse chat -s project_battery_anodes -u team_lead
```

### Integration with research workflows

**Shell scripting:**

```bash
#!/bin/bash
# Automated materials screening

export OPENAI_MDG_API_KEY="your-key"

for material in "LiCoO2" "LiFePO4" "LiMn2O4"; do
    echo "Analysing $material..."
    crystalyse --mode rigorous discover "Analyse $material cathode properties" \
        --provenance-dir ./screening_results/$material
done
```

**Python integration:**

```python
import subprocess

def discover_material(formula, mode="creative"):
    """Run CrystaLyse discovery from Python."""
    cmd = [
        "crystalyse",
        "--mode", mode,
        "discover",
        f"Analyse {formula} properties"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

# Use in pipeline
materials = ["CsSnI3", "CsPbI3", "CsGeI3"]
for material in materials:
    analysis = discover_material(material, mode="rigorous")
    print(f"Analysis of {material}:\n{analysis}\n")
```

## Performance Optimisation

**GPU acceleration:**

```bash
# Check GPU availability
nvidia-smi

# MACE automatically uses GPU if available
# Monitor during analysis
watch -n 1 nvidia-smi
```

**Memory management:**

```bash
# Monitor memory
htop

# Use creative mode for lower memory usage
crystalyse --mode creative discover "query"
```

**Disk space:**

```bash
# Check available space
df -h

# Clean old provenance data
find ./provenance_output -type d -mtime +30 -exec rm -rf {} +

# Clean visualisations
find . -name "*_3dmol.html" -mtime +7 -delete
```

This CLI guide reflects the actual implementation in CrystaLyse.AI v1.0.0. For API-level integration, see the reference documentation.
