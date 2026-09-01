# Agent System

## Overview

Crystalyse v1.0.0-dev uses a single agent architecture built on the OpenAI Agents SDK. The `EnhancedCrystaLyseAgent` coordinates with MCP servers and workspace tools to provide materials discovery capabilities with always-on provenance tracking.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                 EnhancedCrystaLyseAgent                      │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  OpenAI Agents SDK Integration                         │ │
│  │  • Session management (SQLite persistence)             │ │
│  │  • Tool orchestration                                  │ │
│  │  • Conversation handling                               │ │
│  └─────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │ MCP Servers     │  │ Workspace Tools  │  │ Session     │ │
│  │ (Chemistry +    │  │ (read_file,      │  │ Store       │ │
│  │ Visualisation)  │  │ write_file,      │  │ (SQLite)    │ │
│  │                 │  │ list_files)      │  │             │ │
│  └─────────────────┘  └──────────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Core Agent: EnhancedCrystaLyseAgent

**Location**: `dev/crystalyse/agents/agents_bridge.py` (re-exported from `crystalyse.agents` and `crystalyse`)

### Key Features

- **OpenAI Agents SDK Integration**: Built on the official Agents SDK with session management
- **Multi-Provider Models**: A named registry of backbones covering OpenAI, Anthropic, OpenRouter, Mistral and local Ollama
- **Provenance Tracking**: Complete audit trail of all computational operations
- **Multi-Mode Operation**: Explore (120s timeout), Auto (180s), Validate (300s)
- **Response Validation**: Render gate blocks numerical claims that carry no provenance
- **Session Persistence**: SQLite-based conversation storage

### Tool Integration

The agent coordinates with MCP servers and a small set of workspace tools:

**MCP Servers** (chemistry computations). The mode picks one chemistry server; the visualisation server is always started alongside it:

- Chemistry Creative Server (explore mode): Chemeleon + MACE + PyMatGen, no SMACT screening — 4 tools
- Chemistry Unified Server (validate and auto modes): SMACT + Chemeleon + MACE + PyMatGen — 20 tools
- Visualisation Server (all modes): 3D structure views and pymatviz analysis suites — 5 tools

A server that fails to start is logged at `WARNING` level and the run continues without it.

**Workspace Tools** (file operations). Exactly three function tools are registered:

- `read_file`: read a file from the project workspace
- `write_file`: write a file, gated by an approval callback
- `list_files`: list the project workspace

**Session Persistence**:

The SDK's `SQLiteSession` stores the conversation at `~/.crystalyse/sessions/<project>_<mode>.db`,
which gives continuity across `discover()` calls in a chat session. This is the only persistence
the agent wires up; the standalone `crystalyse.memory` package is not registered as an agent tool.

## How the Agent Works

### 1. Query Processing

The agent accepts materials discovery queries in natural language:
- "Find stable perovskite solar cell materials"
- "Analyse CsSnI3 for photovoltaics"
- "Design high-capacity battery cathodes"

### 2. Mode-Based Tool Selection

The mode is set once at agent construction and locked (`GlobalModeManager.set_mode(mode, lock_mode=True)`).
It determines which chemistry server starts and which model is used by default:

**Explore Mode** (120s timeout):
- Uses Chemistry Creative Server
- Structure generation and energies without SMACT screening
- Default model: `openai_o4_mini`
- Fast screening workflow

**Validate Mode** (300s timeout):
- Uses Chemistry Unified Server
- SMACT composition screening plus full structure, energy and stability analysis
- PyMatGen phase diagram analysis
- Default model: `openai_o3`

**Auto Mode** (default, 180s timeout):
- Uses Chemistry Unified Server
- Default model: `openai_o4_mini`
- A fixed configuration, not a runtime switch: the agent chooses which unified-server tools to call, but the mode itself never changes mid-run

The legacy names `creative`, `rigorous` and `adaptive` still resolve to `explore`, `validate` and
`auto`, but emit a `DeprecationWarning` and are scheduled for removal in v2.0.

### 3. Analysis Pipeline

Standard materials discovery workflow:

1. **Parse Query**: Extract materials specifications and requirements
2. **Composition Validation**: SMACT chemical feasibility (unified server: validate and auto modes)
3. **Structure Generation**: Chemeleon DNG prediction
4. **Energy Calculation**: MACE formation energies
5. **Stability Analysis**: PyMatGen energy above hull (unified server: validate and auto modes)
6. **Visualisation**: CIF structures, 3D structure views, pymatviz analysis suites
7. **Response Formation**: Synthesis with provenance tracking

### 4. Provenance Enforcement

Three-layer provenance system ensures computational honesty:

1. **Prompt Guidance**: Instructs agent to compute or decline
2. **Runtime Tracking**: Captures all tool outputs with metadata
3. **Render Gate**: Blocks unprovenanced numerical values from display

See [provenance_system.md](provenance_system.md) for details.

## Usage

### CLI Interface (Primary)

The agent is accessed through CLI commands:

```bash
# Non-interactive discovery
crystalyse discover "Find stable perovskites"

# Interactive chat session
crystalyse chat -u researcher -s battery_study

# With mode control (global flag, or discover's own --mode)
crystalyse --mode validate discover "Analyse CsSnI3"
crystalyse discover "Analyse CsSnI3" --mode validate

# With an explicit backbone from the model registry
crystalyse --model anthropic_claude_sonnet discover "Find stable perovskites"

# Inspect the registry
crystalyse models list
crystalyse models check
```

### Programmatic Usage

For custom integrations:

```python
import asyncio
from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import Config

async def run_discovery():
    config = Config.load()

    agent = EnhancedCrystaLyseAgent(
        config=config,
        project_name="my_research",
        mode="explore",          # "explore", "validate", or "auto"
        model="openai_o4_mini",  # a registry name, or None to take the mode default
    )

    result = await agent.discover(
        query="Find stable perovskite materials",
        history=None  # Optional conversation history
    )

    print(result["status"])       # "completed" or "failed"
    print(result["response"])     # Agent's response text
    print(result["render_gate"])  # Render gate statistics

    # Runtime and tool counts live under provenance, when a provenance handler ran
    summary = result.get("provenance", {}).get("summary", {})
    print(summary.get("total_time_s"))
    print(summary.get("tool_calls_total"))

    return result

# Run
asyncio.run(run_discovery())
```

### Interactive Sessions

The agent supports persistent sessions through the chat command:

```bash
crystalyse chat -u researcher -s battery_project
```

Features:
- Conversation history persists in a SQLite session database
- The session is keyed `<project>_<mode>`, so changing mode starts a fresh thread
- Storage lives in `~/.crystalyse/sessions/`
- `/memory clear` deletes the session database for the current agent
- `-u/--user` is recorded on the chat session but does not currently change agent behaviour

## Configuration

### Runtime Configuration

```python
from crystalyse.config import Config

# Load runtime configuration (environment variables only)
config = Config.load()

# Create agent
agent = EnhancedCrystaLyseAgent(
    config=config,
    project_name="research_project",
    mode="auto",
    model="openai_o4_mini",
)
```

`Config.load()` builds a `CrystaLyseConfig` from environment variables and the installed package
layout: MCP server commands and working directories are derived from the package base directory,
provenance and render-gate behaviour come from `CRYSTALYSE_*` variables, and the per-mode timeouts
are fixed (explore 120s, auto 180s, validate 300s). No YAML configuration file is read anywhere in
the package.

### Config File

Project settings live in `.crystalyse/config.toml`, read from the project root first and then from
`~/.crystalyse/config.toml` (the project file wins):

```toml
default_model = "openai_o4_mini"
default_mode = "explore"
plan_mode = "auto"          # "on" | "off" | "auto"
plans_directory = ".crystalyse/plans"
plans_cleanup_days = 30
```

### Model Selection

The `model=` argument accepts a name from the model registry in
`dev/crystalyse/config/models.py`:

| Name | Backend | Model ID | API key env var |
| --- | --- | --- | --- |
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

Resolution runs through `resolve_model_name()` and `resolve_model_config()`:

- A registry name is validated (its API key variable must be set) and contributes its declared
  reasoning configuration through `ModelConfig.agent_model_settings()`.
- Any other string passes through raw to the SDK. This is the escape hatch for full LiteLLM
  strings such as `litellm/openrouter/anthropic/claude-opus-4.5`, and it gets neither key
  validation nor reasoning settings.
- With `model=None` the mode default applies: explore and auto use `openai_o4_mini`, validate uses
  `openai_o3`.

The reasoning configuration is provider-specific:

- OpenAI reasoning models receive `reasoning=Reasoning(effort=...)`.
- Anthropic Claude 5 models receive `thinking={"type": "adaptive"}` plus `output_config={"effort": ...}`.
- Anthropic Claude 4.x models receive `thinking={"type": "enabled", "budget_tokens": N}`.

API keys must be real environment variables; there is no `.env` support in the codebase. On zsh,
export them from `~/.zshenv` so non-interactive shells see them too.

Registry entries can be adjusted from `.crystalyse/config.toml` with `[models.<name>]` tables:

```toml
# Override a value-like field of a built-in entry.
[models.anthropic_claude_opus]
model_id = "anthropic/claude-opus-4-6"

# Or define a new entry, which must declare its capabilities.
[models.my_local_llm]
backend = "openai-compat"
model_id = "qwen3-32b"
api_key_env_var = ""
base_url = "http://localhost:8000/v1"
supported_modes = ["explore"]
```

Capability fields (`backend`, `api_key_env_var`, `supports_tool_calling`,
`supports_structured_output`, `supported_modes`) cannot be overridden on a built-in entry, and an
invalid table raises `ModelOverrideError` at startup rather than being ignored. `crystalyse models
list` prints the effective registry, including where each entry came from.

## Agent Capabilities

### Materials Science Understanding

The agent comprehends:
- Crystal structures and space groups
- Inorganic materials chemistry
- Formation energy and thermodynamic stability
- Structure-property relationships
- Materials design principles for batteries, solar cells, etc.

### Analysis Tasks

Core capabilities:
- **Structure Prediction**: AI-based crystal structure generation (Chemeleon)
- **Energy Calculation**: Formation energies with ML force fields (MACE)
- **Composition Validation**: Chemical feasibility screening (SMACT)
- **Stability Analysis**: Energy above hull calculations (PyMatGen)
- **Visualisation**: 3D structures, XRD patterns, coordination environments

### Natural Language Interface

Understands diverse query formats:
- "Find materials for X application"
- "Analyse Y composition for Z properties"
- "Design materials with W characteristics"
- "Compare A and B for performance"

## Best Practices

### Mode Selection

**Explore Mode** - Use for:
- Initial exploration
- Broad screening
- Rapid prototyping
- Time-sensitive analysis

**Validate Mode** - Use for:
- Final validation
- Publication-quality results
- Comprehensive characterisation
- Critical design decisions

**Auto Mode** (default) - Use for:
- General research
- Unknown query complexity
- Learning the system
- Mixed workflows

### Query Formulation

**Good**: "Find perovskites with band gaps 1.2-1.6 eV"
- Specific properties
- Clear constraints

**Better**: "Design lead-free perovskite solar cell materials"
- Application context
- Material class specified

**Best**: "Find environmentally friendly perovskite alternatives to MAPbI3 for tandem solar cells"
- Complete context
- Performance requirements
- Design constraints

### Session Management

**For exploration**:
```bash
crystalyse discover "Quick query"  # Single-shot, no interactive follow-up
```

**For research projects**:
```bash
crystalyse chat -u researcher -s project_name  # Interactive, one session store per project and mode
```

Both paths write to the same conversation store: the session is keyed
`<project>_<mode>`, so repeated `discover` calls with the same project and mode
continue the same thread.

### Error Handling

The agent provides clear error messages:
- MCP server connection failures
- Invalid compositions
- Tool execution errors
- Timeout issues

Errors are logged with full context for debugging.

## Advanced Features

### Custom Trace Handlers

`discover()` streams SDK events to a trace handler. A handler needs `on_event(event)`; if it also
defines `set_user_query(query)`, the query is recorded on it before the run:

```python
import asyncio

class PrintingTraceHandler:
    def set_user_query(self, query: str) -> None:  # optional
        print(f"query: {query}")

    def on_event(self, event) -> None:
        item = getattr(event, "item", None)
        if item is not None:
            print(f"event: {getattr(item, 'type', type(event).__name__)}")

result = asyncio.run(agent.discover(query, trace_handler=PrintingTraceHandler()))
```

Passing a handler replaces the provenance handler that `discover()` would otherwise create, so
`result` will carry no `provenance` key.

### Workspace Integration

The agent uses workspace tools for file operations. `write_file` calls a module-level approval
callback, which the CLI replaces at runtime:

```python
from crystalyse.workspace import workspace_tools

# Set custom approval callback
def approve_file_write(path, content):
    print(f"About to write {len(content)} bytes to {path}")
    return True  # or False to deny

workspace_tools.APPROVAL_CALLBACK = approve_file_write
```

### Memory Access

`crystalyse.memory` is a standalone package: it is importable and usable directly, but the agent
does not register it as a tool.

```python
from crystalyse.memory import CrystaLyseMemory

memory = CrystaLyseMemory(user_id="researcher")

# Get context for agent
context = memory.get_context_for_agent()

# Store discoveries
memory.save_discovery("CsSnI3", {"formation_energy": -2.529})
```

## Performance Considerations

### Resource Usage

Runtime is bounded by the per-mode timeout, after which the run returns
`{"status": "failed", "error": "The operation timed out."}`:

| Mode | Timeout |
| --- | --- |
| `explore` | 120s |
| `auto` | 180s |
| `validate` | 300s |

Disk usage is dominated by cached model data rather than by any single run: Chemeleon checkpoints
(~604 MB) in `~/.cache/crystalyse/chemeleon_checkpoints/`, phase-diagram data (~178 MB) in
`~/.cache/crystalyse/`, and MACE foundation models in `~/.cache/mace/`.

### Optimisation

1. **Use explore mode** for initial screening
2. **Pick a cheaper backbone** (`openai_gpt4o_mini`, `anthropic_claude_haiku`) for bulk work
3. **Batch similar queries** in one chat session, which reuses the conversation store
4. **Clean old provenance data** periodically

### Monitoring

```python
result = await agent.discover(query)

summary = result.get("provenance", {}).get("summary", {})
print(summary.get("total_time_s"))      # Wall-clock runtime
print(summary.get("tool_calls_total"))  # Number of tool invocations
print(summary.get("mcp_tools"))         # Per-MCP-tool call counts
```

## Next Steps

- Learn about [Analysis Modes](analysis_modes.md) for mode selection
- Understand [Provenance System](provenance_system.md) for computational integrity
- See [Memory System](memory.md) for persistence details
