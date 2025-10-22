# CrystaLyse Provenance System

## Overview

The provenance system is now fully integrated into CrystaLyse at `/dev/crystalyse/provenance/`. This consolidation makes maintenance easier and ensures tight integration with CrystaLyse's core functionality.

**Phase 1.5 Enhanced**: Full support for all 20 Phase 1.5 MCP tools with Pydantic model serialization and rich metadata extraction.

A comprehensive provenance capture system that tracks:
- All Phase 1.5 MCP tool calls with proper detection
- Materials discovered with enhanced properties (band gap, dopants, stress, etc.)
- Formation energies and structural data with confidence scores
- Tool execution flow and timing with method attribution
- Complete audit trail in JSONL format with v1.5.0 catalog

## Key Features

### ✅ What Works
- **MCP Tool Detection**: Correctly identifies actual MCP tools (comprehensive_materials_analysis, creative_discovery_pipeline, etc.)
- **Materials Extraction**: Captures all materials with compositions and energies
- **Energy Data**: Extracts formation energies from complex nested structures
- **JSONL Logging**: Structured event capture for analysis
- **SDK Integration**: Hooks into OpenAI Agents SDK event stream

### ⚠️ Known Limitations
- **Timing**: Only captures SDK wrapper timing (~3-5ms), not actual MCP operations (30+ seconds)
  - This is a fundamental SDK limitation
  - The SDK only tracks the async call to the MCP server, not internal operations
- **MCP Internal Operations**: Cannot capture individual Chemeleon/MACE timing breakdowns

## Architecture

```
provenance_system/
├── core/                     # Core provenance classes
│   ├── __init__.py
│   ├── event_logger.py       # JSONL event logging
│   ├── materials_tracker.py  # Materials extraction
│   └── mcp_detector.py       # MCP tool detection
├── handlers/                 # Trace handlers
│   ├── __init__.py
│   └── enhanced_trace.py     # Main trace handler
├── integration/              # CrystaLyse integration
│   ├── __init__.py
│   └── agent_wrapper.py      # Agent with provenance
├── examples/                 # Usage examples
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Quick Start

### Basic Usage

```python
from provenance_system import ProvenanceTraceHandler
from crystalyse.agents.openai_agents_bridge import EnhancedCrystaLyseAgent

# Initialize with provenance
trace_handler = ProvenanceTraceHandler(
    output_dir="./provenance_output",
    capture_mcp_logs=True
)

# Run discovery with tracking
agent = EnhancedCrystaLyseAgent(mode="creative")
result = await agent.discover(
    "Find stable binary oxides", 
    trace_handler=trace_handler
)

# Get captured data
summary = trace_handler.finalize()
print(f"Materials found: {summary['materials_found']}")
print(f"MCP tools used: {summary['mcp_tools']}")
```

### Output Structure

```
provenance_output/
└── runs/
    └── session_20250909_153000/
        ├── events.jsonl          # All events
        ├── materials.jsonl       # Materials discovered
        ├── materials_catalog.json # Complete materials data
        ├── summary.json          # Session summary
        ├── assistant_full.md     # Complete response
        └── raw_output_*.json     # Raw tool outputs
```

## Integration with CrystaLyse

The system integrates seamlessly with CrystaLyse's agent architecture:

1. **Trace Handler**: Hooks into SDK event stream
2. **MCP Detection**: Identifies tools from output structure
3. **Materials Extraction**: Parses tool responses
4. **Data Persistence**: JSONL format for analysis

## Data Captured

### Materials Data
- Composition (e.g., "TiO2")
- Formula (e.g., "Ti1O2")
- Formation energy (eV/atom)
- Structure ID
- Space group
- Source tool
- Timestamp

### Tool Metrics
- Tool name (actual MCP tool)
- Call count
- Average duration (wrapper time only)
- Materials generated per tool

### Session Metrics
- Total runtime
- Time to first byte (TTFB)
- Total materials discovered
- Unique compositions
- Energy statistics (min/max/avg)

## Technical Details

### MCP Tool Detection

The SDK wraps MCP tools, showing them as "unknown_tool" in events. We detect the actual tool by parsing the output structure:

```python
def detect_mcp_tool(output):
    # Parse wrapped response
    if output.get("type") == "text":
        data = json.loads(output["text"])
    
    # Detect by structure
    if "generated_structures" in data:
        if data.get("mode") == "creative":
            return "creative_discovery_pipeline"
        return "comprehensive_materials_analysis"
```

### Energy Extraction

Creative mode returns energies in a separate array:

```python
# Build lookup from energy_calculations
energy_lookup = {}
for calc in data["energy_calculations"]:
    struct_id = calc["structure_id"]
    energy_lookup[struct_id] = calc["formation_energy"]

# Match to structures
for struct in structures:
    struct_id = f"{composition}_struct_{idx}"
    energy = energy_lookup.get(struct_id)
```

## Requirements

- Python 3.11+
- OpenAI Agents SDK
- CrystaLyse.AI dev environment
- Conda environment: `rust`

## Installation

```bash
# Activate environment
conda activate rust

# Add to Python path
export PYTHONPATH="/home/ryan/mycrystalyse/CrystaLyse.AI/provenance_system:$PYTHONPATH"

# Test installation
python -c "from provenance_system import ProvenanceTraceHandler"
```

## Testing

```bash
# Run test suite
python provenance_system/tests/test_provenance.py

# Run integration test
python provenance_system/examples/test_all_modes.py
```

## Future Improvements

1. **MCP Server Log Capture**: Parse MCP server INFO logs for actual timing
2. **CIF Artifact Tracking**: Hash and track generated CIF files
3. **Cross-Session Analysis**: Compare materials across runs
4. **Real-time Monitoring**: WebSocket for live tracking
5. **Metrics Dashboard**: Visualize provenance data

## References

- [OpenAI Agents SDK Docs](../openai-agents-python/docs/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [CrystaLyse Architecture](../dev/docs/)