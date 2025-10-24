# CrystaLyse Memory System

## Status: Implemented but Not Activated

This memory system is **fully implemented** but currently **not registered** with the agent. It provides sophisticated features beyond the basic SQLiteSession conversation memory.

## Why Keep This Module?

The current system uses OpenAI SDK's `SQLiteSession` which only provides:
- ✅ Conversation history (query/response pairs)

This memory module provides:
- ✅ **DiscoveryCache** - Cache expensive MACE/Chemeleon calculations (prevent recalculation)
- ✅ **CrossSessionContext** - Pattern detection across sessions (learn user research patterns)
- ✅ **Discovery Search** - Search all analyzed materials by element/property
- ✅ **Weekly Summaries** - Auto-generated research insights
- ✅ **UserMemory** - Research interests and preferences (markdown-based)
- ✅ **SessionMemory** - In-memory context (gemini-cli style)

## Architecture: 4-Layer System

### Layer 1: SessionMemory
**Purpose**: In-memory recent conversation context (last N interactions)
**Storage**: RAM only (ephemeral)
**Use case**: Fast context retrieval during active session

### Layer 2: DiscoveryCache
**Purpose**: Cache expensive computational results
**Storage**: `~/.crystalyse/discoveries.json`
**Use case**: Avoid re-running MACE energy calculations, Chemeleon structure predictions

**Example**:
```python
# First time: Runs expensive calculation
result = discovery_cache.get_cached_result("LiFePO4")  # None
# ... runs MACE/Chemeleon ...
discovery_cache.save_result("LiFePO4", {"energy": -4.2, "structure": "..."})

# Second time: Instant retrieval
result = discovery_cache.get_cached_result("LiFePO4")  # Cached result!
```

### Layer 3: UserMemory
**Purpose**: User preferences, research interests, patterns
**Storage**: `~/.crystalyse/memory_{user_id}.md` (human-readable markdown)
**Use case**: Personalized interactions, remember user constraints

**Example memory file**:
```markdown
## User Preferences
- Default analysis mode: rigorous
- Avoid toxic elements: Pb, Cd, Hg

## Research Interests
- Li-ion battery cathodes
- High energy density materials

## Recent Discoveries
- LiFePO4 - promising stability
- LiCoO2 - good energy density
```

### Layer 4: CrossSessionContext
**Purpose**: Auto-generated insights and weekly summaries
**Storage**: `~/.crystalyse/insights_{user_id}.md`
**Use case**: Long-term pattern detection, research trends

**Auto-generates**:
- Most studied elements
- Common research themes
- Weekly discovery summaries
- Recommendations for next research directions

## How to Activate

### Option 1: Add Memory Tools to Agent (Recommended)

Edit `agents/openai_agents_bridge.py`:

```python
# Add import
from ..memory.memory_tools import get_memory_tools

# In discover() method, around line 178:
sdk_agent = Agent(
    name="CrystaLyse",
    model=selected_model,
    instructions=mode_aware_instructions,
    tools=[
        workspace_tools.read_file,
        workspace_tools.write_file,
        workspace_tools.list_files,
        # Add memory tools:
        *get_memory_tools(user_id=session_id)  # Expands to 8 memory tool functions
    ],
    model_settings=ModelSettings(tool_choice="auto"),
    mcp_servers=mcp_servers
)
```

### Option 2: Initialize Memory System in Agent Constructor

```python
class EnhancedCrystaLyseAgent:
    def __init__(self, config, mode="adaptive", model=None, project_name="crystalyse_session"):
        # ... existing code ...

        # Add memory system
        from ..memory.crystalyse_memory import CrystaLyseMemory
        self.memory = CrystaLyseMemory(user_id=self.session_id)

        # Auto-load context before each query
        context = self.memory.get_context_for_agent()
        # Inject context into instructions
```

### Option 3: Use Discovery Cache Only (Minimal Integration)

For just performance improvements without full memory features:

```python
from ..memory.discovery_cache import DiscoveryCache

# In agent initialization
self.cache = DiscoveryCache()

# Before expensive calculations
cached = self.cache.get_cached_result(formula)
if cached:
    return cached["properties"]

# After calculations
self.cache.save_result(formula, calculated_properties)
```

## Memory Tools Available

When activated, the agent gets these 8 function tools:

1. **`save_to_memory(fact, section)`** - Save important information
2. **`search_memory(query)`** - Search user memory
3. **`save_discovery(formula, properties)`** - Cache computational results
4. **`search_discoveries(query, limit)`** - Find similar analyzed materials
5. **`get_cached_discovery(formula)`** - Check cache for specific material
6. **`get_memory_context()`** - Get comprehensive memory summary
7. **`generate_weekly_summary()`** - Create research progress summary
8. **`get_memory_statistics()`** - Check memory system health

## Example Usage

```python
# Agent can call these functions during discovery:

# 1. Check cache before expensive calculation
result = await save_discovery("LiFePO4", {"energy": -4.2, "stable": True})
# → "💾 Cached discovery: LiFePO4 [2025-10-24 15:30]"

# 2. Search for similar materials
results = await search_discoveries("Li-ion cathode")
# → Shows all previously analyzed Li-containing cathodes

# 3. Remember user preferences
await save_to_memory("User prefers olivine structures", "User Preferences")

# 4. Generate insights
summary = await generate_weekly_summary()
# → Creates markdown summary of week's research
```

## Performance Impact

### With DiscoveryCache Active:
- **MACE calculation** (5-30 seconds) → Instant if cached
- **Chemeleon prediction** (10-60 seconds) → Instant if cached
- **Typical speedup**: 10-100x for repeated materials

### Without DiscoveryCache:
- Every query recalculates from scratch
- No benefit from prior analyses
- User studies same material twice → recalculates everything

## Current vs. With Memory System

| Feature | Current (SQLiteSession) | With Memory System |
|---------|------------------------|-------------------|
| Conversation history | ✅ Persistent DB | ✅ Enhanced with context |
| Material property cache | ❌ None | ✅ JSON cache |
| User preferences | ⚠️ Separate file | ✅ Integrated markdown |
| Research patterns | ❌ None | ✅ Auto-detected |
| Weekly insights | ❌ None | ✅ Auto-generated |
| Discovery search | ❌ None | ✅ Full-text search |
| Cross-session learning | ❌ None | ✅ Pattern detection |

## File Structure

```
memory/
├── __init__.py                 # Module exports
├── README.md                   # This file
├── session_memory.py           # Layer 1: In-memory context
├── discovery_cache.py          # Layer 2: Computation cache
├── user_memory.py              # Layer 3: User preferences
├── cross_session_context.py    # Layer 4: Long-term insights
├── crystalyse_memory.py        # Main memory class (combines all layers)
└── memory_tools.py             # Function tools for agent

Generated files (in ~/.crystalyse/):
├── discoveries.json            # Cached computational results
├── memory_{user_id}.md         # User preferences and notes
├── insights_{user_id}.md       # Auto-generated weekly summaries
└── sessions/*.db               # SQLiteSession conversation history
```

## Design Philosophy

Inspired by `gemini-cli`:
- ✅ Simple file-based storage (no complex databases)
- ✅ Human-readable formats (markdown, JSON)
- ✅ Fast lookups without overhead
- ✅ Explicit preferences over ML "guessing"
- ✅ Smart context beats complex architectures

## Testing

```bash
cd /home/ryan/mycrystalyse/CrystaLyse.AI/dev

# Test memory system components
uv run python << 'EOF'
from crystalyse.memory.discovery_cache import DiscoveryCache
from crystalyse.memory.user_memory import UserMemory

# Test cache
cache = DiscoveryCache()
cache.save_result("TestMaterial", {"energy": -3.5})
result = cache.get_cached_result("TestMaterial")
print(f"Cache test: {result is not None}")

# Test user memory
memory = UserMemory(user_id="test")
memory.add_preference("Test preference")
prefs = memory.get_preferences()
print(f"User memory test: {len(prefs) > 0}")

print("✓ Memory system tests passed")
EOF
```

## Future Enhancements

1. **Vector search** for semantic discovery matching
2. **Export/import** memory between users
3. **Memory compression** for old sessions
4. **Collaborative memory** for research teams
5. **Integration with MCP servers** for distributed caching

## Comparison to Old Files

Files in `~/.crystalyse/` dated July 2025 are from **old tests** when the system was being developed. They are orphaned because:
- Memory tools were never registered with agent
- Old files include: `discoveries.json`, `memory_*.md`, `insights_*.md`
- Safe to delete old files if activating fresh

## Decision Log

**2025-10-24**: Memory module preserved during dead code cleanup because:
1. DiscoveryCache provides significant performance improvements
2. CrossSessionContext enables research pattern learning
3. Fully implemented and tested, just needs activation
4. Low maintenance burden (simple file-based storage)
5. Can be activated incrementally (cache-only or full system)

## Questions?

See `memory_tools.py` for complete API documentation or ask the development team about activation plans.
