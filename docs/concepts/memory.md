# Memory Systems

!!! warning "Experimental Preview"
    The `crystalyse.memory` package described below is implemented but is **not yet wired
    into the agent**: nothing in `crystalyse.agents` imports it. The memory the agent
    actually uses today is the Agents SDK `SQLiteSession` described under
    [Conversation Memory](#conversation-memory). APIs and behaviour may change.

## Overview

Crystalyse implements memory systems that enable agents to maintain context, learn from interactions, and build upon previous discoveries. The memory architecture is designed specifically for materials design research workflows.

Its guiding principle is stated in the package itself: *simple files + smart context beats
complex architectures*. Everything lives in plain files under `~/.crystalyse` — there is no
database server, no vector index and no external service.

## Memory Architecture

### Layered Memory Structure

```
┌────────────────────────────────────────┐
│         SessionMemory (L1)             │
│   (Recent turns, in RAM, max 10)       │
├────────────────────────────────────────┤
│        DiscoveryCache (L2)             │
│   (~/.crystalyse/discoveries.json)     │
├────────────────────────────────────────┤
│          UserMemory (L3)               │
│   (~/.crystalyse/memory_<user>.md)     │
├────────────────────────────────────────┤
│      CrossSessionContext (L4)          │
│   (~/.crystalyse/insights_<user>.md)   │
└────────────────────────────────────────┘
```

## Memory Types

### 1. Session Memory

Short-term memory for the current conversation:
- Recent `(query, response, timestamp)` triples
- Held in RAM only, never written to disk
- Capped at `max_interactions=10`, oldest dropped first
- `get_context(last_n=3)` formats the recent turns for the agent

**Characteristics:**
- High-speed access
- Limited capacity
- Cleared when the process ends, or via `clear_session()`
- Optimised for performance

### 2. Discovery Cache

Cached results for expensive calculations:
- Keyed on chemical formula (`"LiCoO2"`), not on free text
- Each entry stores `formula`, `properties`, `timestamp` and `cached_at`
- Backed by a single JSON file, `~/.crystalyse/discoveries.json`
- Avoids re-running MACE, Chemeleon and SMACT for a formula already seen

**Characteristics:**
- Persistent across sessions
- Exact-formula lookup via `get_cached_discovery(formula)`
- Substring search over formulas and property text via `search_discoveries(query, limit)`
- Exportable and importable as JSON

### 3. User Memory

Personalised memory for each user:
- A human-readable markdown file, `~/.crystalyse/memory_<user_id>.md`
- Sections for preferences, research interests, recent discoveries, patterns and notes
- Written with `save_to_memory(fact, section="Important Notes")`
- Searched with `search_memory(query)`

**Characteristics:**
- User-specific file naming
- Plain markdown, editable by hand
- Enables personalisation
- Read back as agent context

### 4. Cross-Session Context

Auto-generated long-term summaries:
- Weekly summaries of discoveries and recurring patterns
- Stored as `~/.crystalyse/insights_<user_id>.md`
- `generate_weekly_summary()` builds one on demand
- `auto_generate_insights()` builds one only when the insights file is missing or at least 7 days old

**Characteristics:**
- Derived from the discovery cache and user memory
- Markdown, not a graph or an embedding store
- Surfaced in agent context as "Recent Research Context"

## Memory Implementation

### Storage

There is one storage backend: files.

```python
# All four layers share a directory (default: ~/.crystalyse)
~/.crystalyse/
├── discoveries.json         # DiscoveryCache
├── memory_<user_id>.md      # UserMemory
└── insights_<user_id>.md    # CrossSessionContext
# SessionMemory is in-process only
```

### Memory Entry Point

`CrystaLyseMemory` composes the four layers:

```python
from crystalyse.memory import CrystaLyseMemory

memory = CrystaLyseMemory(user_id="default", memory_dir=None)  # default ~/.crystalyse

memory.session_memory          # SessionMemory
memory.discovery_cache         # DiscoveryCache
memory.user_memory             # UserMemory
memory.cross_session_context   # CrossSessionContext
```

The package exports `SessionMemory`, `DiscoveryCache`, `UserMemory`,
`CrossSessionContext`, `CrystaLyseMemory`, `save_to_memory`, `search_memory`,
`save_discovery`, `search_discoveries` and `get_memory_tools`.

## Memory Operations

### Storing Information

```python
# Record a conversation turn (session layer)
memory.add_interaction(
    query="Analyse LiFePO4 for battery applications",
    response=result["response"],
)

# Cache a discovery, keyed by formula
memory.save_discovery(
    formula="LiFePO4",
    properties={
        "formation_energy": -2.345,
        "unit": "eV/atom",
        "space_group": "Pnma",
    },
)

# Note a durable fact about the user's work
memory.save_to_memory(
    "Avoid Co-containing cathodes for this project",
    section="Important Notes",
)
```

### Retrieving Information

```python
# Exact formula lookup in the cache
cached = memory.get_cached_discovery("LiFePO4")

# Substring search across cached discoveries
discoveries = memory.search_discoveries("phosphate", limit=5)

# Search the user's markdown memory
notes = memory.search_memory("cathode")
```

### Building Context

`get_context_for_agent()` concatenates whatever the layers have to offer:

```python
context = memory.get_context_for_agent()

# Context includes, when non-empty:
# - "Previous Conversation"   (session memory, last few turns)
# - "User Profile"            (user memory summary)
# - "Recent Research Context" (cross-session insights)
# - "Recent Discoveries"      (up to 3 recent cache entries)
```

## Memory Tools

Eight memory functions are decorated with `@function_tool` and collected by
`get_memory_tools(user_id)`, ready to be handed to an agent. Nothing calls
`get_memory_tools()` today, so they are available but not yet attached to a run:

| Tool | Purpose |
| ---- | ------- |
| `save_to_memory(fact, section)` | Append a fact to the user's markdown memory |
| `search_memory(query)` | Search that markdown memory |
| `save_discovery(formula, properties)` | Cache a result for a formula |
| `search_discoveries(query, limit)` | Search the discovery cache |
| `get_cached_discovery(formula)` | Exact-formula cache lookup |
| `get_memory_context()` | The combined context string above |
| `generate_weekly_summary()` | Build and store a weekly insights summary |
| `get_memory_statistics()` | Counts across all four layers |

## Conversation Memory

What the agent uses today is separate from the package above. `EnhancedCrystaLyseAgent`
creates an Agents SDK `SQLiteSession` in its constructor and passes it into every run:

```python
session_id = f"{project_name}_{mode}"
# ~/.crystalyse/sessions/<session_id>.db
```

That database carries the conversation across successive `discover()` calls, which is
what makes follow-up questions work in chat. If `SQLiteSession` cannot be imported the
agent logs "conversation memory disabled" and runs stateless.

From chat, `/memory` inspects and clears it:

```
/memory show     # session id, whether persistence is enabled, database size
/memory clear    # deletes the .db/-shm/-wal files and recreates the session
/memory refresh  # prints a refresh message; placeholder, changes nothing
```

`/memory clear` calls `agent.clear_session_memory()`, the only session mutation the agent
exposes.

## Statistics and Maintenance

```python
stats = memory.get_memory_statistics()
# user_id, memory_directory, session summary, cache stats,
# counts of user preferences / research interests / recent discoveries,
# and whether an insights file exists

memory.clear_session()          # drop in-RAM conversation turns
memory.cleanup()                # clear session, then auto-generate insights if due
```

### Export and Import

```python
from pathlib import Path

memory.export_memory(Path("./memory_backup"))
# writes discoveries.json, memory_<user>.md, insights_<user>.md

memory.import_memory(Path("./memory_backup"), merge=True)
```

## Privacy

- Everything is local: files under `~/.crystalyse`, no server, no upload.
- Per-user separation is by filename (`memory_<user_id>.md`, `insights_<user_id>.md`);
  the discovery cache is shared across users of the same machine account.
- There is no encryption at rest and no retention policy — files persist until deleted.

## Best Practices

### 1. Memory Hygiene

- Keep discovery-cache entries keyed by the exact formula you will search for later.
- Edit `memory_<user_id>.md` by hand when a preference changes; it is just markdown.
- Clear the conversation session (`/memory clear`) when switching to an unrelated topic.

### 2. What to Trust

- Cached properties are whatever was written at the time; re-run the calculation if the
  underlying model or checkpoint has changed.
- Weekly insights are generated by summarising the cache — they inherit its gaps.

## Next Steps

- Explore [Session Management](sessions.md) for conversation handling
- Learn about [Agent Integration](agents.md) with memory systems
- Check [API Reference](../reference/index.md) for detailed documentation
