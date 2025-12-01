# CLI Architecture - CrystaLyse.AI v1.0.0

## Overview

CrystaLyse.AI v1.0.0 provides a unified CLI architecture built on a single enhanced agent (`EnhancedCrystaLyseAgent`) that coordinates with specialized tools and MCP servers. This document clarifies the actual implementation versus documentation discrepancies.

## Agent Architecture Reality

### Single Agent Implementation

**Actual Implementation**: One main agent class - `EnhancedCrystaLyseAgent`
- **Location**: `/dev/crystalyse/agents/openai_agents_bridge.py`
- **Role**: Handles all materials discovery functionality through intelligent tool coordination

**Documentation Discrepancy**: Previous docs described multiple specialized agents (MaterialsOrchestrator, CompositionExplorer, etc.) that **do not exist as separate classes**

### How the Single Agent Works

The `EnhancedCrystaLyseAgent` provides "multi-agent-like" behavior through:

1. **Intelligent Tool Coordination**: Automatically selects appropriate MCP servers based on mode
2. **Workspace Management**: Handles file operations with user preview/approval
3. **Clarification System**: Adaptive questioning based on user expertise
4. **Memory Integration**: Session persistence and discovery caching
5. **Mode-Aware Processing**: Different behavior for creative/rigorous/adaptive modes

## CLI Entry Points

### Primary Entry Point: `crystalyse`

**Configuration**: `pyproject.toml` → `crystalyse = "crystalyse.cli:main"`

**Available Commands**:

```bash
crystalyse discover "query"              # Non-interactive discovery
crystalyse chat -u user -s session      # Interactive chat session  
crystalyse user-stats -u user            # User preference statistics
```

**Global Options**:
```bash
--project, -p        # Project name for workspace (default: crystalyse_session)
--mode              # Agent mode: adaptive/creative/rigorous (default: adaptive)
--model             # Language model to use (default: auto-select)
--verbose, -v       # Enable verbose output
--version           # Show version and exit
```

### UI Implementation

The CLI uses a modular UI system located in `crystalyse/ui/`:
- **chat_ui.py**: Main interactive chat interface
- **enhanced_clarification.py**: Adaptive clarification system
- **slash_commands.py**: In-session command handling
- **trace_handler.py**: Tool execution visualization
- **user_preference_memory.py**: User preference tracking

## Command Behavior and Agent Usage

### `crystalyse discover "query"`

**Purpose**: Non-interactive, single-shot analysis ideal for scripting

**Agent Creation** (line 174 in cli.py):
```python
agent = EnhancedCrystaLyseAgent(
    config=Config.load(),
    project_name=state['project'],
    mode=state['mode'].value,
    model=state['model'],
)
```

**Features**:
- Uses workspace tools with non-interactive callbacks
- Direct results display suitable for automation
- Progress visualization with PhaseAwareProgress
- Automatic mode selection based on global options

**Example Usage**:
```bash
# Quick creative analysis
crystalyse discover "Find perovskite solar cell materials" --mode creative

# Detailed rigorous analysis
crystalyse discover "Analyze CsSnI3 stability for photovoltaics" --mode rigorous

# Adaptive analysis (default)
crystalyse discover "Battery cathode materials for Li-ion cells"
```

### `crystalyse chat -u user -s session`

**Purpose**: Interactive research session with enhanced UX

**Agent Creation** (via ChatExperience in ui/chat_ui.py):
```python
agent = EnhancedCrystaLyseAgent(
    config=config,
    project_name=self.project,
    mode=self.mode,
    model=self.model
)
```

**Enhanced Features**:
- **Enhanced Clarification System**: Adaptive questioning based on expertise
- **User Preference Learning**: System learns from interactions
- **Session Persistence**: SQLite-based conversation storage
- **Cross-Session Context**: Building understanding across sessions
- **Mode Switching**: Dynamic adaptation during conversation

**In-Session Commands**:
```bash
/mode creative|rigorous|adaptive    # Switch analysis mode
/history                           # View conversation history
/clear                            # Clear conversation context
/help                             # Show available commands
/exit                             # Save session and exit
```

**Example Usage**:
```bash
# Start research session
crystalyse chat -u researcher1 -s battery_project

# Resume existing session  
crystalyse chat -u researcher1 -s battery_project

# Quick anonymous session
crystalyse chat
```

### `crystalyse user-stats -u user`

**Purpose**: Display user learning profile and preferences

**Implementation**: Direct access to UserPreferenceMemory (no agent used)

**Output Example**:
```
┌─────────────────────────────────────────────────────────────┐
│                 CrystaLyse Learning Profile                 │
├─────────────────────────────────────────────────────────────┤
│ User: researcher1                                           │
│ Interactions: 15                                            │
│ Detected Expertise: Expert                                  │
│ Speed Preference: Balanced (0.6)                            │
│ Successful Modes: rigorous (90%), creative (70%)           │
│ Domain Familiarity:                                         │
│   • Batteries: Expert (0.9)                               │
│   • Photovoltaics: Intermediate (0.6)                     │
│   • Thermoelectrics: Novice (0.3)                         │
└─────────────────────────────────────────────────────────────┘
```

## Mode-Specific Behavior

### Adaptive Mode (Default)

**Agent Behavior**:
- Automatically selects optimal tools based on query complexity
- Uses enhanced clarification system for user interaction
- Balances speed and accuracy based on context
- Learns user preferences over time

**MCP Server Selection**: Context-dependent (unified or creative server)

### Creative Mode

**Agent Behavior**:
- Optimized for speed (~50 seconds)
- Uses basic visualization
- Minimal validation for rapid exploration

**MCP Server**: Chemistry Creative Server (Chemeleon + MACE + Basic Viz)

### Rigorous Mode  

**Agent Behavior**:
- Comprehensive validation (2-5 minutes)
- Full analysis suite with anti-hallucination checks
- Publication-quality results

**MCP Server**: Chemistry Unified Server (SMACT + Chemeleon + MACE + Advanced Analysis)

## Tool Coordination Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                EnhancedCrystaLyseAgent                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ MCP Server      │  │ Workspace       │  │ Memory      │ │
│  │ Coordination    │  │ Tools           │  │ Systems     │ │
│  │                 │  │                 │  │             │ │
│  │ • Chemistry     │  │ • File Ops      │  │ • Session   │ │
│  │   Creative      │  │ • Clarification │  │ • Discovery │ │
│  │ • Chemistry     │  │ • Preview       │  │ • User      │ │
│  │   Unified       │  │ • Approval      │  │ • Cache     │ │
│  │ • Visualization │  │                 │  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Integration

### Config Loading
```python
config = Config.load()  # Loads from ~/.crystalyse/config.yaml
```

### MCP Server Selection
```python
server_configs = {
    "creative": "chemistry_creative",
    "rigorous": "chemistry_unified", 
    "adaptive": "chemistry_unified",
}
```

### Model Selection
```python
def _select_model_for_mode(self, mode: str) -> str:
    return {
        "creative": "o4-mini", 
        "rigorous": "o3", 
        "adaptive": "o4-mini"
    }.get(mode, "o4-mini")
```

## Best Practices

### Command Selection

**Use `discover` when**:
- Scripting or automation
- Single-shot analysis needed
- Non-interactive environment
- CI/CD pipelines

**Use `chat` when**:
- Interactive research sessions
- Building on previous work
- Learning about materials
- Complex multi-part queries

**Use `user-stats` when**:
- Understanding user learning profile
- Debugging preference issues
- Research on user interaction patterns

### Mode Selection

**Adaptive** (recommended default):
- General research scenarios
- First-time users
- Mixed exploration/validation workflows

**Creative** for:
- Rapid screening
- Initial concept exploration
- Time-sensitive analysis

**Rigorous** for:
- Publication-quality results
- Critical validation
- Comprehensive analysis

## Error Handling and Fallbacks

### Agent Failures
- Graceful degradation to simpler modes
- Clear error messages with suggested actions
- Automatic retry with different configurations

### MCP Server Issues
- Automatic fallback to alternative servers
- User notification of reduced functionality
- Detailed logging for debugging

### Clarification Failures
- Fallback to interactive mode
- Manual parameter input options
- Default assumption application with user confirmation

This architecture provides a robust, user-friendly interface while maintaining the flexibility and power of the underlying materials discovery platform.