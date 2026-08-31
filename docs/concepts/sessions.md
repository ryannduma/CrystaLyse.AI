# Session Management

## Overview

Crystalyse's session-based architecture enables persistent, contextual interactions for materials design research. Sessions maintain state across multiple queries, allowing for deep, exploratory analysis that builds upon previous findings.

The implementation is deliberately thin: a session is an Agents SDK `SQLiteSession`
database that the agent passes into every run. There are no session states, checkpoints,
branches, templates or sharing — see [Limitations](#limitations).

## Session Architecture

### Session Identity

`EnhancedCrystaLyseAgent` derives the session id from the project name and the mode:

```python
session_id = f"{project_name}_{mode}"     # e.g. "crystalyse_session_validate"
```

Two consequences follow. Runs that share a project name and mode share conversation
history, and changing mode moves you to a different session database. The id is built
from the mode string as supplied, before alias resolution, so constructing the agent
directly with a deprecated alias (`mode="rigorous"`) yields the id `..._rigorous` while
the run itself proceeds in `validate`. The CLI resolves the mode first, so its ids always
use the canonical name.

### Session Storage

```
~/.crystalyse/sessions/
└── <session_id>.db          # SQLite; -shm and -wal files alongside it while open
```

The directory is created on demand in the agent constructor. If `SQLiteSession` cannot be
imported from the SDK, the agent logs "conversation memory disabled" and every run starts
from scratch.

### Session Lifecycle

```
┌──────────────────────┐     ┌───────────────────────┐     ┌────────────────────┐
│ Agent constructed    │ --> │  discover() runs      │ --> │ Turns appended to  │
│ SQLiteSession opened │     │  session passed in    │     │ <session_id>.db    │
└──────────────────────┘     └───────────────────────┘     └────────────────────┘
             ^                                                        │
             └──────── clear_session_memory() deletes and reopens ────┘
```

The database persists between processes, so a later `crystalyse chat` with the same
project and mode resumes where the previous one stopped.

## Working with Sessions

### From the CLI

```bash
# Interactive chat; -s appends a session name to the project name
crystalyse --mode validate chat --user alice --session cathodes

# Same project name and mode later -> same session database
crystalyse --mode validate chat -u alice -s cathodes

# A different mode is a different session
crystalyse --mode explore chat -u alice -s cathodes

# Single-shot discovery also uses a session, named after project and mode
crystalyse --project cathodes --mode explore discover "Find stable Na-ion cathodes"
```

`--session/-s` is appended to the project name, so `--project crystalyse_session
-s cathodes` in `validate` mode gives the session id
`crystalyse_session_cathodes_validate`. `--user/-u` is accepted and stored on the chat
object, but nothing reads it today — the memory package that would use it is not wired
into the agent — so it affects neither the session id nor any file path.

### From Python

```python
from crystalyse import EnhancedCrystaLyseAgent

agent = EnhancedCrystaLyseAgent(
    project_name="cathode_materials_discovery",
    mode="validate",
)

# The session is created in the constructor and reused by every call
result = await agent.discover("Analyse LiFePO4")

# Follow-up: the session supplies the earlier turns
result = await agent.discover("What about its ionic conductivity?")

print(agent.session_id)   # "cathode_materials_discovery_validate"
```

`discover(query, history=None, trace_handler=None)` is the only query entry point.

### Clearing a Session

```python
agent.clear_session_memory()   # deletes .db/-shm/-wal, then reopens a fresh session
```

From chat:

```
/memory show     # session id, persistence status, database size
/memory clear    # confirms, then calls clear_session_memory() and drops chat history
```

## Context Management

### Two Layers of Context

Conversation context reaches the model by two independent routes:

1. **The SQLite session.** Passed to `Runner.run_streamed(..., session=session)`, it
   carries prior turns automatically and survives process restarts.
2. **The in-process `history` list.** Chat keeps `{"role", "content"}` dicts for the
   current process and passes them as `discover(query, history=...)`; the agent renders
   them into the instructions under a "Conversation History" heading. This list is not
   persisted, and `/memory clear` empties it.

### Mode and Model Switching

`/mode <name>` and `/model <name>` in chat rebuild the agent through `refresh_agent()`.
Because the session id contains the mode but not the model, `/mode` also switches session
databases while `/model` keeps the current one —
useful when you want validation work kept apart from exploration, and worth knowing when
a follow-up question suddenly lacks context.

Accepted mode names are `explore`, `validate` and `auto`. The pre-rename names
`creative`, `rigorous` and `adaptive` still resolve, with a `DeprecationWarning`, and are
scheduled for removal in v2.0.

## Provenance per Run

Sessions do not store discoveries or statistics, but each `discover()` call writes a
provenance record of its own: an event log, a materials catalogue and a summary under the
provenance output directory (`./provenance_output` by default, changed per run with
`crystalyse discover --provenance-dir`). The paths come back on the result dict under
`provenance`, and `crystalyse analyse-provenance --latest` reads the most recent one.

## Limitations

Features that a reader might reasonably expect, and which do not exist:

- No session states — nothing is "paused", "resumed" or "archived"; the database is
  simply there or not.
- No checkpoints, branching, merging or rollback.
- No session export, templates, autosave configuration or per-session statistics.
- No collaborative or multi-user sessions, permissions or share links. Crystalyse is a
  single-user local CLI, and its one user concept (`--user`) is currently inert.
- No per-session tool state. MCP servers are started and stopped inside each
  `discover()` call, and the visualisation tools take CIF content as an argument rather
  than holding a loaded structure.
- No session-specific exception types; a failed run returns
  `{"status": "failed", "error": ...}`.

!!! note "Not the session system"
    `crystalyse.infrastructure.session_manager` defines `SessionContext`,
    `PersistentSession`, `PersistentSessionManager` and `get_session_manager`, but nothing
    outside its own package imports them. It is unused code, not the session system
    described on this page.

## Best Practices

### 1. Session Hygiene

- Use `--project` (and `-s`) to keep unrelated lines of work in separate databases.
- Clear the session when switching topic; stale context costs tokens and can mislead.
- Remember that `/mode` changes which database you are talking to.

### 2. Efficient Context Management

- Keep follow-up questions in the same project and mode so the session applies.
- For a clean comparison run, clear the session first rather than rephrasing around
  earlier answers.

### 3. Durable Records

- Treat provenance output, CIF files and analysis PDFs as the durable record of a
  session; the session database is conversation state, not results.

## Next Steps

- Learn about [Tool Integration](tools.md) in sessions
- Explore [Memory Systems](memory.md) for persistence
- Check [API Reference](../reference/index.md) for detailed documentation
