# CLI Usage Guide

Complete guide to using Crystalyse from the command line.

## Overview

Crystalyse provides a small command-line interface built around these commands:

1. **`crystalyse discover`** - Non-interactive materials discovery with provenance tracking
2. **`crystalyse chat`** - Interactive chat session with per-session conversation memory
3. **`crystalyse setup`** - Download and prepare the required data files
4. **`crystalyse models`** - Inspect (`models list`) and validate (`models check`) the model registry
5. **`crystalyse analyse-provenance`** - Analyse provenance data from previous discovery sessions

Running `crystalyse` with no arguments starts `chat`.

## Installation

### From Source

The package in this repository is version `1.0.0-dev` and is installed from source:

```bash
cd dev
pip install -e .
export OPENAI_API_KEY="your-api-key-here"
crystalyse --help
```

The install provides the `crystalyse` console script (`crystalyse.cli:main`).
Crystalyse is developed and tested on Python 3.12.

API keys must be **real environment variables** - there is no `.env` file
support in the codebase. On zsh, put the exports in `~/.zshenv` rather than
`~/.zshrc` so non-interactive shells see them too.

## Global Options

These options apply to all commands and must be specified before the command name:

```bash
crystalyse [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

**Available global options:**

```bash
--project, -p TEXT      Project name for workspace organisation (default: crystalyse_session)
--mode TEXT             Agent operating mode: explore, validate, auto (default: auto)
--model TEXT            Language model to use (default: the mode's default model)
--verbose, -v           Enable verbose output
--version               Show version and exit
--help                  Show help message
```

`--mode` is a plain string, not a fixed choice list. The canonical names are
`explore`, `validate` and `auto`. The old names `creative`, `rigorous` and
`adaptive` still resolve to `explore`, `validate` and `auto` respectively, but
they emit a `DeprecationWarning` and are slated for removal in v2.0.

**Examples:**

```bash
# Use validate mode with a custom project name
crystalyse --mode validate --project battery_study discover "Find Li-ion cathodes"

# Use a specific model from the registry
crystalyse --model openai_o3 discover "Analyse CsSnI3 stability"

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
--mode TEXT             Agent operating mode (overrides global option)
--project, -p TEXT      Project name (overrides global option)
```

**Provenance is always enabled** - every query generates a complete audit trail including:
- Materials discovered with computed properties
- MCP tool calls with timestamps
- Performance metrics
- Computational artefacts (structures, visualisations)

**Examples:**

```bash
# Basic discovery (auto mode by default)
crystalyse discover "Find stable perovskite solar cell materials"

# Validate mode for comprehensive analysis
crystalyse --mode validate discover "Analyse CsSnI3 phase stability"

# Custom provenance directory
crystalyse discover "Li-ion cathodes" --provenance-dir ./my_research

# Hide summary for cleaner output
crystalyse discover "Quick test" --hide-summary

# Explore mode for a fast first pass
crystalyse --mode explore discover "Design high-capacity battery materials"

# The command-level --mode overrides the global one
crystalyse --mode validate discover "Quick check" --mode explore
```

**Expected output:**

```bash
$ crystalyse discover "Find perovskite solar cell materials"

Starting non-interactive discovery: Find perovskite solar cell materials
Mode: auto | Project: crystalyse_session

[Tool execution with live trace output...]

╭─────────────────────── Discovery Report ─────────────────────────╮
│ Generated 3 perovskite candidates:                               │
│                                                                  │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)       │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                     │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                     │
╰──────────────────────────────────────────────────────────────────╯

                       Provenance Summary
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric           ┃ Value                                        ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Session ID       │ crystalyse_auto_20250101_120000              │
│ Materials Found  │ 3                                            │
│ With Energy Data │ 3                                            │
│ Energy Range     │ -2.558 to -2.529 eV/atom                     │
│ Runtime          │ 48.5s                                        │
│ MCP Tools Used   │ chemistry_unified, visualization             │
│ Output Location  │ provenance_output/runs/crystalyse_auto_2025… │
└──────────────────┴──────────────────────────────────────────────┘
```

Session IDs are formed as `crystalyse_<mode>_<timestamp>` using the canonical
mode name, and each run is written to `<provenance-dir>/runs/<session_id>/`.

### `crystalyse chat`

Interactive chat session with slash commands, live tool tracing, and per-session conversation memory.

**Usage:**

```bash
crystalyse chat [OPTIONS]
```

**Options:**

```bash
--user, -u TEXT       User ID recorded for the session (default: "default")
--session, -s TEXT    Session name appended to the project name
```

Mode and model are **global** options, so they go before `chat`:

```bash
crystalyse --mode validate --model openai_o3 chat -u scientist -s photovoltaics
```

**What a session actually persists:**

- **Conversation memory**: the SDK's `SQLiteSession`, stored per session ID at
  `~/.crystalyse/sessions/<session_id>.db`, where the session ID is
  `<project_name>_<mode>`. `--session` is appended to the project name
  (`<project>_<session>`); nothing is auto-generated. Resuming the same
  conversation therefore needs the same `--project`, the same `--session` and
  the same mode.
- **In-process history**: the turns shown on screen are also passed to the
  agent as conversation history for the current run.

The `--user` value is recorded on the chat session but is not part of the
database key, and no user preferences or expertise profiles are stored.

**Examples:**

```bash
# Start chat with a user ID and session name
crystalyse chat --user researcher1 --session battery_study

# Quick anonymous chat (equivalent to running `crystalyse` with no arguments)
crystalyse chat

# Chat in validate mode
crystalyse --mode validate chat --user scientist --session photovoltaics
```

**In-session slash commands:**

| Command | Description |
|---------|-------------|
| `/help` | Show the command table |
| `/tools` | Reference table of the chemistry and visualisation tools (arguments: `desc`, `nodesc`) |
| `/mcp` | Reference table and descriptions of the MCP servers (arguments: `status`, `servers`, `desc`) |
| `/stats` | Session duration and configuration summary |
| `/memory` | Inspect (`show`), wipe (`clear`) or refresh conversation memory |
| `/mode` | View (`show`) or change the operating mode (`explore`, `validate`, `auto`) |
| `/model` | View (`show`) or change the language model (any registry name) |
| `/about` | Version and system information |
| `/clear` | Clear the terminal screen |
| `/quit`, `/exit` | Exit the session |

`/mode` and `/model` recreate the agent in place, so the change takes effect
from the next query onward. `/memory clear` asks for confirmation, then deletes
and recreates the session database (including its `-shm`/`-wal` siblings).
Unrecognised slash input prints `Unknown command` and points you at `/help`.
`/tools`, `/mcp` and `/stats` print static reference tables rather than live
introspection of the running servers; `/memory show` does read the real session
database (its ID and size on disk).

**Example session:**

```bash
$ crystalyse chat -u researcher -s solar_study

 ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗
 ...responsive CRYSTALYSE logo...

╭──────────────────────────────────────────────────────────────────╮
│      Your interactive materials science research partner.        │
│      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                    │
│  Type your query to begin, /help for commands, or 'quit' to exit.│
╰──────────────────────────────────────────────────────────────────╯

➤ Find perovskites for solar cells

╭─────────────────────────── You ──────────────────────────────────╮
│ Find perovskites for solar cells                                 │
╰──────────────────────────────────────────────────────────────────╯

[Tool execution with live trace output...]

╭───────────────────────── CrystaLyse ─────────────────────────────╮
│ I've analysed several perovskite compositions for photovoltaic   │
│ applications. Most stable candidates:                            │
│                                                                  │
│ 1. CsGeI₃: -2.558 eV/atom                                        │
│ 2. CsPbI₃: -2.542 eV/atom                                        │
╰──────────────────────────────────────────────────────────────────╯

➤ quit

Thank you for using Crystalyse! Goodbye.
```

### `crystalyse setup`

Download and prepare the phase-diagram data used for energy-above-hull
calculations. Exits with a non-zero status if the download or verification
fails.

**Usage:**

```bash
crystalyse setup [OPTIONS]
```

**Options:**

```bash
--force, -f    Force re-download of data files
```

```bash
$ crystalyse setup
Setting up Crystalyse data files...
✓ Phase diagram data ready at: /Users/you/.cache/crystalyse/ppd-mp_all_entries_uncorrected_250409.pkl.gz
```

### `crystalyse models`

Inspect and validate the available model backbones. Running `crystalyse models`
with no subcommand prints the group's help.

**`crystalyse models list`** prints the *effective* registry - the built-in
entries plus anything added or overridden in `.crystalyse/config.toml` - as a
table with the columns **Name**, **Backend**, **Model ID**, **Context**,
**Modes**, **Env Var**, **Source** and **Usable**. `Source` reports where the
entry came from (`built-in`, `user-override` for a built-in with config-supplied
fields, or `user-defined` for an entry that exists only in config). `Usable`
shows whether the entry's API-key environment variable is currently set;
entries that need no key (local Ollama) are always usable.

**`crystalyse models check`** prints a per-model key status line and exits with
code `1` if any model that requires a key is missing it. Note that `check`
iterates the built-in registry only, so entries defined purely in
`config.toml` appear in `list` but not in `check`.

```bash
# See every backbone and where it came from
crystalyse models list

# Verify API keys; useful as a CI or shell-script pre-flight check
crystalyse models check
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

Sessions are read from `<dir>/runs`. With neither `--latest` nor `--session`,
the command lists the 10 most recent sessions and asks you to pick one. If
`<dir>/runs` does not exist it reports `Provenance directory not found`.

**Examples:**

```bash
# List the most recent sessions
crystalyse analyse-provenance

# Analyse most recent session
crystalyse analyse-provenance --latest

# Analyse specific session
crystalyse analyse-provenance --session crystalyse_validate_20250101_120000

# Custom provenance directory
crystalyse analyse-provenance --latest --dir ./my_research/provenance
```

## Analysis Modes

Crystalyse supports three operational modes. The selected mode is passed through
unchanged - it chooses the chemistry MCP server, sets the run timeout, and is
injected into the agent's instructions so every analysis tool receives the same
`mode` argument. Nothing inspects the query and re-selects a mode on your behalf.

| Mode | Chemistry MCP server | Timeout | Intent |
|------|----------------------|---------|--------|
| **explore** | `chemistry_creative` | 120 s | Rapid exploration and broad screening |
| **auto** | `chemistry_unified` | 180 s | Balanced default |
| **validate** | `chemistry_unified` | 300 s | Full validation pipeline |

The `visualization` server is started alongside the chemistry server in every
mode.

**Mode selection:**

```bash
# Explicitly set mode
crystalyse --mode explore discover "Quick exploration"
crystalyse --mode validate discover "Thorough validation"
crystalyse --mode auto discover "Balanced default"  # Default
```

Runtimes and candidate counts vary with the query and the tools the agent
chooses; the timeouts above are the only per-mode limits the code sets.

## Model Selection

`--model` takes a name from the model registry. With no `--model`, the model
comes from the mode's default: `explore` and `auto` use `openai_o4_mini`,
`validate` uses `openai_o3`.

| Registry name | Backend | Model ID | Env var |
|---------------|---------|----------|---------|
| `openai_o4_mini` | openai | `o4-mini` | `OPENAI_API_KEY` |
| `openai_o3` | openai | `o3` | `OPENAI_API_KEY` |
| `openai_gpt4o_mini` | openai | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `anthropic_claude_opus` | litellm | `anthropic/claude-opus-5` | `ANTHROPIC_API_KEY` |
| `anthropic_claude_sonnet` | litellm | `anthropic/claude-sonnet-5` | `ANTHROPIC_API_KEY` |
| `anthropic_claude_haiku` | litellm | `anthropic/claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| `openrouter_claude_opus` | litellm | `openrouter/anthropic/claude-opus-5` | `OPENROUTER_API_KEY` |
| `openrouter_llama3_70b` | litellm | `openrouter/meta-llama/llama-3.1-70b-instruct` | `OPENROUTER_API_KEY` |
| `mistral_large` | litellm | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| `ollama_llama3_70b_direct` | openai-compat | `llama3:70b` | none (local Ollama) |

Run `crystalyse models list` for the authoritative, up-to-date version of this
table, including the context window and the modes each entry declares. The
`Modes` column is declared metadata describing what an entry is intended for;
it is not enforced at run time.

A string that is not a registry name is passed through raw, which is the escape
hatch for full LiteLLM model strings:

```bash
# Registry name
crystalyse --model anthropic_claude_sonnet discover "Screen Na-ion cathodes"

# Raw pass-through
crystalyse --model litellm/openrouter/anthropic/claude-opus-5 discover "..."
```

Where a registry entry declares a reasoning configuration, it is sent to the
provider on every run: OpenAI reasoning models receive a `reasoning` effort,
Claude 5 models adaptive thinking plus an effort level, and Claude 4.x models a
thinking token budget. An entry that declares neither is called with the
provider's own defaults, and a raw pass-through string has no entry and so no
declared reasoning configuration.

Inside a chat session, `/model <name>` swaps the model (overriding the mode
default) and `/mode <name>` swaps the mode; both recreate the agent in place.

## Environment Variables

Configure Crystalyse behaviour through environment variables. Model API keys are
read from the variable each registry entry declares - resolving a model whose
key is unset raises immediately.

```bash
# Model API keys (set the ones for the backbones you use)
export OPENAI_API_KEY="your-key-here"        # openai_* entries
export ANTHROPIC_API_KEY="your-key-here"     # anthropic_claude_* entries
export OPENROUTER_API_KEY="your-key-here"    # openrouter_* entries
export MISTRAL_API_KEY="your-key-here"       # mistral_large

# Optional
export CRYSTALYSE_PYTHON_PATH="/path/to/python"  # Python for the chemistry_unified server
export CRYSTALYSE_DEBUG="false"                  # Debug mode
export CRYSTALYSE_ENABLE_HTML_VIZ="false"        # HTML visualisation
export CRYSTALYSE_PROVENANCE_DIR="./provenance_output"  # Provenance output directory
export CRYSTALYSE_PPD_PATH="/path/to/ppd.pkl.gz" # Custom phase diagram path
export CHEMELEON_CHECKPOINT_DIR="/path/to/ckpts" # Custom checkpoint directory
```

The local Ollama entry needs no key. `OPENAI_MDG_API_KEY`, if set, is preferred
over `OPENAI_API_KEY` when building the OpenAI provider client, but it does not
satisfy a registry entry's key requirement - `OPENAI_API_KEY` must be set for
the OpenAI backbones.

Run `crystalyse models check` to confirm which keys the shell actually sees.

## Configuration File

Persistent settings live in TOML, not YAML. Two files are consulted, with the
project one winning:

1. `<project root>/.crystalyse/config.toml` - a directory containing
   `.crystalyse/` marks the project root
2. `~/.crystalyse/config.toml`

**Model registry overrides** (`[models.<name>]` tables) are read whenever a
model name is resolved and by `crystalyse models list`. A table may override the
value-like fields of a built-in entry (`model_id`, `base_url`,
`context_window`, `max_tokens`, `temperature`, `reasoning_effort`,
`thinking_budget_tokens`, `notes`) or define an entirely new entry:

```toml
# Override one field of a built-in entry.
[models.anthropic_claude_opus]
model_id = "anthropic/claude-opus-4-6"
reasoning_effort = "high"

# Define a new backbone without editing package code.
[models.my_local_llm]
backend = "openai-compat"
model_id = "qwen3-32b"
api_key_env_var = ""
base_url = "http://localhost:8000/v1"
supported_modes = ["explore"]
```

Capability fields (`backend`, `api_key_env_var`, `supports_tool_calling`,
`supports_structured_output`, `supported_modes`) cannot be overridden on a
built-in - define a new entry instead. Anything invalid raises a
`ModelOverrideError` when the registry is first loaded - at the first model
resolution, or on `crystalyse models list` - rather than being silently
ignored, and `models list` shows the resulting `Source` for every entry.

The same files also define runtime settings - `default_model`, `default_mode`,
`plan_mode`, `plans_directory` and `plans_cleanup_days` (unrecognised keys are
dropped). These are read by `crystalyse.config.settings.load_settings()`; the
CLI's own mode and model selection currently comes from `--mode`/`--model` and
the per-mode defaults.

MCP server commands and working directories are computed from the installed
package location, and provenance behaviour is controlled by the `CRYSTALYSE_*`
environment variables above - neither is configurable from the TOML file.

## First Run Auto-Downloads

On first execution, Crystalyse automatically downloads required data:

**Chemeleon Model Checkpoints** (~604 MB):
- Downloaded from Figshare to `~/.cache/crystalyse/chemeleon_checkpoints/`
- One-time download, cached permanently
- Override the location with `CHEMELEON_CHECKPOINT_DIR`

**Materials Project Phase Diagrams** (~178 MB, 271,617 entries):
- Downloaded to `~/.cache/crystalyse/ppd-mp_all_entries_uncorrected_250409.pkl.gz`
- Used for energy-above-hull calculations
- Override the location with `CRYSTALYSE_PPD_PATH`, or fetch it ahead of time
  with `crystalyse setup`

**MACE foundation models** are cached in `~/.cache/mace/`.

Progress bars show download status. Files are never re-downloaded.

## Troubleshooting

### Command not found

```bash
$ crystalyse: command not found

# Solution: Check installation
cd dev && pip install -e .
```

### API key errors

```bash
$ RuntimeError: ModelConfig 'openai_o4_mini' requires env var 'OPENAI_API_KEY', but it is not set.

# Solution: Set the environment variable the registry entry declares
export OPENAI_API_KEY="your-key-here"

# Verify
crystalyse models check
```

On zsh, put the export in `~/.zshenv` - `~/.zshrc` is only read by interactive
shells, so keys set there are invisible to scripts and editors.

### MCP server connection errors

```bash
$ Error: Chemistry server connection failed

# Check Python path
which python

# The chemistry_unified server honours this override (the chemistry_creative
# and visualization servers always use the interpreter running Crystalyse)
export CRYSTALYSE_PYTHON_PATH="/path/to/your/python"

# Verify installation
pip list | grep crystalyse
```

### Session database issues

Conversation memory is one SQLite database per session ID, at
`~/.crystalyse/sessions/<session_id>.db`, where the session ID is
`<project_name>_<mode>`.

```bash
# Check permissions (default project and mode)
ls -la ~/.crystalyse/sessions/crystalyse_session_auto.db

# Reset if corrupted (remove the -shm/-wal siblings too)
rm ~/.crystalyse/sessions/crystalyse_session_auto.db*
crystalyse chat  # Creates a fresh database
```

From inside a session, `/memory clear` does the same thing with a confirmation
prompt.

## Best Practices

### Query optimisation

```bash
# Good: Specific and actionable
crystalyse discover "Find stable perovskites with band gaps 1.2-1.6 eV"

# Better: Include application context
crystalyse discover "Design lead-free perovskite solar cell materials"

# Best: Specify requirements and constraints
crystalyse --mode validate discover "Find environmentally friendly perovskite alternatives to MAPbI3 for tandem solar cells"
```

### Workflow recommendations

1. **Start with explore mode** for rapid exploration
2. **Iterate** based on initial results
3. **Validate with validate mode** for publication-quality analysis
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

Keep `--project` and the mode constant when you want to resume the same
conversation - the database key is `<project>_<session>_<mode>`.

### Integration with research workflows

**Shell scripting:**

```bash
#!/bin/bash
# Automated materials screening

export OPENAI_API_KEY="your-key"
crystalyse models check || exit 1

for material in "LiCoO2" "LiFePO4" "LiMn2O4"; do
    echo "Analysing $material..."
    crystalyse --mode validate discover "Analyse $material cathode properties" \
        --provenance-dir ./screening_results/$material
done
```

**Python integration:**

```python
import subprocess

def discover_material(formula, mode="explore"):
    """Run Crystalyse discovery from Python."""
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
    analysis = discover_material(material, mode="validate")
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

# Use explore mode for the lightest run
crystalyse --mode explore discover "query"
```

**Disk space:**

```bash
# Check available space
df -h

# Clean old provenance data
find ./provenance_output/runs -type d -mtime +30 -exec rm -rf {} +

# Clean visualisations
find . -name "*_3dmol.html" -mtime +7 -delete
```

This CLI guide reflects the actual implementation in Crystalyse v1.0.0-dev
(`crystalyse --version`). For API-level integration, see the reference
documentation.
