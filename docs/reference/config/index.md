# Configuration Reference

Complete reference for Crystalyse configuration options, environment variables, and system settings.

## Overview

Crystalyse can be configured through multiple mechanisms:

- **Environment Variables**: API keys and `CRYSTALYSE_*` runtime switches
- **Configuration Files**: `.crystalyse/config.toml` - runtime settings and model registry overrides
- **Command-line Options**: Per-execution overrides (`--mode`, `--model`, `--project`)
- **MCP Server Configuration**: Built in Python, not user-editable through a config file

## Environment Variables

### Required Variables

At least one provider key is required - which one depends on the backbone you select. All keys
must be **real environment variables**: Crystalyse contains no `.env` / python-dotenv support. On
zsh, put the exports in `~/.zshenv` so non-interactive shells see them (`~/.zshrc` is
interactive-only).

#### `OPENAI_API_KEY`
OpenAI API key for the OpenAI-backed registry entries.

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Used by**: `openai_o4_mini`, `openai_o3`, `openai_gpt4o_mini` - the defaults for every mode
**Required**: Yes, unless you select a non-OpenAI backbone with `--model`
**Default**: None
**Validation**: `ModelConfig.validate_env()` only checks that the variable is non-empty - there is
no key-format check anywhere in the codebase

`CrystaLyseConfig` additionally reads `OPENAI_MDG_API_KEY`, and the agent bridge prefers it over
`OPENAI_API_KEY` when building the OpenAI provider for a run. Set it only if you have a separate
MDG key; otherwise leave it unset.

#### `ANTHROPIC_API_KEY`
Direct Anthropic API key.

```bash
export ANTHROPIC_API_KEY="..."
```

**Used by**: `anthropic_claude_opus`, `anthropic_claude_sonnet`, `anthropic_claude_haiku`

#### `OPENROUTER_API_KEY`
OpenRouter key - one key, many models.

```bash
export OPENROUTER_API_KEY="..."
```

**Used by**: `openrouter_claude_opus`, `openrouter_llama3_70b`

#### `MISTRAL_API_KEY`
Mistral API key.

```bash
export MISTRAL_API_KEY="..."
```

**Used by**: `mistral_large`

The local `ollama_llama3_70b_direct` entry has an empty `api_key_env_var` and needs no key at all.
Run `crystalyse models check` to see which keys are currently set.

### Optional Variables

#### Model Configuration

##### `CRYSTALYSE_MODEL`
Legacy default-model string held on `CrystaLyseConfig.default_model`.

```bash
export CRYSTALYSE_MODEL="o4-mini"
```

**Type**: String
**Default**: `o4-mini`
**Status**: Parsed but not consumed - nothing in the current pipeline reads it. Model selection
goes through the registry instead: the global `--model` flag, the `/model` slash command, or the
mode default.

Registry keys accepted by `--model` and `/model`:

| Name | Backend | Model ID |
|------|---------|----------|
| `openai_o4_mini` | openai | `o4-mini` |
| `openai_o3` | openai | `o3` |
| `openai_gpt4o_mini` | openai | `gpt-4o-mini` |
| `anthropic_claude_opus` | litellm | `anthropic/claude-opus-5` |
| `anthropic_claude_sonnet` | litellm | `anthropic/claude-sonnet-5` |
| `anthropic_claude_haiku` | litellm | `anthropic/claude-haiku-4-5-20251001` |
| `openrouter_claude_opus` | litellm | `openrouter/anthropic/claude-opus-5` |
| `openrouter_llama3_70b` | litellm | `openrouter/meta-llama/llama-3.1-70b-instruct` |
| `mistral_large` | litellm | `mistral/mistral-large-latest` |
| `ollama_llama3_70b_direct` | openai-compat | `llama3:70b` |

An unrecognised string passes through raw, which is the escape hatch for full LiteLLM model
strings. Mode defaults are `explore` → `openai_o4_mini`, `validate` → `openai_o3`,
`auto` → `openai_o4_mini`.

##### `CRYSTALYSE_MAX_TURNS`
Maximum conversation turns per run.

```bash
export CRYSTALYSE_MAX_TURNS="1000"
```

**Type**: Integer
**Default**: 1000
**Status**: Parsed but not consumed - the agent bridge passes a literal `max_turns=1000`

#### Performance Configuration

These three are parsed into `CrystaLyseConfig` but **no code currently reads them**, so setting
them has no effect today:

```bash
export CRYSTALYSE_STRUCTURE_SAMPLES="5"   # default 5
export CRYSTALYSE_MAX_CANDIDATES="100"    # default 100
export CRYSTALYSE_BATCH_SIZE="10"         # default 10
```

#### Debugging and Development

##### `CRYSTALYSE_DEBUG`
Enable debug mode.

```bash
export CRYSTALYSE_DEBUG="true"
```

**Type**: Boolean (`true`/`false`)
**Default**: `false`
**Effect**: Sets `config.debug_mode`, whose only use is to pass `CRYSTALYSE_DEBUG=true` through to
the MCP server subprocesses. For verbose CLI logging use `crystalyse --verbose`.

##### `CRYSTALYSE_PYTHON_PATH`
Interpreter used to launch the `chemistry_unified` MCP server.

```bash
export CRYSTALYSE_PYTHON_PATH="/path/to/conda/envs/crystalyse/bin/python"
```

**Type**: Path to a Python executable
**Default**: `sys.executable`
**Note**: Only `chemistry_unified` honours it; the other two servers always use `sys.executable`

##### `CRYSTALYSE_METRICS`
Sets `config.enable_metrics`.

```bash
export CRYSTALYSE_METRICS="true"
```

**Type**: Boolean
**Default**: `true`
**Status**: Parsed but not consumed

#### Provenance Configuration

Provenance capture is always on; these variables control where it goes and how much is kept.

```bash
export CRYSTALYSE_PROVENANCE_DIR="./provenance_output"   # output directory
export CRYSTALYSE_SESSION_PREFIX="crystalyse"            # session-ID prefix
export CRYSTALYSE_CAPTURE_RAW="true"                     # save raw tool outputs
export CRYSTALYSE_CAPTURE_MCP_LOGS="false"               # capture MCP server logs
export CRYSTALYSE_SHOW_PROVENANCE_SUMMARY="true"         # summary table after discover
export CRYSTALYSE_VISUAL_TRACE="true"                    # visual trace during runs
```

All six are read by the provenance bridge. `crystalyse discover --provenance-dir PATH` overrides
`CRYSTALYSE_PROVENANCE_DIR` for a single run, and `--hide-summary` overrides the summary setting.

#### Render Gate Configuration

```bash
export CRYSTALYSE_RENDER_GATE="true"                     # enable the render gate
export CRYSTALYSE_RENDER_GATE_LOG="true"                 # log gate violations
export CRYSTALYSE_RENDER_GATE_STRICTNESS="intelligent"   # parsed, not consumed
export CRYSTALYSE_BLOCK_UNPROVENANCED="true"             # parsed, not consumed
```

Only the first two reach the agent bridge; the other two are stored on the config object and not
read anywhere yet.

#### Visualisation Preferences

```bash
export CRYSTALYSE_ENABLE_HTML_VIZ="false"   # default false
export CRYSTALYSE_CIF_ONLY="true"           # default true
export CRYSTALYSE_COLOR_SCHEME="vesta"      # default vesta
```

**Status**: Parsed into `config.visualization` but not consumed - the visualisation server writes
CIF files unconditionally, and its 3dmol.js HTML output is disabled in code.

#### Storage and Caching

##### `CHEMELEON_CHECKPOINT_DIR`
Custom directory for Chemeleon model checkpoints.

```bash
export CHEMELEON_CHECKPOINT_DIR="/path/to/existing/checkpoints"
```

**Type**: Directory path
**Default**: `~/.cache/crystalyse/chemeleon_checkpoints/` (auto-downloads if not set)
**Optional**: Yes - zero configuration by default
**Impact**: Allows offline installations or custom checkpoint locations (e.g., shared lab servers)
**Requirements**: Directory must contain:
- `chemeleon_csp_alex_mp_20_v0.0.2.ckpt`
- `chemeleon_dng_alex_mp_20_v0.0.2.ckpt`

The checkpoints are fetched as a single Figshare archive (523 MB) and occupy roughly 604 MB once
extracted.

**When to use**:
- Offline installations (manual checkpoint download)
- Shared multi-user systems with pre-downloaded checkpoints
- Custom storage locations due to disk space constraints

See [Installation Guide - Chemeleon Model Checkpoints](../../guides/installation.md#chemeleon-model-checkpoints) for setup details.

##### `CRYSTALYSE_PPD_PATH`
Explicit path to the pre-computed phase-diagram file.

```bash
export CRYSTALYSE_PPD_PATH="/shared/data/ppd-mp_all_entries_uncorrected_250409.pkl.gz"
```

**Type**: File path
**Default**: unset - resolution falls back to `~/.cache/crystalyse/`, then a copy sitting beside
`pyproject.toml` in a source checkout, then an automatic download
**Related**: `crystalyse setup` performs that download ahead of time (~178 MB, 271617 entries)

MACE foundation models cache separately, under `~/.cache/mace/`.

## Configuration Files

### Location and Precedence

Configuration is **TOML**, in a `.crystalyse/` directory. There are exactly two layers:

1. `~/.crystalyse/config.toml` - user level
2. `<project_root>/.crystalyse/config.toml` - project level, wins over the user level

The project root is the nearest ancestor directory of the working directory that contains a
`.crystalyse/` directory, in the same way `.git/` marks a repository. There is no system-wide
layer and no YAML support.

`ensure_crystalyse_root()` scaffolds a fresh root:

```text
.crystalyse/
├── config.toml          # commented template documenting the settings below
├── plans/               # plan-mode artefacts
├── runs/                # provenance run data
└── .gitignore           # ignores runs/, plans/latest.md and agent/
```

A missing config file is not an error - built-in defaults are used. A file that cannot be parsed
is logged as a warning and treated as empty.

### Runtime Settings

Top-level keys map onto the `CrystalyseSettings` dataclass:

```toml
# <project>/.crystalyse/config.toml

default_model = "openai_o4_mini"   # any name from `crystalyse models list`
default_mode = "explore"           # explore | validate | auto
plan_mode = "auto"                 # on | off | auto
plans_directory = "docs/plans"     # default: <project_root>/.crystalyse/plans/
plans_cleanup_days = 30
```

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `default_model` | string | `"openai_o4_mini"` | Registry key resolved by `resolve_model_name` |
| `default_mode` | string | `"explore"` | Canonical mode name |
| `plan_mode` | `"on"`/`"off"`/`"auto"` | `"auto"` | Whether plan mode is active |
| `plans_directory` | string or unset | unset | Override for the plans directory |
| `plans_cleanup_days` | integer | `30` | Age at which plan files become eligible for cleanup |

Keys that are not settings fields are dropped silently rather than reported.

!!! warning "Runtime settings are not wired into the CLI yet"

    `load_settings()` currently has no production call site - only the tests import it. The five
    keys above are readable through the API but do **not** change CLI behaviour today: mode still
    comes from `--mode` (default `auto`) and model from `--model` or the mode default. The
    `[models.*]` tables below, by contrast, are live.

### `[models.<name>]` Override Tables

A `[models.<name>]` table either overrides a built-in registry entry or defines a new backbone,
so a stale provider model ID or a new provider does not require editing installed package code.

```toml
# Override the value-like fields of a built-in entry.
[models.anthropic_claude_opus]
model_id = "anthropic/claude-opus-4-6"
reasoning_effort = "high"

# Define a whole new entry.  New entries must declare their capabilities.
[models.my_local_llm]
backend = "openai-compat"
model_id = "qwen3-32b"
api_key_env_var = ""
base_url = "http://localhost:8000/v1"
supported_modes = ["explore"]
```

**Overridable on a built-in entry**: `model_id`, `base_url`, `context_window`, `max_tokens`,
`temperature`, `reasoning_effort`, `thinking_budget_tokens`, `notes`.

**Capability fields** - `backend`, `api_key_env_var`, `supports_tool_calling`,
`supports_structured_output`, `supported_modes` - describe what a model can *do*. They are
code-owned and are **refused** on a built-in entry; set them by defining a new entry instead.

**Required when defining a new entry**: `backend`, `model_id` and `api_key_env_var`. An empty
`api_key_env_var` means "no key needed" (a local model).

**Value constraints**:

- `backend` must be `openai`, `litellm` or `openai-compat`
- `reasoning_effort` must be `low`, `medium` or `high`
- `supported_modes` must be a list of strings drawn from `explore`, `validate`, `auto`

**Failure behaviour**: every problem raises `ModelOverrideError` (a `ValueError` subclass) with a
message of the form `[models.<name>] in <path>: <reason>` - unknown fields, bad enum values,
missing required fields and capability-override attempts all abort at start-up rather than being
silently skipped.

**Precedence**: built-ins, then `~/.crystalyse/config.toml`, then `<project>/.crystalyse/config.toml`.
A project table for a model that the user config also overrides replaces it - the project table is
applied to the built-in entry, not merged on top of the user's version.

`crystalyse models list` shows the result, with a **Source** column reporting `built-in`,
`user-override` or `user-defined`. Note that `crystalyse models check` walks the built-in registry
only, so keys for user-defined entries are not covered by it.

## MCP Server Configuration

### Server Definitions

Server definitions are built in Python (`crystalyse/config/__init__.py`), not read from a config
file - there is no user-editable `mcp_servers` section.

| Server | Module | Working directory | Tools |
|--------|--------|-------------------|-------|
| `chemistry_unified` | `chemistry_unified.server` | `<package parent>/chemistry-unified-server/src` | 20 |
| `chemistry_creative` | `chemistry_creative.server` | `<package parent>/chemistry-creative-server/src` | 4 |
| `visualization` | `visualization_mcp.server` | `<package parent>/visualization-mcp-server/src` | 5 |

29 tools in total. Each server is launched as `python -m <module>` with:

- **command**: `sys.executable`, except `chemistry_unified`, which honours `CRYSTALYSE_PYTHON_PATH`
- **env**: a copy of the current environment, plus `CRYSTALYSE_DEBUG=true` when debug mode is on
- **cwd**: the `src` directory listed above

`get_server_config()` raises `FileNotFoundError` if the working directory is missing or the
interpreter is not on `PATH`.

A run starts two servers, not three: the mode's chemistry server (`chemistry_creative` for
`explore`, `chemistry_unified` for `validate` and `auto`) plus `visualization`. Both are started
when the discovery begins and stopped when it ends.

All three servers build on `MCPServer` from `mcp` 2.0 (the class formerly called `FastMCP`).

!!! note "The `chemistry-creative-server` directory name is deliberate"

    Modes were renamed `creative` → `explore`, but the MCP server package keeps its original
    name. `chemistry_creative` is the server used by explore mode.

### Server Status

Check server status from inside a chat session:

```bash
crystalyse
> /mcp status
> /tools
```

## Analysis Mode Configuration

Mode selection is a command-line and slash-command concern, not a config-file one:

```bash
crystalyse --mode validate discover "query"   # global option, before the command
crystalyse discover "query" --mode explore    # per-run override
> /mode auto                                  # inside a chat session
```

Per-mode MCP server and timeout defaults are hard-coded and not configurable:

| Mode | MCP server | Timeout | Default model |
|------|------------|---------|---------------|
| `explore` | `chemistry_creative` | 120 s | `openai_o4_mini` |
| `auto` | `chemistry_unified` | 180 s | `openai_o4_mini` |
| `validate` | `chemistry_unified` | 300 s | `openai_o3` |

`creative`, `rigorous` and `adaptive` still resolve to `explore`, `validate` and `auto`, with a
`DeprecationWarning`; they are removed in v2.0. `default_mode` in `config.toml` and any
`supported_modes` list must use the canonical names.

## Viewing Configuration

```bash
# Effective model registry, including config.toml overrides and where each entry came from
crystalyse models list

# Which provider API keys are set (exit code 1 if any required key is missing)
crystalyse models check
```

There is no `crystalyse config` command; the config file is edited by hand.

## Configuration Validation

### Common Validation Issues

**Missing API key**:
```
ModelConfig 'openai_o4_mini' requires env var 'OPENAI_API_KEY', but it is not set.
   Solution: export the key (in ~/.zshenv on zsh), then re-run `crystalyse models check`
```

**Unparseable config.toml**:
```
WARNING  Failed to parse /path/.crystalyse/config.toml: <tomllib error>
   Effect: the file is treated as empty and defaults apply - the run continues
   Solution: fix the TOML syntax
```

**Invalid `[models.*]` table**:
```
ModelOverrideError: [models.openai_o3] in /path/.crystalyse/config.toml: cannot override
capability field(s) ['backend'] on the built-in entry 'openai_o3'.
   Effect: start-up aborts - a bad model override is never papered over
   Solution: define a new [models.*] entry instead of changing a built-in's capabilities
```

**MCP server directory missing**:
```
FileNotFoundError: MCP server directory not found: <path>/chemistry-unified-server/src
   Solution: install the server packages from dev/ (see the Installation Guide)
```

## Advanced Configuration

### Adding a Provider Without Touching Package Code

```toml
# ~/.crystalyse/config.toml
[models.my_openrouter_qwen]
backend = "litellm"
model_id = "openrouter/qwen/qwen3-235b-a22b"
api_key_env_var = "OPENROUTER_API_KEY"
context_window = 131072
supported_modes = ["explore", "auto"]
notes = "Team-shared screening backbone."
```

```bash
crystalyse models list                              # Source: user-defined
crystalyse --model my_openrouter_qwen discover "…"
```

### Per-Project Overrides

Because the project config wins over the user config, a repository can pin the backbone its
results were produced with by committing `.crystalyse/config.toml`, while individual users keep
their own defaults in `~/.crystalyse/config.toml`.

## Troubleshooting Configuration

### Common Issues

**Overrides Not Taking Effect**:
1. Confirm you are inside the project root (`.crystalyse/` must exist in an ancestor directory)
2. Run `crystalyse models list` and read the `Source` column
3. Remember that the effective registry is cached per process

**MCP Servers Not Starting**:
1. Verify the Python environment (set `CRYSTALYSE_PYTHON_PATH` if the server needs a specific one)
2. Check the server packages are installed from `dev/`
3. Review `crystalyse.log` in the working directory

**Runtime Settings Ignored**:
`default_model`, `default_mode`, `plan_mode`, `plans_directory` and `plans_cleanup_days` are not
yet consumed by the CLI - use `--model` and `--mode` for now.

### Debug Configuration

```bash
export CRYSTALYSE_DEBUG="true"
crystalyse --verbose models list
```

## See Also

- [Installation Guide](../../guides/installation.md) - Initial setup
- [CLI Reference](../cli/index.md) - Command-line options
- [Error Reference](../errors/index.md) - Configuration error types
