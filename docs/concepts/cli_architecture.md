# CLI Architecture - Crystalyse v1.0.0-dev

## Overview

Crystalyse v1.0.0-dev provides a unified CLI architecture built on a single enhanced agent (`EnhancedCrystaLyseAgent`) that coordinates with specialized tools and MCP servers. This document clarifies the actual implementation versus documentation discrepancies.

## Agent Architecture Reality

### Single Agent Implementation

**Actual Implementation**: One main agent class - `EnhancedCrystaLyseAgent`
- **Location**: `dev/crystalyse/agents/agents_bridge.py` (the class is re-exported from `crystalyse.agents` and `crystalyse`)
- **Role**: Handles all materials discovery functionality through intelligent tool coordination

**Documentation Discrepancy**: Previous docs described multiple specialized agents (MaterialsOrchestrator, CompositionExplorer, etc.) that **do not exist as separate classes**

### How the Single Agent Works

The `EnhancedCrystaLyseAgent` provides "multi-agent-like" behavior through:

1. **Intelligent Tool Coordination**: Automatically selects appropriate MCP servers based on mode
2. **Workspace Management**: Handles file operations with user preview/approval
3. **Mode-Aware Processing**: Different behavior for explore/validate/auto modes
4. **Session Persistence**: One SQLite conversation store per project and mode
5. **Model Registry**: Named backbones across OpenAI, Anthropic, OpenRouter, Mistral and local Ollama, resolved from the mode or from `--model`

## CLI Entry Points

### Primary Entry Point: `crystalyse`

**Configuration**: `pyproject.toml` → `crystalyse = "crystalyse.cli:main"`

**Available Commands**:

```bash
crystalyse discover "query"              # Non-interactive, single-shot discovery
crystalyse chat -u user -s session       # Interactive chat session
crystalyse setup                         # Download the phase-diagram data files
crystalyse analyse-provenance --latest   # Inspect provenance from a previous run
crystalyse models list                   # Show the effective model registry
crystalyse models check                  # Validate API-key environment variables
```

Running `crystalyse` with no arguments inserts `chat`.

**Global Options**:
```bash
--project, -p        # Project name for workspace (default: crystalyse_session)
--mode              # Agent operating mode: explore/validate/auto (default: auto)
--model             # Language model: a registry name or a raw model string (default: mode default)
--verbose, -v       # Enable verbose output
--version           # Show version and exit
```

The old mode names `creative`, `rigorous` and `adaptive` still resolve to `explore`, `validate` and
`auto`, but they are deprecated and emit a `DeprecationWarning`.

### UI Implementation

The CLI uses a modular UI system located in `crystalyse/ui/`:
- **chat_ui.py**: Main interactive chat interface
- **slash_commands.py**: In-session command handling
- **trace_handler.py**: Tool execution visualization
- **provenance_bridge.py**: Provenance capture and summary for each query
- **ascii_art.py**: Responsive banner logo

## Command Behavior and Agent Usage

### `crystalyse discover "query"`

**Purpose**: Non-interactive, single-shot analysis ideal for scripting

**Command Options**: `--provenance-dir`, `--hide-summary`, plus its own `--mode` and
`--project/-p`, which override the global options of the same name.

**Agent Creation** (in the `discover` command in `cli.py`):
```python
agent = EnhancedCrystaLyseAgent(
    config=config,                   # Config.load(), with --provenance-dir applied
    project_name=effective_project,  # command --project, else the global option
    mode=effective_mode.value,       # command --mode, else the global option
    model=state["model"],            # global --model
)
```

**Features**:
- Uses workspace tools with the CLI approval callback for file writes
- Prints the answer in a "Discovery Report" panel, followed by a provenance summary table
- `--hide-summary` suppresses the table; provenance is still captured

**Example Usage**:
```bash
# Quick exploratory analysis
crystalyse discover "Find perovskite solar cell materials" --mode explore

# Full validation run
crystalyse discover "Analyze CsSnI3 stability for photovoltaics" --mode validate

# Auto mode (default)
crystalyse discover "Battery cathode materials for Li-ion cells"
```

### `crystalyse chat -u user -s session`

**Purpose**: Interactive research session with enhanced UX

**Agent Creation** (via ChatExperience in ui/chat_ui.py):
```python
agent = EnhancedCrystaLyseAgent(
    config=config,
    project_name=self.project,
    mode=self.mode,
    model=self.model
)
```

**Enhanced Features**:
- **Session Persistence**: SQLite conversation store at `~/.crystalyse/sessions/<project>_<mode>.db`
- **In-Session History**: The running list of turns is also passed to `discover()` as `history`
- **Mode Switching**: `/mode` changes the mode and recreates the agent in place
- **Model Switching**: `/model` recreates the agent with a different backbone
- **Always-On Provenance**: Every query gets a provenance handler and a summary table
- `-s/--session` is appended to the project name; `-u/--user` is recorded on the session but does not currently change behaviour

**In-Session Commands**:
```bash
/help                              # Show available commands
/tools [desc|nodesc]               # List MCP tools and servers
/mcp [status|servers|desc]         # Show MCP server status and details
/stats                             # Session statistics and configuration
/memory [show|clear|refresh]       # Inspect or clear the conversation store
/mode [show|explore|validate|auto] # View or change the operating mode
/model [show|<name>]               # View the model registry or switch backbone
/about                             # Version and system information
/clear                             # Clear the terminal screen
/quit, /exit                       # Exit the session
```

Typing `quit` or `exit` without a slash also ends the loop. Nothing extra is written on the way
out: the conversation is already in the session store.

**Example Usage**:
```bash
# Start research session
crystalyse chat -u researcher1 -s battery_project

# Resume existing session  
crystalyse chat -u researcher1 -s battery_project

# Quick anonymous session
crystalyse chat
```

### `crystalyse models list` and `crystalyse models check`

**Purpose**: Inspect the model registry and confirm the required API keys are present

**Implementation**: A Typer sub-app registered on the main app; no agent is created

`models list` renders the effective registry as a table with the columns Name, Backend, Model ID,
Context, Modes, Env Var, Source and Usable. The effective registry is the built-in
`MODEL_REGISTRY` plus any `[models.<name>]` tables from `.crystalyse/config.toml`, and the Source
column reports which of the two an entry came from (built-in, user-override or user-defined).
Usable reflects whether the entry's API-key variable is set.

`models check` prints per-model environment-variable status and exits with code 1 if any model that
requires a key is missing it.

### Other Commands

- `crystalyse setup [--force]`: downloads the phase-diagram data into `~/.cache/crystalyse/`
- `crystalyse analyse-provenance [--latest | --session <id>] [--dir <path>]`: summarises a previous
  run's provenance directory (runtime, tool calls, materials found, top formation energies)

## Mode-Specific Behavior

### Auto Mode (Default)

**Agent Behavior**:
- The full unified toolset is available and the agent decides which tools a query needs
- 180-second timeout
- Default model: `openai_o4_mini`

**MCP Server Selection**: Chemistry Unified Server, unconditionally
(`MODE_MCP_SERVERS[Mode.AUTO]`). Auto is a fixed configuration, not a runtime switch between the
other two modes.

### Explore Mode

**Agent Behavior**:
- Optimised for speed: 120-second timeout
- No SMACT composition screening
- Default model: `openai_o4_mini`

**MCP Server**: Chemistry Creative Server (Chemeleon + MACE + PyMatGen)

### Validate Mode

**Agent Behavior**:
- Comprehensive validation: 300-second timeout
- Full analysis suite, with the render gate checking numerical claims
- Default model: `openai_o3`

**MCP Server**: Chemistry Unified Server (SMACT + Chemeleon + MACE + PyMatGen)

In every mode the visualisation server is started alongside the chosen chemistry server.

## Tool Coordination Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                EnhancedCrystaLyseAgent                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ MCP Server      │  │ Workspace       │  │ Session     │ │
│  │ Coordination    │  │ Tools           │  │ Store       │ │
│  │                 │  │                 │  │             │ │
│  │ • Chemistry     │  │ • read_file     │  │ • SQLite    │ │
│  │   Creative      │  │ • write_file    │  │   database  │ │
│  │ • Chemistry     │  │ • list_files    │  │ • Keyed by  │ │
│  │   Unified       │  │ • Approval      │  │   project + │ │
│  │ • Visualization │  │   callback      │  │   mode      │ │
│  │                 │  │                 │  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Integration

### Config Loading
```python
config = Config.load()  # CrystaLyseConfig, built from environment variables only
```

No YAML configuration file is read anywhere in the package. The config file that does exist is
`.crystalyse/config.toml` (project root first, then `~/.crystalyse/`), parsed by
`crystalyse/config/settings.py` into `CrystalyseSettings` (`default_model`, `default_mode`,
`plan_mode`, `plans_directory`, `plans_cleanup_days`), and — for `[models.*]` tables — by
`crystalyse/config/model_overrides.py`.

### MCP Server Selection
```python
# crystalyse/config/modes.py
MODE_MCP_SERVERS = {
    Mode.EXPLORE: "chemistry_creative",
    Mode.VALIDATE: "chemistry_unified",
    Mode.AUTO: "chemistry_unified",
}
```

### Model Selection
```python
# crystalyse/agents/agents_bridge.py
def _select_model_for_mode(self, mode: str) -> str:
    from ..config.models import resolve_model_name

    return resolve_model_name(None, mode=mode)
```

`resolve_model_name` reads `MODE_DEFAULTS` (`explore` and `auto` → `openai_o4_mini`, `validate` →
`openai_o3`) and resolves that name through the effective registry.

### Model Registry and `--model`

`--model` accepts a registry name — `openai_o4_mini`, `openai_o3`, `openai_gpt4o_mini`,
`anthropic_claude_opus`, `anthropic_claude_sonnet`, `anthropic_claude_haiku`,
`openrouter_claude_opus`, `openrouter_llama3_70b`, `mistral_large`,
`ollama_llama3_70b_direct` — or any raw LiteLLM string as an escape hatch.

- A registry name is validated against its API-key variable (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`; empty for local Ollama) and supplies
  the reasoning settings declared on the entry through `ModelConfig.agent_model_settings()`: OpenAI
  reasoning models get `reasoning=Reasoning(effort=...)`, Anthropic Claude 5 gets
  `thinking={"type": "adaptive"}` plus `output_config={"effort": ...}`, and Claude 4.x gets
  `thinking={"type": "enabled", "budget_tokens": N}`.
- Any other string passes through raw to the SDK (for example
  `litellm/openrouter/anthropic/claude-opus-4.5`), with neither key validation nor reasoning
  settings.
- `.crystalyse/config.toml` may add `[models.<name>]` tables that override value-like fields of a
  built-in entry or define a new entry. Capability fields are refused on a built-in, an invalid
  table raises `ModelOverrideError`, and project config beats user config.

Keys must be real environment variables; there is no `.env` support in the codebase. See
[Agents](agents.md#model-selection) for the full registry table.

## Best Practices

### Command Selection

**Use `discover` when**:
- Scripting or automation
- Single-shot analysis needed
- Non-interactive environment
- CI/CD pipelines

**Use `chat` when**:
- Interactive research sessions
- Building on previous work
- Learning about materials
- Complex multi-part queries

**Use `models list` / `models check` when**:
- Choosing a backbone or debugging a missing API key
- Confirming which `[models.*]` overrides are in effect

### Mode Selection

**Auto** (recommended default):
- General research scenarios
- First-time users
- Mixed exploration/validation workflows

**Explore** for:
- Rapid screening
- Initial concept exploration
- Time-sensitive analysis

**Validate** for:
- Publication-quality results
- Critical validation
- Comprehensive analysis

## Error Handling

### Agent Failures
A failed run returns `{"status": "failed", "error": ..., "query": ...}`, which the CLI prints in a
red "Discovery Failed" panel. There is no retry and no downgrade to another mode.

### Timeouts
Exceeding the mode timeout returns `{"status": "failed", "error": "The operation timed out."}`.

### MCP Server Issues
A server that fails to start is logged at `WARNING` level and the run proceeds without it: no
substitute server is started and no notice is printed. Check `crystalyse.log` when chemistry or
visualisation tools appear to be missing.

This architecture provides a robust, user-friendly interface while maintaining the flexibility and power of the underlying materials discovery platform.