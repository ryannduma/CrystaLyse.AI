# User Interface Components

## Overview

Crystalyse provides a command-line interface designed for materials design workflows. It is a
Typer application rendered with Rich: panels for agent answers, tables for provenance and the model
registry, and an approval prompt before any file is written. There is no graphical or web UI, and
no interactive viewer — visual artefacts are written to disk by the visualisation MCP server and
opened outside Crystalyse.

## UI Architecture

### Component Structure

```
CLI (crystalyse.cli, Typer + Rich)
├── Commands
│   ├── discover            # single-shot query
│   ├── chat                # interactive session (default with no arguments)
│   ├── setup               # download phase-diagram data
│   ├── analyse-provenance  # inspect a previous run
│   └── models list|check   # inspect the model registry
├── Chat experience (ui/chat_ui.py)
│   ├── ascii_art.py          # responsive banner logo
│   ├── slash_commands.py     # in-session meta-commands
│   └── provenance_bridge.py  # per-query provenance capture
└── Output
    ├── Rich panels (answers, errors, write approval)
    ├── Rich tables (provenance summary, model registry)
    └── Files written by the visualisation MCP server (CIF, and HTML when enabled)
```

## Command-Line Interface

### Entry Points

There are two ways to reach the agent:

```bash
# Single-shot, non-interactive
crystalyse discover "Find stable perovskites"

# Interactive session
crystalyse chat
crystalyse chat -u researcher -s battery_materials

# Bare `crystalyse` inserts the chat command
crystalyse
```

Crystalyse is a subcommand application: a bare natural-language string such as
`crystalyse "What are the properties of LiCoO2?"` is parsed as a command name and fails. Natural
language belongs in `crystalyse discover "..."` or at the chat prompt.

Supporting commands:

```bash
crystalyse setup                        # download the phase-diagram data (~178 MB)
crystalyse analyse-provenance --latest  # summarise the most recent run
crystalyse models list                  # the effective model registry
crystalyse models check                 # per-model API-key status
```

### Session Banner

`crystalyse chat` opens with the box-drawing CRYSTALYSE AI logo, sized to the terminal, above a
cyan-bordered panel:

```
 ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗     █████╗ ██╗
██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║    ╚██╗ ██╔╝██╔════╝██╔════╝    ██╔══██╗██║
██║     ██████╔╝ ╚████╔╝ ███████╗   ██║   ███████║██║     ╚████╔╝ ███████╗█████╗      ███████║██║
██║     ██╔══██╗  ╚██╔╝  ╚════██║   ██║   ██╔══██║██║      ╚██╔╝  ╚════██║██╔══╝      ██╔══██║██║
╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗  ██║   ███████║███████╗    ██║  ██║██║
 ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝  ╚═╝   ╚══════╝╚══════╝    ╚═╝  ╚═╝╚═╝

╭──────────────────────────────────────────────────────────────╮
│      Your interactive materials science research partner.    │
│      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                │
│  Type your query to begin, /help for commands, or 'quit'     │
│  to exit.                                                    │
╰──────────────────────────────────────────────────────────────╯

➤
```

The prompt is `➤ `. Anything starting with `/` is dispatched as a slash command, `quit` or `exit`
ends the loop, and everything else goes to the agent unmodified — there is no preprocessing step
between the prompt and the agent.

### In-Session Commands

| Command | Purpose |
| --- | --- |
| `/help` | Show the command table |
| `/tools` | List MCP tools and servers; `nodesc` drops the description column |
| `/mcp` | MCP server status and details; takes `status`, `servers` or `desc` |
| `/stats` | Session duration, configuration and feature summary |
| `/memory` | Inspect or clear the conversation store; takes `show`, `clear` or `refresh` |
| `/mode` | View or change the operating mode; takes `show`, `explore`, `validate` or `auto` |
| `/model` | View the model registry, or switch backbone by name |
| `/about` | Version and system information |
| `/clear` | Clear the terminal screen (not the conversation) |
| `/quit`, `/exit` | Exit the session |

`/mode` and `/model` both recreate the agent in place, so the change takes effect on the next
query. `/model` with no argument prints the registry as a table (Name, Backend, Model ID, Usable)
with the current selection marked; `/model <name>` accepts any registry name or a raw model string.
`/memory clear` deletes the SQLite session database for the current agent after a confirmation
prompt.

`/tools`, `/mcp` and parts of `/stats` currently print a fixed list rather than querying the
running servers, so treat their tool counts as illustrative. `crystalyse models list` and
`crystalyse models check`, by contrast, read the live registry and environment.

## Display Components

### Conversation Panels

In a chat session each turn is framed: the query in a green `You` panel, the answer in a cyan
`CrystaLyse` panel. `crystalyse discover` prints the answer once, in a green `Discovery Report`
panel, and a failed run prints a red `Discovery Failed` panel carrying the error string.

### Provenance Summary

Every query captures provenance. `crystalyse discover` prints a summary table after the answer
unless `--hide-summary` (or `CRYSTALYSE_SHOW_PROVENANCE_SUMMARY=false`) suppresses it:

```
                  Provenance Summary
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric           ┃ Value                               ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Session ID       │ …                                   │
│ Materials Found  │ …                                   │
│ With Energy Data │ …                                   │
│ Energy Range     │ … to … eV/atom                      │
│ Runtime          │ …s                                  │
│ MCP Tools Used   │ …                                   │
│ Output Location  │ ./provenance_output/…               │
└──────────────────┴─────────────────────────────────────┘
```

The chat session prints a shorter version of the same table: Session ID, Materials Found, MCP Tool
Calls, Total Tool Calls and Output Directory, followed by the `crystalyse analyse-provenance
--session <id>` command that reopens it.

### Write Approval

The agent's `write_file` tool is gated. Before anything is written the CLI shows the first 400
characters of the content in a yellow panel and asks for confirmation:

```
╭─────────────────── 📝 Approval Required ────────────────────╮
│ <first 400 characters of the file content>                  │
╰──── About to write 1234 bytes to results/summary.md ────────╯
Do you approve this file write operation? [Y/n]:
```

### Model Registry

```
                        CrystaLyse Model Registry
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━┓
┃ Name            ┃ Backend ┃ Model ID  ┃ Context ┃ Modes ┃ Env Var ┃ Source ┃Usable┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━┩
│ openai_o4_mini  │ openai  │ o4-mini   │ 128,000 │ …     │ OPENAI… │built-in│  ✓   │
└─────────────────┴─────────┴───────────┴─────────┴───────┴─────────┴────────┴──────┘
```

The Source column distinguishes built-in entries from ones overridden or defined in
`.crystalyse/config.toml`, and Usable reports whether the entry's API-key variable is set.
`crystalyse models check` prints the same key status line by line and exits non-zero if anything
required is missing.

### Visualisation Artefacts

Crystal structures are not drawn in the terminal. The visualisation MCP server writes files
(`create_3dmol_visualization`, `create_pymatviz_analysis_suite`, `create_creative_visualization`,
`create_rigorous_visualization`, `create_mode_aligned_visualization`), and HTML output is off by
default — `CRYSTALYSE_ENABLE_HTML_VIZ` defaults to `false` and `CRYSTALYSE_CIF_ONLY` to `true` — so
the default artefact of a run is a CIF file you open in your own viewer.

## Responsive Design

The one piece of terminal adaptation is the banner. `get_responsive_logo()` measures the logo
variants against the terminal width and returns the widest that fits, in four steps, falling back
to the plain string `Crystalyse - Materials Discovery Platform` when even the smallest is too wide.
Everything else is Rich doing its own wrapping; there is no terminal capability probe, no compact
or monochrome layout, and no split-screen view.

## Configuration

There is no preferences file, theme system or alias mechanism. What exists is:

- `.crystalyse/config.toml` — project settings, read from the project root and then from
  `~/.crystalyse/` (`default_model`, `default_mode`, `plan_mode`, `plans_directory`,
  `plans_cleanup_days`), plus optional `[models.<name>]` registry overrides.
- `~/.crystalyse/sessions/` — the SQLite conversation databases, one per project and mode.
- `CRYSTALYSE_*` environment variables — provenance directory, summary display, visualisation
  output format and render-gate behaviour.

Colours are Rich style strings written at each call site.

## Extending the UI

The extension point is the trace handler. `agent.discover()` streams SDK events and calls
`on_event(event)` on the handler it is given; if the handler also defines `set_user_query(query)`,
the query is recorded on it before the run starts:

```python
class PrintingTraceHandler:
    def set_user_query(self, query: str) -> None:  # optional
        print(f"query: {query}")

    def on_event(self, event) -> None:
        item = getattr(event, "item", None)
        if item is not None:
            print(f"event: {getattr(item, 'type', type(event).__name__)}")

results = await agent.discover(query, trace_handler=PrintingTraceHandler())
```

Streaming is driven by `Runner.run_streamed` inside the agent, not by the UI. Passing your own
handler replaces the provenance handler `discover()` would otherwise create, so the result will
carry no `provenance` key — `CrystaLyseProvenanceHandler` in `ui/provenance_bridge.py` is the
reference implementation to build on if you want both.

## Best Practices

### 1. Choose the Entry Point to Match the Task

`discover` for scripting and single questions; `chat` when the next question depends on the last
answer, since the session store keeps the thread.

### 2. Keep Provenance Visible

The summary table is where runtime, tool calls and the output directory live. Hide it with
`--hide-summary` only in automation — the data is still captured either way, and
`analyse-provenance` can reopen it later.

### 3. Read Errors From the Panel, Details From the Log

A failed run prints its error string in a red panel. Anything below that — an MCP server that did
not start, for instance — is logged at `WARNING` level to `crystalyse.log` rather than shown.

## Next Steps

- Learn about [Session Management](sessions.md) for persistent interfaces
- Explore [Tool Integration](tools.md) for extended functionality
- Check [API Reference](../reference/index.md) for detailed documentation
