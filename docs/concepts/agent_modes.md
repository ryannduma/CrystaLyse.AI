# Agent Execution Modes

## Overview

Crystalyse can be driven in two ways: a single-shot, non-interactive command and an interactive chat session. Both drive the same `EnhancedCrystaLyseAgent`, so they have identical chemistry capabilities; they differ in how queries are supplied and in how much of a conversation is in play. The scientific *operating* mode (`explore`, `validate`, `auto`) is a separate axis - see [Analysis Modes](analysis_modes.md).

## Agent Modes

### Discover Mode (Non-Interactive)

**Purpose**: Single-shot discovery with direct results
**Execution**: One query per process, then exit
**Memory**: A SQLite conversation store keyed by project name and operating mode, reused by later runs with the same key
**Best for**: Scripted runs, batch processing, one-off questions

#### Characteristics
- **One Query per Invocation**: The query is a command-line argument, not a prompt
- **Direct Results**: The answer and a provenance summary are printed, then the process exits
- **Script-Friendly**: Suitable for automated workflows and shell loops
- **Provenance Always On**: Every run writes an audit trail (default `./provenance_output`)
- **Session-Backed**: The agent opens `~/.crystalyse/sessions/<project>_<mode>.db` on construction, so successive runs sharing a project and mode continue the same conversation store

#### CLI Usage
```bash
# Basic single-shot discovery
crystalyse discover "Design a high-capacity Li-ion cathode material"

# Validate mode - full validation pipeline
crystalyse discover "Find stable perovskites for solar cells" --mode validate

# Keep a scripted run in its own workspace and conversation store
crystalyse discover "Thermoelectric materials with high ZT" --project batch_run

# Custom provenance directory, no summary table
crystalyse discover "Screen Na-ion cathodes" --provenance-dir ./my_research --hide-summary
```

`discover` takes `--mode`, `--project`/`-p`, `--provenance-dir` and `--hide-summary`. `--mode`, `--project` and `--model` also exist as global options on the `crystalyse` callback and must precede the subcommand; `discover`'s own `--mode` and `--project` override the global values. There is no user flag on `discover` - separate scripted runs are kept apart with `--project`, which is what keys both the workspace and the session database.

The full command set is `discover`, `setup`, `chat`, `analyse-provenance`, and the `models` sub-app (`models list`, `models check`).

#### Python API Usage
```python
import asyncio

from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import Config


async def main():
    agent = EnhancedCrystaLyseAgent(
        config=Config.load(),
        project_name="battery_project",
        mode="validate",
    )

    result = await agent.discover("Design cathode materials for sodium-ion batteries")

    if result["status"] == "completed":
        print(result["response"])
    else:
        print("Failed:", result["error"])


asyncio.run(main())
```

`EnhancedCrystaLyseAgent` is the only public agent class. It can be imported from `crystalyse.agents.agents_bridge`, from `crystalyse.agents`, or from `crystalyse` directly. Its constructor takes `config`, `project_name`, `mode` and `model`; `config` is the `CrystaLyseConfig` object (aliased `Config`) returned by `Config.load()`, and all four arguments are optional.

MCP servers are started and shut down inside `discover()` by an internal `AsyncExitStack`, so callers have no teardown step to run.

A successful call returns:

```python
{
    "status": "completed",
    "query": "...",
    "response": "...",          # the human-readable answer
    "render_gate": {...},       # render-gate statistics
    # "provenance": {...}       # present when a provenance-aware trace handler was used
}
```

A failed or timed-out call returns `{"status": "failed", "error": ..., "query": ...}`.

#### Workflow Pattern
```
User Query → Agent Processing → MCP Tool Calls → Render Gate → Output
    ↓              ↓                  ↓              ↓          ↓
  "Design      Instructions      SMACT/          Screen for   Text +
   battery     + mode + tool     Chemeleon/      unprovenanced provenance
   cathode"    selection         MACE calls      numbers      summary
```

### Chat Mode (Interactive Sessions)

**Purpose**: Interactive research sessions over many turns
**Execution**: A read-eval-print loop around the same agent
**Memory**: In-process turn history plus the same persistent SQLite session store
**Best for**: Research projects, exploratory analysis, follow-up questions

#### Characteristics
- **Conversation History**: Each turn's history is passed back into the agent's instructions
- **Session Persistence**: The agent's SQLite store keeps turns across restarts of the same project and mode
- **Context Continuity**: Follow-up questions build on earlier answers in the same session
- **Meta Commands**: Slash commands for tools, MCP status, memory, mode and model
- **Per-Query Provenance**: A provenance summary is printed after every answer

#### CLI Usage
```bash
# Start an interactive session (also what bare `crystalyse` runs)
crystalyse chat

# Named research session
crystalyse chat -s battery_research

# Resume it later - the same project and session name reopen the same store
crystalyse chat -s battery_research

# Choose the operating mode (a global option, so it precedes the subcommand)
crystalyse --mode validate chat -s battery_research
```

`chat` accepts only `--user`/`-u` and `--session`/`-s`. `--session` is appended to the project name, which is what keys the workspace and the session database. `--user` is recorded on the chat session object but is not otherwise read: it does not partition memory, workspaces or sessions, so there is no multi-user separation to rely on.

#### Session Commands (within chat)
```bash
/help                         # Show the command table
/tools [desc|nodesc]          # List MCP tools and servers
/mcp [status|servers|desc]    # MCP server status and details
/stats                        # Session statistics and performance
/memory [show|clear|refresh]  # Inspect or clear conversation memory
/mode [show|explore|validate|auto]  # View or change the operating mode
/model [show|<name>]          # View or change the model backbone
/about                        # Version and system information
/clear                        # Clear the terminal screen
/quit, /exit                  # Exit the session
```

Typing `quit` or `exit` without a slash also exits. Note that `/clear` clears the *screen*: to clear the conversation itself use `/memory clear`, which deletes the SQLite session after a confirmation prompt and empties the in-session history.

#### Python API Usage
```python
import asyncio

from crystalyse.ui.chat_ui import ChatExperience

chat = ChatExperience(project="battery_research", mode="validate", model=None)
asyncio.run(chat.run_loop())
```

`ChatExperience` keeps a plain list of turns in `self.history` and calls `agent.discover(query, history=self.history, trace_handler=...)` for each one. Longer-term continuity comes from the agent's own `SQLiteSession`, not from a separate session manager.

#### Workflow Pattern
```
User Query → Turn History → Agent Processing → SQLite Session → Response
    ↓             ↓               ↓                  ↓             ↓
 "What about   Previous       Instructions +     Store the      Contextual
  stability?"  LiCoO₂ turn    MCP tool calls     exchange       answer
```

## Mode Comparison

| Aspect | Discover Mode | Chat Mode |
|--------|---------------|-----------|
| **Invocation** | `crystalyse discover "<query>"` | `crystalyse chat` (also bare `crystalyse`) |
| **Turns per process** | One | Many |
| **In-process history** | None | Turn list fed back into instructions |
| **Persistent store** | `~/.crystalyse/sessions/<project>_<mode>.db` | Same file, same keying |
| **Meta commands** | None | Slash commands |
| **Provenance** | Summary per run (`--hide-summary` to suppress) | Summary after each answer |
| **Operating mode** | Global `--mode`, or `discover --mode` | Global `--mode`, changeable with `/mode` |
| **Model** | Global `--model` | Global `--model`, changeable with `/model` |
| **Use case** | Automation, batch | Research, exploration |

## Choosing the Right Mode

### Use Discover Mode When:
- **One-off Questions**: A single analysis is all you need
- **Batch Processing**: Many queries driven from a script
- **Automated Workflows**: Non-interactive pipelines and CI
- **Reproducible Runs**: One command, one provenance directory
- **Isolated State**: A dedicated `--project` keeps a run's session out of your interactive one

### Use Chat Mode When:
- **Research Projects**: Extended investigation over many turns
- **Exploratory Analysis**: Building on previous answers
- **Learning/Teaching**: Interactive walk-throughs
- **Complex Queries**: Multi-step workflows where follow-ups matter
- **Mode/Model Tuning**: Switching between `explore` and `validate` mid-session

## Operating Mode and Model Selection

Execution mode (discover vs chat) is independent of the operating mode. The global `--mode` option accepts `explore`, `validate` and `auto` and defaults to `auto`; the legacy names `creative`, `rigorous` and `adaptive` still resolve, but emit a `DeprecationWarning` saying they will be removed in v2.0.

The operating mode also chooses the default model backbone:

| Mode | Default backbone | Model ID |
|------|------------------|----------|
| `explore` | `openai_o4_mini` | `o4-mini` |
| `auto` | `openai_o4_mini` | `o4-mini` |
| `validate` | `openai_o3` | `o3` |

A `--model` value overrides that default for the whole run, and inside chat `/model <name>` overrides it for the session (both recreate the agent). Names come from the model registry, which also carries OpenAI `gpt-4o-mini`, Anthropic Claude Opus 5 / Sonnet 5 / Haiku 4.5, OpenRouter, Mistral and local Ollama entries; an unrecognised string is passed through to the SDK unchanged.

```bash
# Inspect the registry: Name, Backend, Model ID, Context, Modes, Env Var, Source, Usable
crystalyse models list

# Check that the required API keys are actually set (non-zero exit if any is missing)
crystalyse models check

# Run one query on a named backbone
crystalyse --model anthropic_claude_sonnet discover "Screen Na-ion cathodes" --mode explore
```

Some registry entries restrict which modes they support - for example `anthropic_claude_haiku` and `openrouter_llama3_70b` are `explore`/`auto` only, and `ollama_llama3_70b_direct` is `explore` only. API keys are read from real environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`); there is no `.env` file support.

A project can also add or adjust registry entries with `[models.<name>]` tables in `.crystalyse/config.toml` (project config beats user config). Value-like fields of a built-in entry can be overridden and new backbones defined; capability fields cannot be overridden on a built-in, and an invalid table raises `ModelOverrideError` at startup rather than being ignored.

## Technical Implementation

### The Agent
```python
class EnhancedCrystaLyseAgent:
    """UI-agnostic backend: manages MCP servers and answers queries."""

    def __init__(self, config=None, project_name="crystalyse_session",
                 mode="auto", model=None):
        # Resolve the mode, open the SQLite session, pin the mode globally
        ...

    async def discover(self, query, history=None, trace_handler=None) -> dict:
        # Start MCP servers, run the SDK agent, apply the render gate,
        # return {"status": ..., "response": ..., "render_gate": ...}
        ...

    def clear_session_memory(self) -> bool:
        # Delete and recreate the SQLite session store
        ...
```

The remaining methods are internal: `_managed_mcp_servers`, `_select_model_for_mode` and `_create_enhanced_instructions`.

### The Chat Loop
```python
class ChatExperience:
    """Interactive session around one EnhancedCrystaLyseAgent."""

    def __init__(self, project: str, mode: str, model: str, user_id: str = "default"):
        self.history: list[dict] = []
        self.agent = None  # created in run_loop()

    def refresh_agent(self):
        # Re-arm mode injection and rebuild the agent (used by /mode and /model)
        ...
```

## Session Memory

Both execution paths use the same mechanism, and only that one:

- **One store per project and mode**: `~/.crystalyse/sessions/<project_name>_<mode>.db`, opened when the agent is constructed
- **Shared across runs**: Two `crystalyse discover` invocations with the same project and mode continue the same store; changing either starts a different one
- **Turn history in chat**: In addition, the chat loop passes the current session's turns into the agent's instructions
- **Cleared explicitly**: `/memory clear` deletes the database and empties the in-session history; `/memory show` reports the session ID and database size

There is no discovery cache, cross-session learning or preference model in the live code path - the `crystalyse.memory` package exists but is not wired into the agent.

## Best Practices

### Discover Mode Best Practices
1. **Clear Queries**: State the target, chemistry and constraints in the one query
2. **Name the Project**: Use `--project` so batch runs do not share a store with your chat sessions
3. **Keep the Provenance**: `--provenance-dir` per study makes runs easy to audit later
4. **Pick the Mode Deliberately**: `--mode validate` for results you intend to report

### Chat Mode Best Practices
1. **Session Names**: Use descriptive `-s` names; they key the store you will resume
2. **Switch Modes Explicitly**: `/mode validate` when a promising result needs checking
3. **Watch the Model**: `/model show` after a `/mode` change - the mode's default is reselected unless you have overridden it
4. **Reset Between Topics**: `/memory clear` when starting an unrelated investigation

## Integration Patterns

### Continuing a Batch Run Interactively
```bash
# Scripted pass
crystalyse -p battery_project discover "Screen high-capacity Na-ion cathodes"

# Same project and mode, so the chat session opens the same conversation store
crystalyse -p battery_project chat
```

### API Integration
```python
from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import Config


@app.post("/materials/analyse")
async def analyse_material(query: str):
    agent = EnhancedCrystaLyseAgent(
        config=Config.load(),
        project_name="web_api",
        mode="validate",
    )
    result = await agent.discover(query)
    return result
```

MCP servers are started per `discover()` call and shut down when it returns, so the endpoint needs no cleanup step. Note that every agent sharing a project name and mode also shares one SQLite session file; give concurrent callers distinct project names if they must not share history.

## Performance Considerations

Each operating mode has a timeout, and these are the only per-mode timing numbers in the code. They are ceilings, not expected runtimes: exceeding one returns `{"status": "failed", "error": "The operation timed out."}`.

| Mode | Timeout |
|------|---------|
| `explore` | 120 s |
| `auto` | 180 s |
| `validate` | 300 s |

Actual runtime depends on the query, the model backbone and whether Chemeleon and MACE run on GPU. Startup cost is dominated by launching the MCP servers, which both execution paths pay; chat pays it once per agent, discover pays it once per invocation.

## Next Steps

- Explore [Analysis Modes](analysis_modes.md) for explore, validate and auto workflows
- Learn [Session Management](sessions.md) for chat mode operation
- Check [Memory Systems](memory.md) for persistence details
- Review [CLI Usage Guide](../guides/cli_usage.md) for practical examples
