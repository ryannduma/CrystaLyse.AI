# Clarification System (Removed)

!!! warning "Removed feature"
    The clarification system was **removed** from Crystalyse and nothing
    replaced it. This page is kept as a record so that links and bookmarks to
    it resolve rather than 404. Queries now go straight to the agent.

## What was removed

Crystalyse used to preprocess every query through an adaptive clarification
stage: it estimated the user's expertise, asked expertise-appropriate
questions, proposed assumptions for confirmation, and picked an operating mode
from the answers. That subsystem lived in
`crystalyse/ui/enhanced_clarification.py` and was deleted outright, together
with:

- the CLI's `non_interactive_clarification` function and `CLARIFICATION_CALLBACK` wiring,
- every clarification preprocessing method in the chat UI,
- the dynamic mode adapter that switched modes from feedback keywords,
- the `user_stats` command that reported the per-user preference profile.

`crystalyse/ui/user_preference_memory.py` still exists but is marked deprecated,
exports nothing, and is not imported anywhere; the expertise levels,
`speed_preference`, `successful_modes` and `domain_familiarity` fields that
earlier documentation described are not read by anything. The
`IntegratedClarificationSystem` API, and the `--clarification-style`,
`--no-clarification` and `--expertise` flags that page documented, do not exist -
`crystalyse chat` accepts only `--user`/`-u` and `--session`/`-s`.

## What happens instead

Nothing sits between you and the agent. Both entry points call
`agent.discover(...)` with the query exactly as typed:

- `crystalyse discover "<query>"` runs it once, non-interactively.
- `crystalyse chat` passes each turn straight through, with the session's
  history attached.

Because there is no clarification pass, a vague query is answered as a vague
query. State what you want validated, over which chemistry, and under which
constraints, in the query itself - and pick the operating mode deliberately
(`--mode explore` for a fast pass, `--mode validate` for the full pipeline).

A plan mode is scaffolded in configuration (`plan_mode` in
`.crystalyse/config.toml`) but is not implemented, so it is not a replacement
for clarification today.

## Where to look instead

- [Analysis Modes](analysis_modes.md) - what `explore`, `validate` and `auto` change
- [Agent Execution Modes](agent_modes.md) - `crystalyse discover` versus `crystalyse chat`, and the slash commands a chat session really has
