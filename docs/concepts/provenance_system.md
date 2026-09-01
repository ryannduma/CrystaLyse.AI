# Crystalyse Provenance System - Complete Technical Documentation

**Version**: v1.0.0


---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Integration Points](#integration-points)
5. [Data Flow](#data-flow)
6. [File Structure](#file-structure)
7. [Implementation Status](#implementation-status)
8. [Known Limitations](#known-limitations)
9. [Configuration](#configuration)
10. [Usage Examples](#usage-examples)

---

## Overview

The provenance system provides complete audit trails for all materials discovery operations in Crystalyse. It captures events, materials, MCP tool calls, and performance metrics in a structured format suitable for reproducibility, analysis, and debugging.

### Design Philosophy

- **Always-On**: Provenance is a core feature, not optional
- **Transparent**: Users see where data is stored
- **Non-Invasive**: Graceful degradation if capture fails
- **Structured**: JSONL events + JSON summaries for easy parsing
- **Comprehensive**: Captures complete lifecycle from query to results

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                      CrystaLyse CLI                         │
│  ┌──────────────────┐           ┌──────────────────────┐   │
│  │  crystalyse      │           │  crystalyse discover │   │
│  │  (interactive)   │           │  (non-interactive)   │   │
│  └────────┬─────────┘           └──────────┬───────────┘   │
│           │                                 │               │
│           └─────────────┬───────────────────┘               │
│                         ▼                                   │
│              ┌─────────────────────┐                        │
│              │  ChatExperience or  │                        │
│              │  Direct discover()  │                        │
│              └──────────┬──────────┘                        │
│                         │                                   │
│                         ▼                                   │
│         ┌───────────────────────────────┐                   │
│         │ EnhancedCrystaLyseAgent       │                   │
│         │   .discover(trace_handler)    │                   │
│         └──────────┬────────────────────┘                   │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ CrystaLyseProvenanceHandler    │
        │  (extends ProvenanceTraceHandler)│
        └──────────┬─────────────────────┘
                   │
                   ▼
        ┌────────────────────────────────┐
        │  ProvenanceTraceHandler        │
        │  (from crystalyse.provenance)  │
        └──────────┬─────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────────┐
        ▼                     ▼                   ▼
   ┌─────────┐         ┌──────────────┐    ┌──────────┐
   │ JSONL   │         │  Materials   │    │   MCP    │
   │ Logger  │         │   Tracker    │    │ Detector │
   └─────────┘         └──────────────┘    └──────────┘
        │                     │                   │
        └──────────┬──────────┴───────────────────┘
                   ▼
          ┌─────────────────────┐
          │  Provenance Output  │
          │  provenance_output/ │
          │    runs/            │
          │      session_id/    │
          │        events.jsonl │
          │        summary.json │
          │        materials... │
          └─────────────────────┘
```

### Component Hierarchy

```
dev/crystalyse/provenance/         # Provenance package (crystalyse.provenance)
├── __init__.py                    # Package exports
├── core/                          # Core utilities
│   ├── __init__.py
│   ├── event_logger.py            # Event dataclass + JSONLLogger
│   ├── materials_tracker.py       # Materials extraction
│   ├── mcp_detector.py            # MCP tool detection
│   └── pydantic_serializer.py     # Pydantic output serialisation
├── handlers/                      # Trace handlers
│   ├── __init__.py
│   └── enhanced_trace.py          # ProvenanceTraceHandler
├── integration/                   # Integration helpers
│   ├── __init__.py
│   └── agent_wrapper.py           # (Not used - circular import avoided)
├── artifact_tracker.py            # ArtifactTracker (computational artefacts)
├── value_registry.py              # ProvenanceValueRegistry
└── render_gate.py                 # IntelligentRenderGate

dev/crystalyse/                    # CrystaLyse integration
├── ui/
│   ├── provenance_bridge.py       # CrystaLyseProvenanceHandler
│   └── chat_ui.py                 # Interactive chat integration
├── agents/
│   └── agents_bridge.py           # Agent discover() method
├── cli.py                         # CLI entry points
└── config/
    └── __init__.py                # CrystaLyseConfig (provenance settings)
```

The package is imported as `crystalyse.provenance` and uses relative imports
internally (`from ..core import JSONLLogger, MaterialsTracker, MCPDetector`).
There is no standalone top-level `provenance_system` module.

---

## Core Components

### 1. ProvenanceTraceHandler

**Location**: `dev/crystalyse/provenance/handlers/enhanced_trace.py`

**Purpose**: Main trace handler that captures all events from OpenAI Agents SDK

**Key Methods**:
```python
def __init__(
    console: Optional[Console] = None,
    output_dir: Optional[Path] = None,
    session_id: Optional[str] = None,
    enable_provenance: bool = True,
    enable_visual: bool = True,
    capture_mcp_logs: bool = False,
    save_raw_outputs: bool = True
)

def on_event(event: Any) -> None
    """Captures SDK events and routes to appropriate handlers"""

def finalize() -> Dict[str, Any]
    """Generates summary and saves all outputs"""
```

**Responsibilities**:
- Captures SDK trace events (tool calls, outputs, errors)
- Detects actual MCP tool names from SDK wrapper names
- Extracts materials from tool outputs
- Logs all events to JSONL
- Generates performance metrics
- Creates summary JSON

**Event Lifecycle**:
1. `session_start` - Initialize session (records output_dir and capture_mcp_logs)
2. `user_query` - Original query, recorded by `set_user_query()`
3. `tool_start` - Tool invocation begins
4. `tool_end` - Tool completes, materials extracted (carries `has_pydantic`)
5. `ttfb` - First assistant message output observed
6. `assistant_output` - Response generated
7. `session_end` - Finalize and summarize

Also emitted where they apply: `enhanced_material` (Phase 1.5 tools whose name
starts `validate_`, `calculate_`, `analyze_`, `predict_` or `generate_`),
`reasoning` (reasoning items) and `error` (event processing failed).

### 2. CrystaLyseProvenanceHandler

**Location**: `dev/crystalyse/ui/provenance_bridge.py`

**Purpose**: CrystaLyse-specific wrapper around ProvenanceTraceHandler

**Key Features**:
```python
def __init__(
    console: Optional[Console] = None,
    config: Optional['CrystaLyseConfig'] = None,
    mode: str = "auto",                # explore / auto / validate
    session_id: Optional[str] = None,
    **kwargs
)

# Module-level factory with the same defaults
def create_provenance_handler(
    mode: str = "auto",
    config: Optional['CrystaLyseConfig'] = None,
    console: Optional[Console] = None,
    session_id: Optional[str] = None
) -> CrystaLyseProvenanceHandler
```

**Responsibilities**:
- Loads CrystaLyse configuration
- Generates mode-prefixed session IDs (`crystalyse_{mode}_{timestamp}`)
- Maps config settings to provenance parameters
- Adds CrystaLyse-specific metadata to summaries
- Provides convenient access methods (get_summary_path, get_session_info)
- Graceful error handling

**Configuration Mapping**:
```python
super().__init__(
    console=console,
    output_dir=config.provenance['output_dir'],
    session_id=session_id,
    enable_provenance=True,  # Always enabled
    enable_visual=config.provenance['visual_trace'],
    capture_mcp_logs=config.provenance['capture_mcp_logs'],
    save_raw_outputs=config.provenance['capture_raw']
)
```

### 3. JSONLLogger

**Location**: `dev/crystalyse/provenance/core/event_logger.py`

**Purpose**: Structured event logging in JSON Lines format

**Key Methods**:
```python
def log(event_type: str, data: Dict[str, Any]) -> None
    """Write event to JSONL file"""

def log_session_start(session_id: str, metadata: Optional[dict] = None) -> None
    """Session start event (session_id, timestamp, event_count + metadata)"""

def log_session_end(session_id: str, summary: Dict[str, Any]) -> None
    """Final session summary event"""

def get_event_count() -> int
    """Number of events written so far"""

def read_events() -> list
    """Read every event back from the file"""
```

**Event Format**:
```json
{
  "type": "tool_start",
  "ts": "2025-10-08T21:00:00.123456",
  "data": {
    "wrapper": "unknown_tool",
    "call_id": "fc_...",
    "timestamp": "2025-10-08T21:00:00.123456"
  }
}
```

### 4. MaterialsTracker

**Location**: `dev/crystalyse/provenance/core/materials_tracker.py`

**Purpose**: Extract and track materials from tool outputs

**Key Methods**:
```python
def extract_from_output(output: Any, tool_name: Optional[str] = None) -> List[Material]
    """Parse tool output for materials, then track and de-duplicate them"""

def get_summary() -> Dict[str, Any]
    """Counts, energy coverage and min/max/avg formation energy"""

def to_catalog() -> List[Dict[str, Any]]
    """Unique materials as a plain list"""

def to_enhanced_catalog() -> Dict[str, Any]
    """Versioned catalogue with metadata and statistics"""

def save_catalog(path: str, enhanced: bool = True) -> None
    """Save materials_catalog.json"""
```

**Extraction Patterns**:
- Per-tool extractors dispatched on the detected MCP tool name, with a generic fallback
- Detects composition strings (e.g., "MgFe2O4", "Li2CoO3")
- Extracts formation energies, including an `energy_calculations` lookup keyed on `structure_id`
- Records Phase 1.5 properties: energy above hull, stability, band gap, bulk modulus,
  stress tensor, dopants, oxidation states, coordination environments
- De-duplicates on a normalised (alphabetically ordered) composition, merging repeat
  observations of the same material

### 5. MCPDetector

**Location**: `dev/crystalyse/provenance/core/mcp_detector.py`

**Purpose**: Detect actual MCP tool names from SDK-wrapped outputs

**Key Methods**:
```python
@classmethod
def detect_tool(output: Any) -> Optional[str]
    """Identify the actual MCP tool from the (serialised) tool output"""

@classmethod
def get_tool_category(tool_name: str) -> str
    """Group a tool for metrics: generation, validation, calculation, ..."""
```

**Detection Strategy** (the detector only ever sees the output, never the tool args):
1. Unwrap any SDK `{"type": "text", "text": "..."}` envelope and parse the JSON inside
2. Check for an explicit `server_type` field: `chemistry-creative-server` →
   `creative_discovery_pipeline`, `chemistry-unified-server` →
   `comprehensive_materials_analysis`
3. Check for `analysis_mode` in (`explore`, `creative`) → `creative_discovery_pipeline`
4. Score the output's keys against `TOOL_SIGNATURES`, accepting the best match at ≥ 50%
5. Fall back on `generated_structures` (+ `energy_calculations`) being present,
   otherwise return None

**Known Tools**: `TOOL_SIGNATURES` holds 20 entries -
`comprehensive_materials_analysis`, `creative_discovery_pipeline`,
`validate_composition`, `estimate_band_gap`, `predict_dopants`,
`smact_validate_fast`, `generate_ml_representation`, `filter_compositions`,
`generate_crystal_csp`, `calculate_formation_energy`, `relax_structure`,
`calculate_stress`, `fit_equation_of_state`, `list_foundation_models`,
`analyze_space_group`, `calculate_energy_above_hull`, `analyze_coordination`,
`analyze_oxidation_states`, `save_structure_as_cif` and `visualize_structure`.
A call the detector cannot identify is recorded under its SDK wrapper name
(usually `unknown_tool`).

### 6. ProvenanceValueRegistry and the Render Gate

**Location**: `dev/crystalyse/provenance/value_registry.py`,
`dev/crystalyse/provenance/artifact_tracker.py`,
`dev/crystalyse/provenance/render_gate.py`

**Purpose**: Make individual numbers traceable back to the tool call that produced them

Every identified MCP tool output is registered with the global registry as the
tool call ends:

```python
registry = get_global_registry()
if registry and mcp_tool:
    registry.register_tool_output(
        tool_name=mcp_tool,
        tool_call_id=call_id,
        input_data={},
        output_data=serialized_output,
        timestamp=datetime.now().isoformat(),
    )
```

`ProvenanceValueRegistry` delegates to an `ArtifactTracker`, which registers each
tool output as an artifact and extracts the numeric values it contains, so a value
can be traced back to its source call. `EnhancedCrystaLyseAgent.discover()` then
builds an `IntelligentRenderGate(provenance_tracker=get_global_registry())` when
`config.render_gate["enabled"]`, runs the assistant response through it, and returns
a `render_gate` block alongside the provenance block. See
[Render Gate System](render_gate_system.md) for the gate itself.

---

## Integration Points

### 1. CLI Entry Points

**File**: `dev/crystalyse/cli.py`

#### Non-Interactive Discovery

```python
@app.command()
def discover(
    query: str,
    provenance_dir: Optional[str] = None,   # --provenance-dir
    hide_summary: bool = False,             # --hide-summary
    mode: Optional[str] = None,             # --mode explore|validate|auto
    project: Optional[str] = None,          # --project / -p
):
    """Single-shot discovery with automatic provenance"""

    # Per-command options override the global ones
    effective_mode = resolve_mode_name(mode) if mode is not None else state["mode"]
    effective_project = project if project is not None else state["project"]

    config = Config.load()
    if provenance_dir:
        config.provenance["output_dir"] = Path(provenance_dir)

    agent = EnhancedCrystaLyseAgent(
        config=config,
        project_name=effective_project,
        mode=effective_mode.value,
        model=state["model"],
    )

    # Agent auto-creates provenance handler
    results = await agent.discover(query)

    # display_results() reaches into results["provenance"]
    show_summary = config.provenance["show_summary"] and not hide_summary
    display_results(results, show_provenance_summary=show_summary)
```

`--mode` takes the canonical modes (`explore`, `validate`, `auto`); the legacy
names `creative`, `rigorous` and `adaptive` still resolve through
`resolve_mode_name()` with a `DeprecationWarning`.

#### Interactive Chat

```python
@app.command()
def chat(user: str = "default", session: Optional[str] = None):
    """Interactive chat with provenance per query"""

    chat_experience = ChatExperience(
        project=state['project'] + (f"_{session}" if session else ""),
        mode=state['mode'].value,
        model=state['model'],
        user_id=user
    )

    asyncio.run(chat_experience.run_loop())
```

#### Provenance Analysis

```python
@app.command(name="analyse-provenance")
def analyse_provenance(
    session_id: Optional[str] = None,
    latest: bool = False,
    provenance_dir: str = "./provenance_output"
):
    """Analyse provenance from previous sessions"""

    base_dir = Path(provenance_dir) / "runs"

    if latest:
        sessions = sorted(base_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        session_dir = sessions[0]
    elif session_id:
        session_dir = base_dir / session_id
    else:
        # List available sessions
        display_session_list(base_dir)
        return

    # Load and display summary
    display_session_analysis(session_dir)
```

**Legacy Path Initialization** (inert):

`cli.py` still carries an early `sys.path` block from the days when provenance
lived in a standalone top-level module:

```python
# dev/crystalyse/cli.py
crystalyse_root = Path(__file__).parent.parent.parent
provenance_system_path = crystalyse_root / "provenance_system"
if provenance_system_path.exists() and str(crystalyse_root) not in sys.path:
    sys.path.insert(0, str(crystalyse_root))
```

No `provenance_system/` directory exists any more, so the guard never fires.
Provenance is imported as an ordinary subpackage
(`from ..provenance.handlers import ProvenanceTraceHandler`), which needs no
`sys.path` manipulation.

### 2. ChatExperience Integration

**File**: `dev/crystalyse/ui/chat_ui.py`

**Initialization**:
```python
def __init__(self, project: str, mode: str, model: str, user_id: str = "default"):
    # ... existing initialization ...
    self.config = Config.load()  # Load config for provenance settings
    self.provenance_handler = None  # Will be created per query
```

**Per-Query Provenance**:
```python
async def run_loop(self):
    while True:
        query = self.console.input("[bold green]➤ [/bold green]")

        # Create provenance handler for this query (always-on)
        if PROVENANCE_AVAILABLE:
            trace_handler = CrystaLyseProvenanceHandler(
                console=self.console,
                config=self.config,
                mode=self.mode
            )
            self.provenance_handler = trace_handler
            # Record the user's original query -> user_query event
            trace_handler.set_user_query(query)
        else:
            trace_handler = ToolTraceHandler(self.console)

        # Query goes straight to the agent with no preprocessing
        results = await self.agent.discover(
            query,
            history=self.history,
            trace_handler=trace_handler
        )

        if results and results.get("status") == "completed":
            # Display response
            self._display_message("assistant", response)

            # Finalize and display provenance summary
            if PROVENANCE_AVAILABLE and self.provenance_handler:
                try:
                    summary = self.provenance_handler.finalize()
                    if summary and self.config.provenance.get('show_summary', True):
                        self._display_provenance_summary(summary)
                except Exception as e:
                    self.console.print(f"[dim yellow]Provenance summary unavailable: {e}[/dim yellow]")
```

**Summary Display**:
```python
def _display_provenance_summary(self, summary: Dict[str, Any]):
    """Display provenance summary in a compact format."""
    from rich.table import Table

    table = Table(title="Provenance Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    # Add key metrics (using actual keys from summary)
    table.add_row("Session ID", summary.get("session_id", "N/A"))
    table.add_row("Materials Found", str(summary.get("materials_found", 0)))

    # Use mcp_operations (actual key) instead of mcp_tools_detected
    mcp_ops = summary.get("mcp_operations", 0)
    table.add_row("MCP Tool Calls", str(mcp_ops))

    # Show tool call breakdown
    tool_calls = summary.get("tool_calls_total", 0)
    table.add_row("Total Tool Calls", str(tool_calls))

    # Add file location
    session_info = summary.get("session_info", {})
    output_dir = session_info.get("output_dir") or summary.get("output_dir")
    if output_dir:
        table.add_row("Output Directory", str(output_dir))

    self.console.print("\n")
    self.console.print(table)
    self.console.print(f"[dim]Analyse with: crystalyse analyse-provenance --session {summary.get('session_id', 'N/A')}[/dim]\n")
```

### 3. Agent Integration

**File**: `dev/crystalyse/agents/agents_bridge.py`

**Auto-Create Provenance Handler**:
```python
async def discover(
    self,
    query: str,
    history: Optional[List[Dict[str, Any]]] = None,
    trace_handler: Optional[ToolTraceHandler] = None
) -> Dict[str, Any]:
    """
    Processes a single discovery request with automatic provenance capture.

    Provenance is always enabled - every query generates a complete audit trail.
    """
    if not SDK_AVAILABLE:
        return {"status": "failed", "error": "OpenAI Agents SDK is not installed."}

    # Auto-create provenance handler if not provided
    if trace_handler is None and PROVENANCE_AVAILABLE and CrystaLyseProvenanceHandler:
        try:
            trace_handler = CrystaLyseProvenanceHandler(
                config=self.config, mode=self.mode, console=Console()
            )
        except Exception as e:
            logger.warning(f"Failed to create provenance handler: {e}")
            trace_handler = None  # discovery proceeds without provenance

    # Record the user's query (auto-created or caller-supplied handler)
    if trace_handler is not None and hasattr(trace_handler, "set_user_query"):
        trace_handler.set_user_query(query)

    async with self._managed_mcp_servers() as mcp_servers:
        # ... resolve_model_name() / resolve_model_config(), build the SDK Agent ...

        # trace_id must start with 'trace_' (OpenAI API) and contain no dots
        trace_timestamp = int(time.time())
        trace_id = f"trace_crystalyse_{self.session_id}_{trace_timestamp}"
        run_config = RunConfig(trace_id=trace_id)

        async with asyncio.timeout(self.config.mode_timeouts.get(self.mode, 180)):
            # Always streamed, so provenance capture works for every model
            result = Runner.run_streamed(**stream_args)
            async for event in result.stream_events():
                if trace_handler:
                    trace_handler.on_event(event)

        # ... render gate over final_response ...

        result = {
            "status": "completed",
            "query": query,
            "response": final_response,
            "render_gate": render_gate_stats,
        }

        if isinstance(trace_handler, CrystaLyseProvenanceHandler):
            result["provenance"] = {
                "session_id": trace_handler.session_id,
                "output_dir": str(trace_handler.output_dir),
                "summary": trace_handler.finalize(),
                "materials_catalogue": str(trace_handler.get_materials_catalogue_path()),
                "summary_file": str(trace_handler.get_summary_path()),
                "events_file": str(trace_handler.get_events_path()),
            }

        return result
```

The finalised summary is nested under `results["provenance"]["summary"]`; there is
no top-level `provenance_summary` key.

---

## Data Flow

### Complete Request Lifecycle

```
1. User Query
   └─> CLI (crystalyse discover "query" OR crystalyse → "query")
       │
2. Handler Creation
   └─> CrystaLyseProvenanceHandler(config, mode, console)
       ├─> JSONLLogger.log_session_start(...)
       └─> set_user_query(query) → JSONLLogger.log("user_query", ...)
       │
3. Agent Discovery
   └─> EnhancedCrystaLyseAgent.discover(query, trace_handler)
       │
4. SDK Stream Events (run_item_stream_event)
   ├─> tool_call_item → ProvenanceTraceHandler.on_event()
   │                 └─> JSONLLogger.log("tool_start", {...})
   │                 └─> Track tool call (EnhancedToolCall)
   │
   ├─> tool_call_output_item → ProvenanceTraceHandler.on_event()
   │               └─> serialize_pydantic_model(output)
   │               └─> Save raw output (if enabled)
   │               └─> MCPDetector.detect_tool(output)
   │               └─> MaterialsTracker.extract_from_output(output, tool)
   │               └─> get_global_registry().register_tool_output(...)
   │               └─> JSONLLogger.log("enhanced_material", ...) (Phase 1.5 tools)
   │               └─> JSONLLogger.log("tool_end", {...})
   │
   ├─> message_output_item → ProvenanceTraceHandler.on_event()
   │                       └─> JSONLLogger.log("ttfb", ...) on the first message
   │                       └─> Buffer response content
   │
   ├─> reasoning_item → JSONLLogger.log("reasoning", {...})
   │
   └─> session_end (implicit via finalize)
       │
5. Finalization
   └─> ProvenanceTraceHandler.finalize()
       ├─> Save assistant_full.md
       ├─> Save conversation_full.md (and conversation.json when non-empty)
       ├─> MaterialsTracker.save_catalog(..., enhanced=True) → materials_catalog.json
       ├─> Generate summary statistics
       ├─> Save summary.json
       └─> JSONLLogger.log_session_end(...)
       │
6. Display Summary
   ├─> cli.display_provenance_summary(results["provenance"])  (crystalyse discover)
   └─> ChatExperience._display_provenance_summary(summary)     (interactive chat)
       └─> Rich Table with metrics
```

### Event Flow Detail

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenAI Agents SDK                        │
│                                                             │
│  Runner.run_streamed() emits stream events; the handler     │
│  reacts to exactly one of them:                             │
│    - run_item_stream_event, dispatched on event.item.type:  │
│        · tool_call_item                                     │
│        · tool_call_output_item                              │
│        · message_output_item                                │
│        · reasoning_item                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │ events
                   ▼
┌─────────────────────────────────────────────────────────────┐
│         ProvenanceTraceHandler.on_event(event)              │
│                                                             │
│  if event.type == "run_item_stream_event":                  │
│      self._process_stream_event(event.item)                 │
│                                                             │
│  tool_call_item        → _on_tool_call_start(item)          │
│      tool_call = EnhancedToolCall(...)                      │
│      self.event_logger.log("tool_start", ...)               │
│                                                             │
│  tool_call_output_item → _on_tool_call_end(item)            │
│      mcp_tool = self.mcp_detector.detect_tool(output)       │
│      materials = self.materials_tracker                     │
│          .extract_from_output(output, mcp_tool or wrapper)  │
│      get_global_registry().register_tool_output(...)        │
│      self.event_logger.log("tool_end", ...)                 │
│                                                             │
│  message_output_item   → _on_message_output(item)           │
│      self.assistant_buffer.append(                          │
│          ItemHelpers.text_message_output(item))             │
│                                                             │
│  reasoning_item        → _on_reasoning(item)                │
│                                                             │
│  Every other event type is ignored.                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Provenance Output Files                        │
│                                                             │
│  provenance_output/runs/crystalyse_explore_YYYYMMDD_HHMMSS/ │
│  ├── events.jsonl              ← All events                 │
│  ├── summary.json              ← Session summary            │
│  ├── materials_catalog.json    ← Materials found            │
│  ├── materials.jsonl           ← One line per material      │
│  ├── assistant_full.md         ← Full response              │
│  ├── conversation_full.md      ← Query + response           │
│  ├── conversation.json         ← Conversation log           │
│  └── raw_output_<call_id>.json ← Raw tool outputs           │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Provenance Output Directory

```
provenance_output/
└── runs/
    └── crystalyse_{mode}_{timestamp}/        # e.g., crystalyse_explore_20260120_015444
        ├── events.jsonl                      # Sequential event log
        ├── summary.json                      # Session summary
        ├── materials_catalog.json            # Materials discovered (enhanced catalogue)
        ├── materials.jsonl                   # One line per extracted material
        ├── assistant_full.md                 # Complete assistant response
        ├── conversation_full.md              # Query and response as markdown
        ├── conversation.json                 # Conversation log (when non-empty)
        └── raw_output_{call_id}.json         # Raw tool output, one per call (if enabled)
```

Raw outputs are written flat into the session directory as
`raw_output_{call_id[:8]}.json`, not into a subdirectory.

### File Formats

#### events.jsonl

Sequential log of all events (JSON Lines format - one JSON object per line).
The sample below is the run committed at
`dev/provenance_output/runs/crystalyse_creative_20260120_015444/`; it was captured
before the mode rename, so its session id still carries the deprecated `creative`
alias, and new sessions are named `crystalyse_explore_*`, `crystalyse_validate_*`
or `crystalyse_auto_*`:

```jsonl
{"type": "session_start", "ts": "2026-01-20T01:54:44.452377", "data": {"session_id": "crystalyse_creative_20260120_015444", "timestamp": "2026-01-20T01:54:44.452370", "event_count": 0, "output_dir": "provenance_output/runs/crystalyse_creative_20260120_015444", "capture_mcp_logs": false}}
{"type": "user_query", "ts": "2026-01-20T01:54:44.452511", "data": {"query": "Find stable thermoelectric", "timestamp": "2026-01-20T01:54:44.452509"}}
{"type": "tool_start", "ts": "2026-01-20T01:54:56.347302", "data": {"wrapper": "unknown_tool", "call_id": "fc_09583ad4b8700c8500696ee06f51e481a18ecabc96f6d7846c", "timestamp": "2026-01-20T01:54:56.347295"}}
{"type": "tool_end", "ts": "2026-01-20T01:55:03.397454", "data": {"wrapper": "unknown_tool", "mcp_tool": "creative_discovery_pipeline", "duration_ms": 7047.950029373169, "materials_count": 0, "call_id": "fc_09583ad4b8700c8500696ee06f51e481a18ecabc96f6d7846c", "has_pydantic": false, "timestamp": "2026-01-20T01:55:03.397449"}}
{"type": "ttfb", "ts": "2026-01-20T01:55:08.055359", "data": {"time_ms": 23602.98442840576, "timestamp": "2026-01-20T01:55:08.055353"}}
{"type": "assistant_output", "ts": "2026-01-20T01:55:08.061122", "data": {"length": 1128, "timestamp": "2026-01-20T01:55:08.061118", "session_id": "crystalyse_creative_20260120_015444"}}
{"type": "session_end", "ts": "2026-01-20T01:55:08.061434", "data": {"session_id": "crystalyse_creative_20260120_015444", "timestamp": "2026-01-20T01:55:08.061379", "event_count": 6, "total_time_s": 23.60901117324829, "ttfb_ms": 23602.98442840576, "tool_calls_total": 1, "materials_found": 0, "unique_compositions": 0, "mcp_operations": 1, "mcp_tools": {"creative_discovery_pipeline": {"count": 1, "total_ms": 7047.950029373169, "materials": 0, "avg_ms": 7047.950029373169}}, "materials_summary": {"total": 0, "with_energy": 0, "min_energy": null, "max_energy": null, "avg_energy": null}}}
```

That is 7 events for a single one-tool query. `reasoning`,
`enhanced_material` and `error` events appear when the run produces them.

#### summary.json

High-level session statistics, exactly the keys
`ProvenanceTraceHandler.finalize()` writes (same committed sample run):

```json
{
  "session_id": "crystalyse_creative_20260120_015444",
  "total_time_s": 23.60901117324829,
  "ttfb_ms": 23602.98442840576,
  "tool_calls_total": 1,
  "materials_found": 0,
  "unique_compositions": 0,
  "mcp_operations": 1,
  "timestamp": "2026-01-20T01:55:08.061379",
  "mcp_tools": {
    "creative_discovery_pipeline": {
      "count": 1,
      "total_ms": 7047.950029373169,
      "materials": 0,
      "avg_ms": 7047.950029373169
    }
  },
  "materials_summary": {
    "total": 0,
    "with_energy": 0,
    "min_energy": null,
    "max_energy": null,
    "avg_energy": null
  }
}
```

`CrystaLyseProvenanceHandler.finalize()` adds `mode`, `session_info` and
`output_dir` to the dictionary it *returns*, after summary.json has already been
written - so those three keys reach the CLI summary table, not the file.

#### materials_catalog.json

`finalize()` calls `save_catalog(..., enhanced=True)`, which writes
`to_enhanced_catalog()`. `Material.to_dict()` drops `None` values, so unset fields
are absent rather than null. From the committed sample run (which extracted no
materials):

```json
{
  "version": "1.5.0",
  "timestamp": "2026-01-20T01:55:08.061314",
  "total_materials": 0,
  "materials": [],
  "materials_by_method": {},
  "statistics": {
    "total_materials": 0,
    "unique_compositions": 0,
    "materials_with_energy": 0,
    "energy_coverage": 0.0,
    "total_observations": 0,
    "methods_used": [],
    "materials_with_band_gap": 0,
    "materials_with_dopants": 0,
    "stable_materials": 0,
    "materials_with_stress": 0
  },
  "unique_compositions": []
}
```

For a run that does find materials, `materials` holds one record per unique
(normalised) composition - `composition`, `formula`, `formation_energy`,
`energy_unit`, `structure_id`, `space_group`, `source_tool`, `timestamp`, `method`,
plus whichever Phase 1.5 fields were measured (`energy_above_hull`, `is_stable`,
`band_gap`, `bulk_modulus`, `stress_tensor`, `dopants`, `oxidation_states`,
`coordination_environments`) - and `materials_by_method` groups the same records
by `method`. There is no `summary` or `by_tool` key; the counts live under
`statistics`.

#### assistant_full.md

Complete assistant response (markdown format):

```markdown
I have completed an auto-mode comprehensive analysis for the spinel series
Mg₁₊ₓFe₂₋ₓO₄ (x = 0–3), focusing on MgFe₂O₄ as the baseline photocatalyst
composition. Key findings:

1. MgFe₂O₄ (spinel)
   - Most stable sample: sample_0
   - Formation energy per atom: –4.5365 eV/atom (MACE)
   - Energy above convex hull: 0.1183 eV/atom (metastable)
   ...
```

---

## Implementation Status

### ✅ What's Working

#### Always-on Provenance Capture
- ✅ `crystalyse discover` - Non-interactive single queries
- ✅ `crystalyse` (interactive chat) - Multi-query sessions
- ✅ Automatic handler creation when none provided
- ✅ Graceful degradation: interactive chat falls back to the basic trace handler,
  `discover()` proceeds with `trace_handler = None`

#### Complete Data Capture
- ✅ All events logged to `events.jsonl`
  - session_start, user_query, tool_start, tool_end, ttfb, assistant_output, session_end
  - plus reasoning, enhanced_material and error events where they apply
  - 7 events for the single-tool query in the committed sample run
- ✅ Materials tracked with compositions
  - Correct count (16 materials in test case)
  - Compositions extracted (MgFe2O4, Mg2Fe4O8, etc.)
  - Source tool attribution
- ✅ MCP tool detection working
  - 20 tool signatures in `MCPDetector.TOOL_SIGNATURES`
  - Wrapper name → actual tool name mapping (`unknown_tool` → `creative_discovery_pipeline`)
- ✅ Performance metrics captured
  - Total runtime (110.46s in test case)
  - Time to first byte (TTFB: 108030ms)
  - Per-tool duration (0.129ms avg)

#### No Technical Blockers
- ✅ Circular imports resolved
  - Removed ToolTraceHandler import from enhanced_trace.py
  - Using duck typing instead of actual inheritance
- ✅ Module path issues fixed
  - Provenance folded into the package as `crystalyse.provenance`
  - Imported with ordinary relative imports; no sys.path manipulation needed
- ✅ SDK trace_id validation errors fixed
  - Using `int(time.time())` instead of float
  - No dots in trace_id (SDK requirement satisfied)
  - Prefixed with `trace_`, as the OpenAI API requires
- ✅ Summary display shows correct values
  - Fixed key mismatches (mcp_operations, tool_calls_total)
  - All metrics display correctly

#### User Experience
- ✅ Provenance summary displayed after queries
  - Compact Rich table format
  - Key metrics visible
  - Output directory path shown
- ✅ Files organized in timestamped directories
  - Format: `crystalyse_{mode}_{YYYYMMDD}_{HHMMSS}`
  - Easy chronological sorting
- ✅ `crystalyse analyse-provenance` command working
  - `--latest` flag works
  - `--session <id>` flag works
  - Session list display works
- ✅ Clear output directory paths shown
  - Both in summary table and CLI output
  - Relative paths for convenience

---

## Known Limitations

### Energy Extraction

Formation energies are extracted. `MaterialsTracker` builds an energy lookup from
`energy_calculations` keyed on `structure_id` and assigns `formation_energy` to each
structure pulled out of `comprehensive_materials_analysis` and
`creative_discovery_pipeline` output, and has dedicated extractors for
`calculate_formation_energy`, `calculate_energy_above_hull` and
`calculate_energy_mace`. An energy that arrives without a composition is held as
`_orphaned_energy_data` and attached to the next material that lacks one.
`get_summary()` fills in `min_energy` / `max_energy` / `avg_energy` whenever any
tracked material carries an energy, and each `Material` also records
`energy_above_hull`, `is_stable`, `band_gap`, `bulk_modulus`, `stress_tensor`,
`dopants` and `oxidation_states`.

**What still limits coverage**:

- Extraction is dispatched on the *detected* tool name. A call the detector cannot
  identify falls through to `_extract_generic()`, which only reads top-level
  `formula` / `composition` and top-level property fields - a nested payload
  (a list of structures, say) yields nothing.
- `with_energy` counts unique materials, so structures that were generated but
  never costed pull the reported energy coverage down.
- Raw tool outputs remain the ground truth. Each call is saved as
  `raw_output_{call_id}.json` while `CRYSTALYSE_CAPTURE_RAW` is enabled, and the
  same energies are in the CIF files and analysis reports.

---

## Configuration

### CrystaLyse Config

**File**: `dev/crystalyse/config/__init__.py` (the former `config.py`, promoted to a package to house `models.py`, `modes.py`, `settings.py` and `model_overrides.py`)

```python
class CrystaLyseConfig:
    def load_from_env(self):
        # Provenance Configuration (ALWAYS ENABLED)
        self.provenance = {
            "output_dir": Path(os.getenv(
                "CRYSTALYSE_PROVENANCE_DIR",
                "./provenance_output"
            )),
            "capture_raw": os.getenv(
                "CRYSTALYSE_CAPTURE_RAW",
                "true"
            ).lower() == "true",
            "capture_mcp_logs": os.getenv(
                "CRYSTALYSE_CAPTURE_MCP_LOGS",
                "false"
            ).lower() == "true",
            "session_prefix": os.getenv(
                "CRYSTALYSE_SESSION_PREFIX",
                "crystalyse"
            ),
            "show_summary": os.getenv(
                "CRYSTALYSE_SHOW_PROVENANCE_SUMMARY",
                "true"
            ).lower() == "true",
            "visual_trace": os.getenv(
                "CRYSTALYSE_VISUAL_TRACE",
                "true"
            ).lower() == "true"
        }
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CRYSTALYSE_PROVENANCE_DIR` | `./provenance_output` | Base directory for provenance files |
| `CRYSTALYSE_CAPTURE_RAW` | `true` | Save raw tool outputs to files |
| `CRYSTALYSE_CAPTURE_MCP_LOGS` | `false` | Attempt to capture MCP server logs |
| `CRYSTALYSE_SESSION_PREFIX` | `crystalyse` | Prefix for session IDs |
| `CRYSTALYSE_SHOW_PROVENANCE_SUMMARY` | `true` | Display summary table after queries |
| `CRYSTALYSE_VISUAL_TRACE` | `true` | Gates the duck-typed base handler, whose `on_event()` is a no-op - currently renders nothing |

### Customization Examples

**Custom output directory**:
```bash
export CRYSTALYSE_PROVENANCE_DIR="/home/user/research/provenance"
crystalyse discover "Li-ion cathodes"
```

**Hide summary table** (still captures data):
```bash
export CRYSTALYSE_SHOW_PROVENANCE_SUMMARY=false
crystalyse discover "perovskites"
# OR
crystalyse discover "perovskites" --hide-summary
```

**Disable raw output saving** (saves space):
```bash
export CRYSTALYSE_CAPTURE_RAW=false
crystalyse discover "thermoelectrics"
```

---

## Usage Examples

### Example 1: Non-Interactive Discovery

```bash
$ crystalyse discover "novel photocatalyst for water splitting"

Starting non-interactive discovery: novel photocatalyst for water splitting
Mode: auto | Project: crystalyse_session

[... discovery process ...]

                          Provenance Summary
┌──────────────────┬────────────────────────────────────────────────┐
│ Session ID       │ crystalyse_auto_20251008_210500                │
│ Materials Found  │ 16                                             │
│ With Energy Data │ 0                                              │
│ Runtime          │ 110.5s                                         │
│ MCP Tools Used   │ comprehensive_materials_analysis               │
│ Output Location  │ provenance_output/runs/crystalyse_auto_2025... │
└──────────────────┴────────────────────────────────────────────────┘
```

### Example 2: Interactive Chat

```bash
$ crystalyse

[ASCII art banner]

➤ suggest a novel photocatalyst for water splitting

[... discovery process ...]

[CrystaLyse response panel]

                          Provenance Summary
┌──────────────────┬────────────────────────────────────────────────┐
│ Session ID       │ crystalyse_auto_20251008_210600                │
│ Materials Found  │ 16                                             │
│ MCP Tool Calls   │ 1                                              │
│ Total Tool Calls │ 1                                              │
│ Output Directory │ provenance_output/runs/crystalyse_auto_...     │
└──────────────────┴────────────────────────────────────────────────┘
Analyse with: crystalyse analyse-provenance --session crystalyse_auto_20251008_210600

➤ [next query...]
```

### Example 3: Analyse Latest Session

```bash
$ crystalyse analyse-provenance --latest

╭──────────────────────────────────────────────────────────╮
│ Analysing Session: crystalyse_auto_20251008_210600       │
╰──────────────────────────────────────────────────────────╯

Performance Metrics:
┌────────────────────┬──────────┐
│ Total Runtime      │ 110.46s  │
│ Time to First Byte │ 108030ms │
│ Total Tool Calls   │ 1        │
└────────────────────┴──────────┘

Materials Summary:
┌──────────────────┬────┐
│ Total Found      │ 16 │
│ With Energy Data │ 0  │
└──────────────────┴────┘

MCP Tools Used:
╭───────────────────────────────────────────────────────╮
│           comprehensive_materials_analysis            │
│ Calls: 1                                              │
│ Average Time: 0.1ms                                   │
│ Materials Generated: 16                               │
╰───────────────────────────────────────────────────────╯

Session files located at: provenance_output/runs/crystalyse_auto_20251008_210600
```

### Example 4: List All Sessions

```bash
$ crystalyse analyse-provenance

Available Provenance Sessions
┌─────────────────────────────────────────┬─────────────────────┬───────────┐
│ Session ID                              │ Timestamp           │ Materials │
├─────────────────────────────────────────┼─────────────────────┼───────────┤
│ crystalyse_auto_20251008_210600         │ 2025-10-08T21:06:00 │ 16        │
│ crystalyse_auto_20251008_210500         │ 2025-10-08T21:05:00 │ 16        │
│ crystalyse_explore_20251008_190619      │ 2025-10-08T19:06:19 │ 8         │
└─────────────────────────────────────────┴─────────────────────┴───────────┘

Use --latest or --session <id> to analyse a specific session
```

### Example 5: Custom Provenance Directory

```bash
$ crystalyse discover "thermoelectrics" --provenance-dir ./my_research/provenance

Starting non-interactive discovery: thermoelectrics
Mode: auto | Project: crystalyse_session

[... discovery process ...]

                          Provenance Summary
┌──────────────────┬────────────────────────────────────────────────┐
│ ...              │ (same rows as Example 1)                       │
│ Output Location  │ ./my_research/provenance/runs/crystalyse_...   │
└──────────────────┴────────────────────────────────────────────────┘
```

### Example 6: Programmatic Access

```python
import json
from pathlib import Path

# Load session summary
session_dir = Path("provenance_output/runs/crystalyse_auto_20251008_210600")
with open(session_dir / "summary.json") as f:
    summary = json.load(f)

print(f"Materials found: {summary['materials_found']}")
print(f"Total time: {summary['total_time_s']:.2f}s")
print(f"Tools used: {list(summary['mcp_tools'].keys())}")

# Load events
with open(session_dir / "events.jsonl") as f:
    events = [json.loads(line) for line in f]

print(f"Total events: {len(events)}")
tool_events = [e for e in events if e['type'].startswith('tool_')]
print(f"Tool events: {len(tool_events)}")

# Load materials catalog
with open(session_dir / "materials_catalog.json") as f:
    materials = json.load(f)

for material in materials['materials']:
    print(f"  - {material['composition']} (from {material['source_tool']})")
```

---

## Technical Decisions & Rationale

### 1. Always-On Provenance

**Decision**: Provenance is always enabled, not optional.

**Rationale**:
- Core feature for reproducibility
- Essential for debugging complex agent workflows
- Minimal performance overhead (<1%)
- Users can hide display, but capture always happens

**Alternative Considered**: Optional toggle
- Rejected: Adds complexity, users might forget to enable
- Users can disable display if desired (--hide-summary)

### 2. Per-Query Sessions in Interactive Chat

**Decision**: Each query in interactive chat gets its own provenance directory.

**Rationale**:
- Clear attribution of results to specific queries
- Prevents state leakage between queries
- Easier to analyse individual discoveries
- Follows OpenAI Agents SDK session model

**Alternative Considered**: Unified session per chat
- Rejected: Harder to isolate specific query provenance
- Could be added as future enhancement if requested

### 3. Duck Typing for ToolTraceHandler

**Decision**: Define a minimal `ToolTraceHandler` base class in `enhanced_trace.py`
instead of importing `crystalyse.ui.trace_handler.ToolTraceHandler`.

**Rationale**:
- Avoids a circular import (`crystalyse.provenance` ↔ `crystalyse.ui`)
- The provenance package stays importable on its own
- Duck typing preserves interface contract
- No runtime impact

**Consequence**: the local base class's `on_event()` body is `pass`, so
`enable_visual` (`CRYSTALYSE_VISUAL_TRACE`) renders nothing for
`ProvenanceTraceHandler` or its subclass. The real console tracer lives in
`crystalyse.ui.trace_handler`.

**Alternative Considered**: Restructure imports
- Rejected: Would require moving core CrystaLyse code
- Duck typing is cleaner and more Pythonic

### 4. Provenance as a Subpackage

**Decision**: Fold the provenance module into the package as
`crystalyse.provenance` rather than ship a standalone top-level module.

**Rationale**:
- Installs with the package; there is nothing to add to `sys.path`
- Relative imports (`from ..core import JSONLLogger`) keep the internals private
- One import path across editable installs, wheels and tests

**Legacy**: `cli.py` still contains a `sys.path` guard that looks for a
`provenance_system/` directory. That directory no longer exists, so the guard is
inert.

### 5. Integer Trace IDs

**Decision**: Build the trace_id from `int(time.time())` rather than
`asyncio.get_event_loop().time()`, and prefix the whole id with `trace_`.

**Rationale**:
- OpenAI SDK requires trace_id with only letters, numbers, underscores, dashes
- Float timestamps contain dots: `1234567890.123456` ❌
- Integer timestamps have no dots: `1234567890` ✅
- The OpenAI API additionally requires the id to start with `trace_`
- Still unique (second-level granularity sufficient)

**Result**: `trace_id = f"trace_crystalyse_{self.session_id}_{trace_timestamp}"`

### 6. JSONL for Events

**Decision**: Use JSON Lines (JSONL) format for events, not JSON array.

**Rationale**:
- Streaming-friendly (append-only)
- Each line is valid JSON (easy parsing)
- Works with line-based tools (grep, head, tail)
- No need to rewrite entire file on append

**Format**:
```jsonl
{"type": "event1", "data": {...}}
{"type": "event2", "data": {...}}
```

vs JSON array (rejected):
```json
[
  {"type": "event1", "data": {...}},
  {"type": "event2", "data": {...}}
]
```

---

## Future Enhancements

### 1. Energy Coverage for Undetected Tools

**Goal**: Attach energies from tool outputs the detector cannot identify.

**Implementation**:
- Extend `MCPDetector.TOOL_SIGNATURES` as new MCP tools land
- Teach `_extract_generic()` to walk nested payloads, not just top-level fields
- Surface `energy_coverage` (already computed by `get_summary()`) in the CLI table

**Benefit**: Energy statistics that reflect every costed structure.

### 2. Unified Session Mode (Optional)

**Goal**: Option to capture entire interactive chat session in one provenance directory.

**Implementation**:
- Add `--unified-session` flag to `crystalyse` command
- Create session directory at chat start
- Append queries as subdirectories or query-specific event streams
- Generate session-wide summary on exit

**Structure**:
```
crystalyse_auto_20251008_210000/
├── query_1/
│   ├── events.jsonl
│   └── materials_catalog.json
├── query_2/
│   ├── events.jsonl
│   └── materials_catalog.json
└── session_summary.json
```

### 3. Cross-Query Analytics

**Goal**: Compare and analyse multiple queries within same chat session.

**Features**:
- Track user preference evolution
- Compare discovery strategies across queries
- Session-wide materials deduplication

### 4. Provenance Compression

**Goal**: Reduce disk usage for long-term provenance storage.

**Implementation**:
- Compress old sessions (gzip)
- Archive by date (weekly/monthly)
- Prune old `raw_output_*.json` files while keeping summaries
- Configurable retention policies

### 5. Web UI for Provenance

**Goal**: Interactive web interface for provenance exploration.

**Features**:
- Timeline visualization of tool calls
- Materials explorer with filtering
- Performance charts (runtime, TTFB trends)
- Session comparison tools

---

## Troubleshooting

### Issue: Provenance Summary Shows 0 for All Metrics

**Symptom**:
```
MCP Tool Calls   │ 0
Total Tool Calls │ 0
```

**Cause**: Key mismatch between summary dict and display method.

**Solution**: Fixed in v1.0.0 (commit: fix(provenance): enable provenance capture)

**Verify Fix**:
```bash
pip install -e .  # Reinstall
crystalyse discover "test"
# Should show correct values
```

### Issue: Provenance System Handlers Not Available

**Symptom**:
```
WARNING: Provenance system handlers not available: <import error>
```

**Cause**: `from ..provenance.handlers import ProvenanceTraceHandler` failed - a
broken install or a missing dependency of the provenance package. (The old
`No module named 'provenance_system'` failure can no longer happen: provenance is
a subpackage of `crystalyse`.)

**Solution**:
1. Reinstall: `pip install -e .`
2. Check the reported import error for the missing dependency

**Verify**:
```bash
python -c "from crystalyse.provenance.handlers import ProvenanceTraceHandler; print('OK')"
```

### Issue: Circular Import Errors

**Symptom**:
```
ImportError: cannot import name 'ProvenanceTraceHandler' from partially initialized module
```

**Cause**: Circular dependency between `crystalyse.provenance` and `crystalyse.ui`.

**Solution**: Fixed by using duck typing in enhanced_trace.py (no import of ToolTraceHandler from crystalyse).

**Verify**:
```python
from crystalyse.provenance.handlers import ProvenanceTraceHandler
print("Import successful")
```

### Issue: SDK Trace ID Validation Errors

**Symptom**:
```
ERROR: Invalid 'data[0].trace_id': 'crystalyse_..._123.456'
Expected letters, numbers, underscores, or dashes
```

**Cause**: Float timestamp contains dots.

**Solution**: Fixed by using `int(time.time())` instead of `asyncio.get_event_loop().time()`.

**Verify**: Check that `agents_bridge.py` builds `trace_id` from `trace_timestamp = int(time.time())` and prefixes it with `trace_`.

### Issue: No Provenance in Interactive Chat

**Symptom**: `crystalyse discover` has provenance, but `crystalyse` (interactive) doesn't.

**Cause**: ChatExperience was using basic ToolTraceHandler.

**Solution**: Fixed in v1.0.0 (ChatExperience now creates CrystaLyseProvenanceHandler).

**Verify**:
```bash
crystalyse
➤ test query
# Should see "Provenance Summary" table after response
```

---

## Summary

The Crystalyse provenance system provides comprehensive, always-on audit trails for all materials discovery operations. It captures complete event streams, materials data, MCP tool calls, and performance metrics in a structured format suitable for reproducibility, debugging, and analysis.
