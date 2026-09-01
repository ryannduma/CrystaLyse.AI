# Mode Switching

!!! warning "Removed feature"
    Autonomous mode switching was **removed** from Crystalyse. This page is a
    tombstone kept only so existing links resolve; it will be deleted along
    with its navigation entry. For how modes work now, see
    [Analysis Modes](analysis_modes.md).

## What was removed

Earlier documentation described a dynamic mode adapter that monitored execution
in real time and switched between analysis modes on its own, driven by user
feedback keywords, confidence scores, execution time and learned preferences.
That subsystem (`crystalyse/ui/dynamic_mode_adapter.py`, and the
`DynamicModeSuppressor` helper in the mode injector) was deleted in the same
commit that removed the clarification system.

Nothing replaced it. There is no autonomous, performance-based, confidence-based
or keyword-based mode switching anywhere in the codebase: no confidence score is
computed or stored, no `/adapt` command exists, and none of the `adaptation:` or
`ADAPTATION_CONFIG` settings that page described were ever read.

## What is true now

- The operating mode is resolved once when an agent is created and pinned for
  that agent's lifetime.
- The only way it changes is a user asking for it: `/mode explore|validate|auto`
  inside a chat session, which recreates the agent, re-arms mode injection, and
  lets the mode's default model be reselected unless `/model` has overridden it.
- On the command line the mode is set by the global `--mode` option, or by
  `discover`'s own `--mode`, which overrides the global one.
- `explore`, `validate` and `auto` are the canonical mode names; `creative`,
  `rigorous` and `adaptive` still resolve but are deprecated and will be
  removed in v2.0.

See [Analysis Modes](analysis_modes.md) for what each mode changes, and
[Agent Execution Modes](agent_modes.md) for the difference between
`crystalyse discover` and `crystalyse chat`.
