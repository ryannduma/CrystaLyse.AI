# Agent System

## Overview

Crystalyse v1.0.0 uses a single agent architecture built on the OpenAI Agents SDK. The `EnhancedCrystaLyseAgent` coordinates with MCP servers and workspace tools to provide materials discovery capabilities with adaptive clarification and provenance tracking.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                 EnhancedCrystaLyseAgent                      │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  OpenAI Agents SDK Integration                         │ │
│  │  • Session management (SQLite persistence)             │ │
│  │  • Tool orchestration                                  │ │
│  │  • Conversation handling                               │ │
│  └─────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │ MCP Servers     │  │ Workspace Tools  │  │ Memory      │ │
│  │ (Chemistry      │  │ (File Ops +      │  │ System      │ │
│  │ Tools)          │  │ Clarification)   │  │ (4-layer)   │ │
│  └─────────────────┘  └──────────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Core Agent: EnhancedCrystaLyseAgent

**Location**: `/dev/crystalyse/agents/openai_agents_bridge.py`

### Key Features

- **OpenAI Agents SDK Integration**: Built on the official Agents SDK with session management
- **Adaptive Clarification**: LLM-powered questioning that adapts to user expertise
- **Provenance Tracking**: Complete audit trail of all computational operations
- **Multi-Mode Operation**: Creative (~50s), Rigorous (2-5min), Adaptive (context-dependent)
- **Response Validation**: Anti-hallucination system validates all numerical claims
- **Session Persistence**: SQLite-based conversation storage

### Tool Integration

The agent coordinates with three types of tools:

**MCP Servers** (chemistry computations):
- Chemistry Creative Server: Chemeleon + MACE (~50s)
- Chemistry Unified Server: SMACT + Chemeleon + MACE + PyMatGen (2-5min)
- Visualisation Server: 3D rendering, XRD patterns, coordination analysis

**Workspace Tools** (file operations):
- File read/write with user approval
- Adaptive clarification system
- Progress tracking and visualization

**Memory Systems** (persistence):
- Session memory (conversation history)
- Discovery cache (computational results)
- User preferences (learning system)
- Cross-session context (research summaries)

## How the Agent Works

### 1. Query Processing

The agent accepts materials discovery queries in natural language:
- "Find stable perovskite solar cell materials"
- "Analyse CsSnI3 for photovoltaics"
- "Design high-capacity battery cathodes"

### 2. Mode-Based Tool Selection

Based on the selected mode, the agent routes to appropriate tools:

**Creative Mode** (~50 seconds):
- Uses Chemistry Creative Server
- Generates ~3 structure candidates
- Basic visualisation
- Fast screening workflow

**Rigorous Mode** (2-5 minutes):
- Uses Chemistry Unified Server
- Generates 30+ candidates with full validation
- SMACT composition screening
- PyMatGen phase diagram analysis
- Comprehensive visualisation

**Adaptive Mode** (default):
- Analyses query complexity
- Automatically selects creative or rigorous
- Balances speed and thoroughness

### 3. Analysis Pipeline

Standard materials discovery workflow:

1. **Parse Query**: Extract materials specifications and requirements
2. **Clarification** (if needed): Adaptive questioning based on expertise
3. **Composition Validation**: SMACT chemical feasibility (rigorous mode)
4. **Structure Generation**: Chemeleon DNG prediction
5. **Energy Calculation**: MACE formation energies
6. **Stability Analysis**: PyMatGen energy above hull (rigorous mode)
7. **Visualisation**: 3D structures, XRD patterns, coordination analysis
8. **Response Formation**: Synthesis with provenance tracking

### 4. Provenance Enforcement

Three-layer provenance system ensures computational honesty:

1. **Prompt Guidance**: Instructs agent to compute or decline
2. **Runtime Tracking**: Captures all tool outputs with metadata
3. **Render Gate**: Blocks unprovenanced numerical values from display

See [provenance_system.md](provenance_system.md) for details.

## Usage

### CLI Interface (Primary)

The agent is accessed through CLI commands:

```bash
# Non-interactive discovery
crystalyse discover "Find stable perovskites"

# Interactive chat session
crystalyse chat -u researcher -s battery_study

# With mode control
crystalyse --mode rigorous discover "Analyse CsSnI3"
```

### Programmatic Usage

For custom integrations:

```python
import asyncio
from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import Config

async def run_discovery():
    config = Config.load()

    agent = EnhancedCrystaLyseAgent(
        config=config,
        project_name="my_research",
        mode="creative",  # "creative", "rigorous", or "adaptive"
        model="o4-mini"   # or "o3" for rigorous mode
    )

    result = await agent.discover(
        query="Find stable perovskite materials",
        history=None  # Optional conversation history
    )

    print(result["status"])     # "completed" or "failed"
    print(result["response"])   # Agent's response text
    print(result["metadata"])   # Performance metrics

    return result

# Run
asyncio.run(run_discovery())
```

### Interactive Sessions

The agent supports persistent sessions through the chat command:

```bash
crystalyse chat -u researcher -s battery_project
```

Features:
- Conversation history persists across sessions
- User preferences learned over time
- Contextual understanding builds with interactions
- SQLite-based storage in `~/.crystalyse/`

## Configuration

### Basic Configuration

```python
from crystalyse.config import Config

# Load default configuration
config = Config.load()  # Reads ~/.crystalyse/config.yaml

# Create agent
agent = EnhancedCrystaLyseAgent(
    config=config,
    project_name="research_project",
    mode="adaptive",
    model="o4-mini"
)
```

### Config File

Create `~/.crystalyse/config.yaml`:

```yaml
# Model selection
default_model: "o4-mini"

# MCP server paths (auto-configured)
mcp_servers:
  chemistry_unified:
    command: "python"
    args: ["-m", "chemistry_unified.server"]
    cwd: "/path/to/chemistry-unified-server/src"

  chemistry_creative:
    command: "python"
    args: ["-m", "chemistry_creative.server"]
    cwd: "/path/to/chemistry-creative-server/src"

# Provenance (always enabled)
provenance:
  enabled: true
  output_dir: "./provenance_output"
  show_summary: true

# Timeouts by mode
timeouts:
  creative: 120
  adaptive: 180
  rigorous: 300
```

## Agent Capabilities

### Materials Science Understanding

The agent comprehends:
- Crystal structures and space groups
- Inorganic materials chemistry
- Formation energy and thermodynamic stability
- Structure-property relationships
- Materials design principles for batteries, solar cells, etc.

### Analysis Tasks

Core capabilities:
- **Structure Prediction**: AI-based crystal structure generation (Chemeleon)
- **Energy Calculation**: Formation energies with ML force fields (MACE)
- **Composition Validation**: Chemical feasibility screening (SMACT)
- **Stability Analysis**: Energy above hull calculations (PyMatGen)
- **Visualisation**: 3D structures, XRD patterns, coordination environments

### Natural Language Interface

Understands diverse query formats:
- "Find materials for X application"
- "Analyse Y composition for Z properties"
- "Design materials with W characteristics"
- "Compare A and B for performance"

## Best Practices

### Mode Selection

**Creative Mode** - Use for:
- Initial exploration
- Broad screening
- Rapid prototyping
- Time-sensitive analysis

**Rigorous Mode** - Use for:
- Final validation
- Publication-quality results
- Comprehensive characterisation
- Critical design decisions

**Adaptive Mode** - Use for:
- General research
- Unknown query complexity
- Learning the system
- Mixed workflows

### Query Formulation

**Good**: "Find perovskites with band gaps 1.2-1.6 eV"
- Specific properties
- Clear constraints

**Better**: "Design lead-free perovskite solar cell materials"
- Application context
- Material class specified

**Best**: "Find environmentally friendly perovskite alternatives to MAPbI3 for tandem solar cells"
- Complete context
- Performance requirements
- Design constraints

### Session Management

**For exploration**:
```bash
crystalyse discover "Quick query"  # No session persistence
```

**For research projects**:
```bash
crystalyse chat -u researcher -s project_name  # Full persistence
```

### Error Handling

The agent provides clear error messages:
- MCP server connection failures
- Invalid compositions
- Tool execution errors
- Timeout issues

Errors are logged with full context for debugging.

## Advanced Features

### Custom Callbacks

For custom UIs or integrations:

```python
from crystalyse.ui.progress import PhaseAwareProgress

# Custom progress handler
class CustomProgress(PhaseAwareProgress):
    def update(self, phase, message):
        # Custom progress display
        print(f"[{phase}] {message}")

# Use with agent
agent.discover(query, trace_handler=CustomProgress())
```

### Workspace Integration

The agent uses workspace tools for file operations:

```python
from crystalyse import workspace

# Set custom approval callback
def approve_file_write(path, content):
    print(f"About to write {len(content)} bytes to {path}")
    return True  # or False to deny

workspace.APPROVAL_CALLBACK = approve_file_write
```

### Memory Access

Access the memory system directly:

```python
from crystalyse.memory import CrystaLyseMemory

memory = CrystaLyseMemory(user_id="researcher")

# Get context for agent
context = memory.get_context_for_agent()

# Store discoveries
memory.store_discovery({
    "material": "CsSnI3",
    "formation_energy": -2.529,
    "timestamp": "2025-01-01T12:00:00"
})
```

## Performance Considerations

### Resource Usage

- **API Tokens**: ~1000-5000 tokens per query (model-dependent)
- **Memory**: ~500MB baseline + structure data
- **Disk**: Provenance output ~10-50MB per session
- **Time**: 50s (creative) to 5min (rigorous)

### Optimisation

1. **Use creative mode** for initial screening
2. **Enable caching** to avoid redundant computations
3. **Batch similar queries** in single sessions
4. **Clean old provenance data** periodically

### Monitoring

```python
# Check agent statistics
result = await agent.discover(query)

print(result["metadata"]["duration"])     # Execution time
print(result["metadata"]["tool_calls"])   # Number of tool invocations
print(result["metadata"]["model_used"])   # LLM model
```

## Next Steps

- Learn about [Analysis Modes](analysis_modes.md) for mode selection
- Explore [Clarification System](clarification_system.md) for adaptive UX
- Understand [Provenance System](provenance_system.md) for computational integrity
- See [Memory System](memory.md) for persistence details
