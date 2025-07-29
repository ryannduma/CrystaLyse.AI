# CrystaLyse.AI 2.0 Agents

## Overview

CrystaLyse.AI 2.0 features an enhanced agent system built on the OpenAI Agents SDK. The system uses a single sophisticated agent (`EnhancedCrystaLyseAgent`) that coordinates with specialized tools and MCP servers to provide advanced materials discovery capabilities with enhanced UX features.

## Agent Architecture

### Current Implementation

```
┌──────────────────────────────────────────────────────────────┐
│                 Enhanced Agent System                         │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           EnhancedCrystaLyseAgent                       │ │
│  │  - OpenAI Agents SDK Integration                       │ │
│  │  - Enhanced Clarification System                       │ │
│  │  - Workspace Management                                │ │
│  │  - Multi-Mode Operation (adaptive/creative/rigorous)   │ │
│  │  - Session-Based Memory                                │ │
│  └─────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │ MCP Server      │  │ Workspace        │  │ Memory      │ │
│  │ Coordination    │  │ Tools            │  │ System      │ │
│  │ (Chemistry      │  │ (File Ops +      │  │ (Session +  │ │
│  │ Tools)          │  │ Clarification)   │  │ Discovery)  │ │
│  └─────────────────┘  └──────────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Core Agent: EnhancedCrystaLyseAgent

The main agent class provides all materials discovery functionality through intelligent tool coordination:

### Key Features
- **OpenAI Agents SDK Integration**: Production-ready agent framework with proper session management
- **Enhanced Clarification System**: LLM-powered adaptive questioning based on user expertise
- **Workspace Management**: Transparent file operations with preview/approval workflows
- **Multi-Mode Operation**: Adaptive, creative, and rigorous analysis modes
- **Anti-Hallucination**: Response validation to ensure computational honesty
- **Session Persistence**: SQLite-based conversation and discovery memory

### Tool Integration Architecture

The agent coordinates with various tools and services:

#### MCP Server Integration
- **Chemistry Creative Server**: Fast exploration tools (Chemeleon + MACE + Visualization)
- **Chemistry Unified Server**: Complete validation tools (SMACT + Chemeleon + MACE + Analysis)
- **Visualization Server**: Advanced 3D rendering and analysis plots

#### Workspace Tools
- **File Operations**: Read, write, and list files with user preview/approval
- **Clarification System**: Adaptive questioning based on user expertise and context
- **Session Management**: Persistent conversation storage and retrieval

#### Memory Systems
- **Session Memory**: SQLite-based conversation persistence
- **Discovery Cache**: Computational results caching to avoid redundancy
- **User Preferences**: Learning system that adapts to user patterns

## How Agents Work

### 1. Input Processing

Agents accept various input formats:
- Chemical formulas (e.g., CaTiO3, LiFePO4)
- Materials names (e.g., perovskite, spinel)
- Natural language queries (e.g., "Find stable cathode materials")
- Crystal structure files (CIF format)
- Composition specifications (e.g., "lithium iron phosphate")

### 2. Tool Selection

Agents intelligently select appropriate tools based on analysis mode:
```python
# Creative Mode (Fast Exploration)
if mode == "creative":
    use_tools = ["chemeleon_mcp", "mace_mcp", "visualisation_server"]

# Rigorous Mode (Complete Validation)
elif mode == "rigorous":
    use_tools = ["smact_mcp", "chemeleon_mcp", "mace_mcp", 
                 "visualisation_server", "analysis_suite"]
```

### 3. Analysis Pipeline

The standard materials analysis flow:
1. **Parse Input**: Convert to standardised materials representation
2. **Composition Validation**: SMACT screening for chemical feasibility (rigorous mode)
3. **Structure Generation**: Chemeleon crystal structure prediction
4. **Energy Calculation**: MACE formation energy evaluation
5. **Analysis & Visualisation**: XRD patterns, 3D structures, coordination analysis
6. **Results Synthesis**: Combine outputs with uncertainty quantification
7. **Format Response**: Present findings with scientific integrity

### 4. Memory Integration

Agents utilise multiple memory types:
- **Working Memory**: Current analysis context
- **Session Memory**: Conversation history
- **Discovery Memory**: Important findings
- **User Memory**: Preferences and history

## Agent Capabilities

### Materials Science Understanding

Agents comprehend:
- Crystal structures and space groups
- Inorganic materials chemistry
- Formation energy and thermodynamic stability
- Structure-property relationships in materials
- Materials design principles

### Analysis Tasks

Core analytical capabilities:
- **Structure Prediction**: Crystal structure generation using AI models
- **Energy Calculation**: Formation energies with uncertainty quantification
- **Composition Validation**: Chemical feasibility screening
- **Stability Analysis**: Thermodynamic stability assessment
- **Visualisation**: 3D crystal structures, XRD patterns, coordination analysis

### Natural Language Interface

Agents understand materials design queries in plain English:
- "Find stable perovskite materials for solar cells"
- "What's the formation energy of LiFePO4?"
- "Design high-capacity battery cathode materials"
- "Analyse CaTiO3 for photocatalytic applications"

## Configuration

### Basic Agent Configuration

```python
from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import Config

# Basic configuration
config = Config.load()
agent = EnhancedCrystaLyseAgent(
    config=config,
    project_name="my_research",
    mode="adaptive",  # "creative", "rigorous", or "adaptive" (default)
    model="o4-mini"   # or "o3" for rigorous mode
)
```

### Advanced Usage

```python
# Using the agent for discovery
async def run_discovery():
    result = await agent.discover(
        query="Find stable perovskite materials for solar cells",
        history=None,  # Optional conversation history
        trace_handler=None  # Optional event handler for UI
    )
    
    print(result["status"])     # "completed" or "failed"
    print(result["response"])   # Agent's response
    return result
```

## Working with Agents

### Simple Analysis

```python
# Basic materials analysis
result = agent.analyse("LiFePO4")
print(result.formation_energy)
print(result.crystal_structure)
print(result.summary)
```

### Interactive Sessions

```python
# Start an interactive session
session = agent.create_session("battery_materials_project")

# Maintain context across queries
session.query("Analyse LiFePO4 cathode material")
session.query("What about other lithium iron phosphates?")
session.query("Which has the highest capacity?")
```

### Batch Processing

```python
# Analyse multiple materials
materials = ["LiFePO4", "LiCoO2", "LiNi0.5Mn1.5O4"]
results = agent.batch_analyse(materials)

for material, result in results:
    print(f"{material}: Formation Energy = {result.formation_energy} eV/atom")
```

## Best Practices

### 1. Choose the Right Agent

- Use `CrystaLyseAgent` for one-off analyses
- Use `SessionBasedAgent` for research projects
- Use specialised agents for domain-specific tasks

### 2. Optimise Tool Selection

- Enable only necessary tools to improve performance
- Configure tool-specific parameters for your use case
- Consider tool dependencies and ordering

### 3. Manage Context

- Clear context between unrelated analyses
- Use sessions for related queries
- Export important discoveries for future reference

### 4. Handle Errors Gracefully

```python
try:
    result = agent.analyse(smiles)
except InvalidStructureError:
    print("Invalid molecular structure")
except ToolError as e:
    print(f"Tool error: {e.tool_name} - {e.message}")
```

## Advanced Features

### Custom Tools

Extend agents with custom tools:
```python
from crystalyse.tools import Tool

class CustomTool(Tool):
    def execute(self, molecule):
        # Custom analysis logic
        return results

agent.register_tool(CustomTool())
```

### Agent Composition

Combine multiple agents:
```python
synthesis_agent = SynthesisAgent()
property_agent = PropertyAgent()

# Coordinate agents
compound = "target_smiles"
routes = synthesis_agent.plan_synthesis(compound)
properties = property_agent.predict_properties(compound)
```

### Fine-tuning

Customise agent behaviour:
```python
agent.fine_tune(
    examples=[
        {"input": "...", "output": "..."},
        # More examples
    ],
    domain="medicinal_chemistry"
)
```

## Performance Considerations

### Resource Usage

- Agents consume API tokens for LLM calls
- Chemistry tools may require significant computation
- Memory usage scales with session history

### Optimisation Tips

1. **Cache Results**: Enable caching for repeated analyses
2. **Batch Requests**: Process multiple molecules together
3. **Limit Context**: Clear old context to reduce token usage
4. **Tool Selection**: Disable unnecessary tools

### Monitoring

Track agent performance:
```python
stats = agent.get_statistics()
print(f"Total queries: {stats.query_count}")
print(f"Average response time: {stats.avg_response_time}")
print(f"Tool usage: {stats.tool_usage}")
```

## Next Steps

- Learn about [Memory Systems](memory.md) for context management
- Explore [Session Management](sessions.md) for persistent analysis
- Understand [Tool Integration](tools.md) for extending capabilities
- See [API Reference](../reference/agents/) for detailed documentation