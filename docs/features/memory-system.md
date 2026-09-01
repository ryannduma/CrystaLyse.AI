# Memory System

## Overview

Crystalyse (v1.0.0-dev) implements a 4-layer memory system using a "simple files + smart context" philosophy. This replaces complex database architectures with efficient file-based storage.

Note that this file-based memory is distinct from *conversation* memory, which lives in a
SQLite database managed by the OpenAI Agents SDK - see
[Session Management](session-management.md).

## Architecture

### 1. Session Memory
**Location**: In-memory  
**Purpose**: Current conversation context  
**Retention**: Last 10 interactions by default

```python
from crystalyse.memory import SessionMemory

session = SessionMemory(max_interactions=10)

# add_interaction records BOTH sides of one exchange in a single call:
#   add_interaction(query, response)
session.add_interaction(
    "Find perovskites for solar cells",
    "I'll search for lead-free perovskites...",
)
```

Passing a role as the first argument (`add_interaction("user", ...)`) would store the
literal string `"user"` as the query. The history is a list of
`(query, response, timestamp)` triples, trimmed to the most recent `max_interactions`.

### 2. Discovery Cache
**Location**: `~/.crystalyse/discoveries.json`  
**Purpose**: Expensive computational results  
**Benefits**: Avoids re-computation of MACE energies, SMACT validations

```json
{
  "LiCoO2": {
    "formula": "LiCoO2",
    "properties": {
      "formation_energy": -2.45,
      "structure_source": "chemeleon",
      "validation_status": "valid"
    },
    "timestamp": "2025-07-27T10:30:00.123456",
    "cached_at": "2025-07-27 10:30:00"
  }
}
```

`save_result(formula, properties)` writes one wrapper entry per formula: the properties you
supply are nested under `"properties"`, never flattened, and two time fields are recorded -
`timestamp` (ISO) and `cached_at` (`%Y-%m-%d %H:%M:%S`).

### 3. User Memory
**Location**: `~/.crystalyse/memory_{user_id}.md`  
**Purpose**: User preferences, research interests, important notes  
**Format**: Human-readable Markdown

```markdown
# Research Preferences - researcher1

## Materials of Interest
- Lead-free perovskites for solar applications
- High-entropy alloys for catalysis
- Solid electrolytes for batteries

## Preferred Analysis Parameters
- Formation energy threshold: < -1.0 eV
- Stability requirement: Above convex hull
- Synthesis temperature: < 800°C

## Important Discoveries
- Ba2NbTaO5N showed promising photovoltaic properties
- CaTiO3 family needs further investigation
```

### 4. Cross-Session Context
**Location**: `~/.crystalyse/insights_{user_id}.md`  
**Purpose**: Auto-generated research summaries and patterns  
**Update**: Regenerated on demand when the file is missing or at least 7 days old

```markdown
# Research Insights - researcher1
Generated: 2025-07-27

## Recent Focus Areas
- 67% queries related to battery materials
- 23% focus on solar applications
- 10% structural analysis

## Successful Discovery Patterns
- Oxide perovskites consistently show good stability
- Quaternary compositions often more stable than ternary
- MACE predictions align well with experimental trends

## Recommended Next Steps
- Explore Ti-based perovskites for photovoltaics
- Investigate high-entropy oxide stability
- Consider defect chemistry in promising candidates
```

## Memory Tools Integration

Eight function tools provide seamless memory access for the OpenAI Agents SDK:

### Core Tools
```python
@function_tool
def save_to_memory(fact: str, section: str = "Important Notes") -> str:
    """Save important information to user memory"""

@function_tool  
def search_memory(query: str) -> str:
    """Search user memory for relevant information"""

@function_tool
def save_discovery(formula: str, properties: str) -> str:
    """Cache computational results to avoid re-computation.
    `properties` is a JSON string, json.loads-ed internally."""

@function_tool
def search_discoveries(query: str, limit: int = 5) -> str:
    """Find previously computed materials (substring match on formula
    and on the stringified properties)"""
```

### Advanced Tools
```python
@function_tool
def get_cached_discovery(formula: str) -> str:
    """Look up one formula in the discovery cache by exact name"""

@function_tool
def get_memory_context() -> str:
    """Summary across all memory layers: session, user memory, discoveries"""

@function_tool
def generate_weekly_summary() -> str:
    """Generate the cross-session insights summary now"""

@function_tool
def get_memory_statistics() -> str:
    """Cache and memory-system statistics"""
```

Those eight - and only those eight - are what `get_memory_tools(user_id)` returns, in that
order. `MEMORY_TOOLS_METADATA` in the same module lists the same set.

## Usage Examples

### Caching Expensive Calculations
```bash
# First query - performs full computation
User: "Calculate formation energy of LiCoO2"
Agent: [Calls MACE, saves result to cache]

# Later query - retrieves from cache
User: "What was the formation energy of LiCoO2?"
Agent: [Reads ~/.crystalyse/discoveries.json, no recomputation]
```

The cache is keyed by exact formula string. `get_cached_discovery` requires an exact match;
`search_discoveries` does a case-insensitive substring match over formulas and stringified
properties.

### Cross-Session Learning
```bash
# Session 1: Battery research
User: "Find cathode materials for Li-ion batteries"
Agent: [Saves research focus and successful patterns]

# Session 2: Weeks later
User: "I need more battery materials"
Agent: "Based on your previous research into Li-ion cathodes, 
        I recommend exploring these Ti-based alternatives..."
```

### Personalised Recommendations  
```bash
# System learns user preferences
User consistently asks about:
- Formation energies < -1.0 eV
- Earth-abundant elements
- Synthesis temperatures < 800°C

# Future recommendations automatically apply these constraints
```

## File Management

### Cleanup

- **Discovery cache**: **no expiration of any kind.** There is no TTL and no age-based
  eviction - entries carry `timestamp` and `cached_at`, but nothing reads them for removal
  (only `get_recent_discoveries` sorts by them, for display). The single deletion path is
  `clear_cache()`, which wipes the whole file. If a cached result is stale, delete it or
  clear the cache
- **User memory**: manual management, human-readable format
- **Session memory**: cleared at session teardown (`CrystaLyseMemory.cleanup()`)
- **Cross-session insights**: regenerated on demand, not on a schedule.
  `should_generate_summary()` returns True when `insights_{user_id}.md` is missing or its
  mtime is at least 7 days old, and `auto_generate_if_needed()` acts on that. Nothing runs
  on a timer - it is reached only when something calls
  `CrystaLyseMemory.auto_generate_insights()`, notably `cleanup()` at session teardown

### Backup and Sync

- The four memory layers are human-readable and version-control friendly
- Simple backup: copy `~/.crystalyse/`
- **But `~/.crystalyse/` now holds more than the memory layers.** It also contains
  `sessions/` with binary SQLite conversation databases (plus their `-wal` and `-shm`
  companions) and, optionally, a user-level `config.toml`. The databases are neither
  human-readable nor version-control friendly, and copying them mid-session can capture a
  partial WAL state. Back up while no session is running, or exclude `sessions/`
- Cloud sync: works for the markdown and JSON layers; be wary of syncing live SQLite files

### Performance Characteristics

There is no latency or hit-rate instrumentation in the memory system, so no figures are
quoted here. Cache hits and misses appear only as `logger.debug` lines - nothing counts
them. What `get_statistics()` does report is `total_entries`, `cache_file` and
`cache_size_mb`, available to the agent through `get_memory_statistics`.

The design constraint that matters more than any number: the discovery cache is a single
JSON file loaded into memory in full and rewritten on every save, and searches are linear
scans. It is fast for thousands of entries and will not stay fast for millions.