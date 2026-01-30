# Legacy UI Components

Archived: 2026-01-30

These files were part of an older `ChatExperience` system that was replaced by:
- `crystalyse/cli.py` - Main Typer CLI with `chat` command
- `crystalyse/ui/clarification.py` - Simplified V2 clarification system

## Why Archived

The V2 architecture uses a simpler approach:
- Mode selection via `--rigorous` flag (not auto-detected)
- Skills-based tool execution (not MCP servers)
- Session persistence via SQLite (not custom memory)

These files implemented:
- `ChatExperience` class with complex mode detection
- `IntegratedClarificationSystem` with expertise scoring
- `DynamicModeAdapter` for automatic mode switching
- `UserPreferenceMemory` for learning user preferences
- Various trace handlers for tool output formatting

## Files

| File | Lines | Purpose |
|------|-------|---------|
| chat_ui.py | 850 | Main ChatExperience class |
| enhanced_clarification.py | 1500 | Complex clarification with LLM |
| dynamic_mode_adapter.py | 400 | Auto mode detection |
| user_preference_memory.py | 300 | User preference learning |
| ascii_art.py | 180 | Terminal logo/art |
| slash_commands.py | 700 | /help, /mode, etc. commands |
| trace_handler.py | 220 | Tool execution formatting |
| enhanced_trace_handler.py | 470 | Enhanced trace output |
| enhanced_trace_handler_v2.py | 600 | V2 trace output |
| enhanced_result_formatter.py | 310 | Result formatting |
| provenance_bridge.py | 200 | Provenance integration |
| progress.py | 60 | Progress indicators |

## Restoration

If needed, these can be restored to `dev/crystalyse/ui/`:
```bash
cp archive/ui-legacy/*.py dev/crystalyse/ui/
```
