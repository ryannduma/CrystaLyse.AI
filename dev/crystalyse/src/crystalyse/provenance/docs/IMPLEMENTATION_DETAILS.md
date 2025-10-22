# Provenance System Implementation Details

## Problem Statement

The OpenAI Agents SDK wraps MCP (Model Context Protocol) tools, making them appear as "unknown_tool" in the event stream. This prevents proper tracking of:
- Which actual MCP tools are being used
- Real execution timing (we only see wrapper timing ~3-5ms vs actual 30+ seconds)
- Materials discovered and their properties

## Solution Architecture

### 1. MCP Tool Detection

Since the SDK doesn't expose MCP tool names directly, we detect them by parsing the output structure:

```python
class MCPDetector:
    def detect_tool(output):
        # Unwrap SDK response: {"type": "text", "text": "{actual_json}"}
        data = unwrap_output(output)
        
        # Detect by unique fields
        if "generated_structures" in data and "energy_calculations" in data:
            return "comprehensive_materials_analysis"
        elif data.get("analysis_mode") == "creative":
            return "creative_discovery_pipeline"
```

### 2. Materials Extraction

The output structure varies by tool and mode. For creative mode:

```json
{
  "generated_structures": [
    {
      "composition": "TiO2",
      "structures": [...]  // No energies here!
    }
  ],
  "energy_calculations": [  // Energies in separate array
    {
      "structure_id": "TiO2_struct_1",
      "formation_energy": -6.823
    }
  ]
}
```

We build a lookup table to match energies to structures:

```python
# Build energy lookup
energy_lookup = {}
for calc in data["energy_calculations"]:
    energy_lookup[calc["structure_id"]] = calc["formation_energy"]

# Match to structures
for idx, struct in enumerate(structures):
    struct_id = f"{composition}_struct_{idx+1}"
    energy = energy_lookup.get(struct_id)
```

### 3. Event Stream Integration

We hook into the SDK's event stream:

```python
def on_event(event):
    if event.type == "run_item_stream_event":
        if event.item.type == "tool_call_item":
            # Tool call started
            track_tool_start(event.item)
        elif event.item.type == "tool_call_output_item":
            # Tool call ended - detect MCP tool
            mcp_tool = detect_tool(event.item.output)
            materials = extract_materials(event.item.output)
```

## Key Challenges Solved

### Challenge 1: Wrapped Responses
**Problem**: SDK wraps all MCP responses in `{"type": "text", "text": "..."}`
**Solution**: Recursive unwrapping function that handles multiple levels

### Challenge 2: Energy Location
**Problem**: Energies not in structure objects for creative mode
**Solution**: Parse separate `energy_calculations` array and match by ID

### Challenge 3: Tool Identification
**Problem**: All MCP tools show as "unknown_tool"
**Solution**: Pattern matching on output structure

### Challenge 4: Timing Accuracy
**Problem**: Only wrapper timing captured (~3ms vs actual 30+ seconds)
**Status**: Fundamental SDK limitation - cannot be fully solved without SDK changes
**Partial Solution**: Document limitation, consider parsing MCP server logs separately

## Data Flow

1. **User Query** → CrystaLyse Agent
2. **Agent** → MCP Server (via SDK wrapper)
3. **MCP Server** → Executes tools (Chemeleon, MACE, etc.)
4. **Response** → Wrapped by SDK → Agent
5. **Provenance Handler**:
   - Intercepts SDK events
   - Detects actual MCP tool from output
   - Extracts materials and energies
   - Logs to JSONL files
6. **Output Files**:
   - `events.jsonl` - All events
   - `materials.jsonl` - Materials stream
   - `materials_catalog.json` - Complete catalog
   - `summary.json` - Session metrics
   - `raw_output_*.json` - Debug files

## File Structure

```
provenance_output/
└── runs/
    └── session_20250909_150000/
        ├── events.jsonl           # Event stream
        ├── materials.jsonl        # Materials discovered
        ├── materials_catalog.json # Complete materials data
        ├── summary.json          # Session summary
        ├── assistant_full.md     # Complete response
        └── raw_output_*.json     # Raw tool outputs (debug)
```

## JSONL Event Format

Each line in `events.jsonl`:

```json
{
  "type": "tool_end",
  "ts": "2025-09-09T15:00:00.000Z",
  "data": {
    "wrapper": "unknown_tool",
    "mcp_tool": "comprehensive_materials_analysis",
    "duration_ms": 3.7,
    "materials_count": 15,
    "call_id": "call_123abc"
  }
}
```

## Materials Catalog Format

```json
[
  {
    "composition": "TiO2",
    "formula": "Ti1O2",
    "formation_energy": -6.823,
    "energy_unit": "eV/atom",
    "structure_id": "TiO2_struct_1",
    "space_group": "P1",
    "source_tool": "comprehensive_materials_analysis",
    "timestamp": "2025-09-09T15:00:00.000Z"
  }
]
```

## Integration Points

### With CrystaLyse

```python
from provenance_system import CrystaLyseWithProvenance

agent = CrystaLyseWithProvenance(mode="creative")
result = await agent.discover("Find oxides")
# Provenance automatically captured
```

### With OpenAI SDK

```python
from provenance_system import ProvenanceTraceHandler
from crystalyse.agents import EnhancedCrystaLyseAgent

trace_handler = ProvenanceTraceHandler(output_dir="./provenance")
agent = EnhancedCrystaLyseAgent(mode="creative")
result = await agent.discover(query, trace_handler=trace_handler)
```

## Performance Impact

- **Memory**: ~1-2 MB per session (JSONL files)
- **CPU**: Minimal (<1% overhead for parsing)
- **I/O**: Immediate writes to JSONL (no buffering)
- **Latency**: No impact on discovery speed

## Limitations

1. **Timing Accuracy**: Only captures SDK wrapper timing, not actual MCP execution time
2. **MCP Internal Details**: Cannot capture Chemeleon/MACE individual operation timing
3. **Tool Detection**: Relies on output patterns - may fail for new tools
4. **Streaming**: JSONL files grow linearly - no rotation implemented

## Future Improvements

1. **MCP Server Log Integration**: Parse server INFO logs for real timing
2. **CIF Tracking**: Hash and link generated CIF files
3. **Real-time Dashboard**: WebSocket server for live monitoring
4. **Session Comparison**: Tools to diff materials across runs
5. **Metrics Aggregation**: Statistics across multiple sessions