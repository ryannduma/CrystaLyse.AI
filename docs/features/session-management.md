# Session Management

## Overview

Crystalyse (v1.0.0-dev) provides session management for persistent research workflows. Sessions enable multi-day materials discovery projects with full conversation context retention.

## Core Features

### Session Persistence
- **SQLite Storage**: each session gets its own database at
  `~/.crystalyse/sessions/{session_id}.db`, created through the OpenAI Agents SDK's
  `SQLiteSession`. Clearing a session removes the `.db` plus its `-shm` and `-wal`
  companions
- **Session Identity**: `session_id = f"{project_name}_{mode}"`. The CLI derives
  `project_name` from the global `--project` plus the `-s` session name
- **Context Retention**: Full conversation history maintained
- **Cross-session Memory**: Research insights carried forward through the
  [memory system](memory-system.md)

> **The mode is part of the session identity.** Because `session_id` embeds the mode,
> switching mode with `/mode` or a different `--mode` gives you a *different* database.
> Resuming "the same session" in another mode will not restore the earlier conversation.

> **`user_id` is not part of the session identity.** Two different `-u` users on the same
> project, session name and mode read and write the same database. `user_id` scopes only
> the markdown memory files (`memory_{user_id}.md`, `insights_{user_id}.md`);
> `discoveries.json` is shared across users.

> **Conversation memory can be silently absent.** The `SQLiteSession` import is
> best-effort: if the SDK does not provide it, `self.session` is `None` and conversation
> memory is disabled with a warning ("SQLiteSession not available - conversation memory
> disabled"). The session will still run, but nothing will be remembered between turns.

### CLI Commands

`chat` accepts only two options: `-u/--user` and `-s/--session`. Mode and model are
**global** options and must precede the subcommand.

#### Starting a New Session
```bash
crystalyse --mode validate chat -u researcher1 -s battery_project
```

`crystalyse chat -m rigorous ...` does **not** work - there is no `-m/--mode` on `chat`.
(`rigorous` itself still resolves, as a deprecated alias for `validate`.)

#### Selecting a Model
```bash
crystalyse --model anthropic_claude_sonnet chat -s battery_project
```

See `crystalyse models list` for the available backbones.

#### Resume a previous session
```bash
crystalyse --mode validate chat -s battery_project -u researcher1
```

Pass the same `--mode` you started with, or you will land in a different database.

### In-Session Commands

- `/help` - Show available commands
- `/tools [desc|nodesc]` - List available MCP tools and servers
- `/mcp [status|servers|desc]` - Show MCP server status and details
- `/stats` - Session statistics and performance
- `/memory [show|clear|refresh]` - Manage agent memory and conversation history
- `/mode [show|explore|validate|auto]` - View or change the operating mode
- `/model [show|<registry name>]` - `/model show` (or bare `/model`) prints the
  registry with the current entry marked and whether each is usable; passing a name
  switches backbone and recreates the agent
- `/about` - Version and system information
- `/clear` - Clear the terminal screen (this does **not** clear the conversation - use
  `/memory clear` for that)
- `/quit`, `/exit` - Exit the session

There is no `/history`, `/undo` or `/sessions` command.

### Memory Integration

Sessions integrate with the 4-layer memory system:

1. **Session Memory**: Current conversation context
2. **Discovery Cache**: Cached computational results
3. **User Memory**: Personal preferences and notes
4. **Cross-Session Context**: Research patterns and insights

### Usage Patterns

#### Research Project Workflow
```bash
# Day 1: Start exploring battery materials
crystalyse --mode validate chat -u researcher1 -s li_ion_cathodes

# Day 2: Continue with specific compositions (same mode, same database)
crystalyse --mode validate chat -s li_ion_cathodes -u researcher1

# Day 3: Compare with previous findings in a fresh session
crystalyse --mode validate chat -u researcher1 -s comparison_study
```

#### Multi-user Collaboration
```bash
# Principal investigator starts project
crystalyse --mode validate chat -u prof_smith -s solar_perovskites

# Graduate student works in a separate session name
crystalyse --mode validate chat -u grad_student -s solar_perovskites_detailed
```

Isolation here is **partial**, and comes from the differing session names, not from the
user IDs. Because `session_id` omits `user_id`, two users sharing a project, session name
and mode share one conversation database. Give collaborators distinct `-s` names if you
want separate conversation histories; their markdown memory files are separated by `-u`
either way, and the discovery cache is shared by design.

### Implementation Details

- **Session IDs**: `f"{project_name}_{mode}"` - project and mode, not user
- **Database Schema**: owned by the OpenAI Agents SDK's `SQLiteSession`, not by Crystalyse.
  Do not depend on its layout
- **Memory Persistence**: conversation turns are written by the SDK as they happen; the
  file-based memory layers are loaded on start and the insights file is regenerated at
  teardown
- **Error Recovery**: if `SQLiteSession` is unavailable the session runs without
  conversation memory rather than failing

### Best Practices

1. **Descriptive Session Names**: Use clear, project-specific identifiers - the session
   name is what actually separates conversation histories
2. **Consistent Mode**: Resume with the same `--mode`, or you will get a different database
3. **User Separation**: Distinct `-u` IDs separate the markdown memory files; use distinct
   `-s` names to separate conversations
4. **Cache Management is Manual**: nothing expires the discovery cache. Clear it yourself
   when results go stale - the only automatic action at teardown is regenerating the
   insights file