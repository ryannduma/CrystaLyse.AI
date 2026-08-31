# CLI Reference

Complete command-line interface reference for Crystalyse.

## Overview

Crystalyse provides a unified command-line interface with multiple commands for different workflows:

- **Analysis Commands**: Direct materials analysis and evaluation
- **Session Commands**: Interactive conversation
- **Model Commands**: Inspect and validate the available model backbones
- **Utility Commands**: Data setup and provenance inspection

## Command Structure

```bash
crystalyse [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

Global options are declared on the top-level callback, so they must appear **before** the command
name. `crystalyse --verbose discover "query"` works; `crystalyse discover "query" --verbose` is a
usage error.

Running `crystalyse` with no command starts `chat`.

### Global Options

Available for all commands:

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `--version` | Print `Crystalyse v1.0.0-dev` and exit |
| `-p, --project TEXT` | Project name for the workspace (default: `crystalyse_session`) |
| `--mode TEXT` | Agent operating mode, case-insensitive (default: `auto`) |
| `--model TEXT` | Backbone to use - a name from `crystalyse models list`, or a raw LiteLLM model string |
| `-v, --verbose` | Enable debug-level logging |

Accepted `--mode` values are `explore`, `validate` and `auto`. The legacy names `creative`,
`rigorous` and `adaptive` still resolve to them, but emit a `DeprecationWarning` and will be
removed in v2.0.

## Commands Overview

### Analysis Commands

#### `crystalyse discover`
Run non-interactive materials discovery with provenance tracking.

```bash
crystalyse discover QUERY [OPTIONS]
```

**Key Options**:
- `--mode TEXT` - Analysis mode for this run (overrides the global option)
- `--project, -p TEXT` - Project name for workspace organisation (overrides the global option)
- `--provenance-dir PATH` - Custom directory for provenance output (default: `./provenance_output`)
- `--hide-summary` - Suppress the provenance summary table (data is still captured)

**Examples**:
```bash
crystalyse discover "Find battery cathode materials" --mode explore
crystalyse discover "Analyse LiCoO2 stability" --mode validate
crystalyse discover "Quick test" --hide-summary
crystalyse -v discover "Find stable perovskites"        # --verbose is global
```

### Session Commands

#### `crystalyse chat`
Start an interactive chat session for materials discovery.

```bash
crystalyse chat [OPTIONS]
```

**Key Options**:
- `--user, -u TEXT` - User identifier (default: `default`)
- `--session, -s TEXT` - Session name; appended to the project name for the workspace

Mode and model are **not** per-command options here - set them globally
(`crystalyse --mode validate chat`) or switch them inside the session with `/mode` and `/model`.
Conversation memory is stored per project, session and mode at
`~/.crystalyse/sessions/<project>_<session>_<mode>.db` (`<project>_<mode>.db` when `-s` is
omitted), so re-running the same invocation continues the same conversation.

**Examples**:
```bash
crystalyse chat -u researcher -s battery_project
crystalyse --mode validate chat -u researcher -s battery_project
crystalyse -p solar_study chat -u student
```

### Interactive Interface

#### `crystalyse` (Unified Interface)
Launch the interactive interface with real-time mode switching.

```bash
crystalyse
```

**In-Session Commands**:
- `/mode [show|explore|validate|auto]` - View or change the operating mode
- `/model [show|<name>]` - View or change the backbone
- `/tools [desc|nodesc]` - List available MCP tools and servers
- `/mcp [status|servers|desc]` - Show MCP server status and details
- `/stats` - Session statistics and performance
- `/memory [show|clear|refresh]` - Manage agent memory and conversation history
- `/about` - Show version and system information
- `/help` - Show available commands
- `/clear` - Clear screen
- `/quit`, `/exit` - Exit interface

Changing the mode or model recreates the agent in place.

### Model Commands

#### `crystalyse models list`
Print the effective model registry - the built-in entries plus any `[models.*]` tables from
`.crystalyse/config.toml`.

```bash
crystalyse models list
```

Columns: **Name**, **Backend**, **Model ID**, **Context**, **Modes**, **Env Var**, **Source**,
**Usable**. `Source` reports where the entry came from - `built-in`, `user-override` or
`user-defined`. `Usable` is a green tick when the entry's API-key variable is set, or when it
needs no key at all.

#### `crystalyse models check`
Validate the API-key environment variables for the built-in registry entries.

```bash
crystalyse models check
```

Prints one line per model and exits with code `1` if any model that requires a key is missing it.
Entries with no `api_key_env_var` (the local Ollama backbone) are reported as requiring no key.

### Utility Commands

#### `crystalyse setup`
Download and set up required data files (the pre-computed phase diagram).

```bash
crystalyse setup [OPTIONS]
```

**Key Options**:
- `--force, -f` - Force re-download of data files

**Examples**:
```bash
crystalyse setup
crystalyse setup --force
```

#### `crystalyse analyse-provenance`
Analyse provenance data from previous discovery sessions.

```bash
crystalyse analyse-provenance [OPTIONS]
```

**Key Options**:
- `--latest` - Analyse the most recent session
- `--session TEXT` - Analyse a specific session ID
- `--dir PATH` - Provenance directory to search (default: `./provenance_output`)

With neither `--latest` nor `--session`, the command lists the ten most recent sessions found
under `<dir>/runs/`.

**Examples**:
```bash
crystalyse analyse-provenance --latest
crystalyse analyse-provenance --session crystalyse_explore_20250910_120000
crystalyse analyse-provenance --dir ./my_research/provenance
```

## Command Categories

### By Workflow Type

**Quick Analysis**:
```bash
crystalyse discover "query" --mode explore     # Fast results
```

**Research Sessions**:
```bash
crystalyse chat -u researcher -s project       # Interactive research
crystalyse --mode validate chat -s project     # Same session, thorough mode
```

**System Management**:
```bash
crystalyse models list                         # Effective registry and its provenance
crystalyse models check                        # Which API keys are set
crystalyse setup                               # Phase-diagram data
```

### By Analysis Mode

**Explore Mode** (Fast exploration):
```bash
crystalyse discover "query" --mode explore
crystalyse --mode explore chat
```

**Validate Mode** (Complete validation):
```bash
crystalyse discover "query" --mode validate
crystalyse --mode validate chat
```

## Exit Codes

Crystalyse itself produces only two codes; `2` comes from Click's own usage-error handling:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | `setup` failed to download data, `models check` found a missing key, or an unhandled exception was caught |
| 2 | Usage error raised by the CLI framework (unknown option, missing argument) |

There are no dedicated codes for configuration, API, MCP or timeout failures - those surface as
code `1` with the error text printed and a pointer to `crystalyse.log`.

## Environment Variables

### Provider API Keys

Set the key for whichever backbone you use. These must be real environment variables - Crystalyse
does not read `.env` files. On zsh, put them in `~/.zshenv` so non-interactive shells see them
too (`~/.zshrc` is interactive-only).

```bash
export OPENAI_API_KEY="..."         # OpenAI entries (the defaults)
export ANTHROPIC_API_KEY="..."      # anthropic_claude_* entries
export OPENROUTER_API_KEY="..."     # openrouter_* entries
export MISTRAL_API_KEY="..."        # mistral_large
# the local Ollama entry needs no key
```

`crystalyse models check` reports which of these are set.

### Optional
```bash
export CRYSTALYSE_DEBUG="true"                 # Passes CRYSTALYSE_DEBUG through to MCP servers
export CRYSTALYSE_PYTHON_PATH="/path/to/python"  # Interpreter for the chemistry_unified server
export CRYSTALYSE_PROVENANCE_DIR="./provenance_output"  # Default provenance location
export CRYSTALYSE_SHOW_PROVENANCE_SUMMARY="true"        # Summary table after discover
export CRYSTALYSE_PPD_PATH="/path/to/ppd.pkl.gz"        # Pre-existing phase-diagram file
export CHEMELEON_CHECKPOINT_DIR="/path/to/checkpoints"  # Pre-downloaded Chemeleon checkpoints
```

See the [Configuration Reference](../config/index.md) for the complete list, including which
variables are parsed but not yet consumed.

## Common Usage Patterns

### Research Workflow
```bash
# 1. Start with fast exploration
crystalyse discover "battery materials" --mode explore

# 2. Interactive refinement
crystalyse --mode explore chat -u researcher -s battery_study

# 3. Detailed validation in the same session
crystalyse --mode validate chat -u researcher -s battery_study

# 4. Review what the runs actually did
crystalyse analyse-provenance --latest
```

### Batch Analysis
```bash
# Multiple one-shot analyses
crystalyse discover "LiCoO2 cathode" --mode validate --project batch1
crystalyse discover "LiFePO4 cathode" --mode validate --project batch1
crystalyse discover "LiMn2O4 cathode" --mode validate --project batch1

# Review batch results
crystalyse analyse-provenance --dir ./provenance_output
```

### Mode Switching
```bash
# Unified interface with mode switching
crystalyse
> /mode explore
> Find perovskite materials
> /mode validate
> Analyse the most stable candidate
> /exit
```

## Output Formats

### Analysis Results

**Explore Mode**:
- Structured terminal output with formation energies
- CIF structure files (`{formula}.cif`)
- Provenance summary table

**Validate Mode**:
- Complete analysis pipeline output
- pymatviz PDF plots in `{formula}_analysis/`: `XRD_Pattern_{formula}.pdf`,
  `RDF_Analysis_{formula}.pdf`, `Coordination_Analysis_{formula}.pdf`
- CIF structure files

3dmol.js HTML output is disabled: the visualisation tool writes the CIF file and reports
`"type": "cif_file"`.

### Session Output

**Interactive Sessions**:
- Real-time conversation display
- Progress indicators
- Error messages with context
- Mode and model switching feedback

### Registry Output

**`crystalyse models list`**:
- Rich table of the effective registry
- Per-entry provenance (`built-in` / `user-override` / `user-defined`)
- Per-entry key availability

## Error Handling

### Common Error Scenarios

**API Key Missing**:
```bash
$ crystalyse discover "test"
❌ An unexpected error occurred: ModelConfig 'openai_o4_mini' requires env var
'OPENAI_API_KEY', but it is not set.
```
Diagnose with `crystalyse models check`, then export the key (see above). Exit code `1`.

**Invalid Mode**:
```bash
$ crystalyse discover "test" --mode invalid
❌ An unexpected error occurred: Unknown mode 'invalid'. Valid modes: adaptive, auto,
creative, explore, rigorous, validate
```

**Global option after the command**:
```bash
$ crystalyse discover "test" --verbose
# Usage error, exit code 2: --verbose is a global option
$ crystalyse --verbose discover "test"
```

**Invalid model override in config.toml**:
```bash
$ crystalyse models list
❌ An unexpected error occurred: [models.openai_o3] in /path/.crystalyse/config.toml: cannot
override capability field(s) ['backend'] on the built-in entry 'openai_o3'. ...
```
The underlying exception is `ModelOverrideError`; an invalid `[models.*]` table aborts rather
than being skipped.

### Error Recovery

Unhandled errors are logged and the CLI points at the log file:
```bash
❌ An unexpected error occurred: <message>
Check crystalyse.log for details.
```
`crystalyse.log` is written in the current working directory.

## Performance Tuning

### Choosing a Mode and a Backbone

Runtime is dominated by the mode (which MCP server and timeout it uses) and by the backbone.
`crystalyse models list` shows the context window and supported modes for each entry, and the
`notes` in the registry record the relative cost of each Anthropic tier.

```bash
crystalyse discover "query" --mode explore                          # 120 s budget
crystalyse --model anthropic_claude_haiku discover "query"          # cheapest Anthropic tier
crystalyse --model openai_o3 discover "query" --mode validate       # highest quality, slowest
```

`CRYSTALYSE_STRUCTURE_SAMPLES`, `CRYSTALYSE_MAX_CANDIDATES`, `CRYSTALYSE_BATCH_SIZE` and
`CRYSTALYSE_MAX_TURNS` are parsed into the config object but no code currently reads them, so
setting them does not change behaviour.

### GPU Acceleration
```bash
# MACE automatically uses GPU if available
nvidia-smi  # Check GPU status
```

## Debugging

### Verbose Output
```bash
crystalyse --verbose discover "query"
crystalyse -v chat -u user
```

### Debug Environment
```bash
export CRYSTALYSE_DEBUG="true"
crystalyse discover "query"
```

## Integration Examples

### Shell Scripting
```bash
#!/bin/bash
export OPENAI_API_KEY="..."

materials=("LiCoO2" "LiFePO4" "LiMn2O4")
for material in "${materials[@]}"; do
    crystalyse discover "Analyse $material cathode" --mode validate
done
```

### Python Integration
```python
import subprocess

def analyse_material(formula, mode="explore"):
    cmd = ["crystalyse", "discover", f"Analyse {formula}", "--mode", mode]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

## See Also

- [Installation Guide](../../guides/installation.md) - Setup and configuration
- [CLI Usage Guide](../../guides/cli_usage.md) - Comprehensive examples
- [Configuration Reference](../config/index.md) - Configuration options
- [Error Reference](../errors/index.md) - Error codes and troubleshooting
