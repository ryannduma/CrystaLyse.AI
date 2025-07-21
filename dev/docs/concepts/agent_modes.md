# Agent Execution Modes

## Overview

CrystaLyse.AI operates in two distinct execution modes that determine how the agent processes queries and maintains state. Understanding these modes is crucial for choosing the right approach for your materials design workflow.

## Agent Modes

### Analyse Mode (Autonomous)

**Purpose**: Single-shot autonomous analysis with direct results  
**Execution**: Stateless, self-contained processing  
**Memory**: No persistent memory between queries  
**Best for**: Quick analyses, batch processing, one-off questions

#### Characteristics
- **Autonomous Operation**: Agent independently processes the query end-to-end
- **Direct Results**: Immediate output without interactive elements
- **Stateless**: Each analysis is independent with no memory between queries
- **Efficient**: Optimised for single-purpose tasks
- **Batch-Friendly**: Suitable for automated workflows and scripting

#### CLI Usage
```bash
# Basic autonomous analysis
crystalyse analyse "Design a high-capacity Li-ion cathode material"

# Rigorous mode analysis
crystalyse analyse "Find stable perovskites for solar cells" --mode rigorous

# Batch processing friendly
crystalyse analyse "Thermoelectric materials with high ZT" --user-id batch_user
```

#### Python API Usage
```python
from crystalyse.agents.crystalyse_agent import CrystaLyse, AgentConfig

# Configure for autonomous analysis
config = AgentConfig(mode="rigorous", enable_memory=False)
agent = CrystaLyse(agent_config=config)

# Single-shot analysis
result = await agent.discover_materials(
    "Design cathode materials for sodium-ion batteries"
)

print(result['discovery_result'])
await agent.cleanup()
```

#### Workflow Pattern
```
User Query → Agent Processing → Tool Calls → Results → Output
    ↓              ↓               ↓          ↓        ↓
  "Design      Parse Query    SMACT/       Analyse   JSON/Text
   battery     & Generate     Chemeleon/   & Rank    Output
   cathode"    Candidates     MACE Calls   Results
```

### Chat Mode (Interactive Sessions)

**Purpose**: Interactive research sessions with persistent memory  
**Execution**: Stateful, conversation-aware processing  
**Memory**: Full session persistence and cross-query context  
**Best for**: Research projects, exploratory analysis, collaborative work

#### Characteristics
- **Session Persistence**: Maintains conversation history across interactions
- **Memory Integration**: Remembers previous analyses and discoveries
- **Context Continuity**: Builds upon previous queries and results
- **Interactive Commands**: Special commands for session management
- **Collaborative**: Multi-user session support

#### CLI Usage
```bash
# Start interactive session
crystalyse chat

# Named research session
crystalyse chat -s battery_research -u researcher1

# Resume previous session
crystalyse resume battery_research -u researcher1

# Collaborative session
crystalyse chat -s team_project -u team_member
```

#### Session Commands (within chat)
```bash
/history          # Show conversation history
/clear            # Clear conversation history
/undo             # Remove last interaction
/sessions         # List all sessions  
/resume <id>      # Resume a session
/help             # Show help
/exit             # Exit chat
```

#### Python API Usage
```python
from crystalyse.agents.session_based_agent import CrystaLyseSession

# Create session with memory
session = manager.get_or_create_session("research_project", "user_id")
await session.setup_agent("rigorous")

# Interactive queries with context
result1 = await session.run_with_history("Analyse LiCoO₂ cathode")
result2 = await session.run_with_history("What about volume changes?")
result3 = await session.run_with_history("Compare with experimental data")

# Session maintains full context
history = session.get_conversation_history()
await session.cleanup()
```

#### Workflow Pattern
```
User Query → Session Context → Agent Processing → Update Memory → Response
    ↓             ↓                ↓                 ↓            ↓
 "What about   Previous         Enhanced Query    Store New     Contextual
  stability?"  LiCoO₂ analysis  with Context     Discovery     Response
```

## Mode Comparison

| Aspect | Analyse Mode | Chat Mode |
|--------|--------------|-----------|
| **State** | Stateless | Stateful |
| **Memory** | None | Persistent |
| **Context** | Single query | Multi-turn conversation |
| **Performance** | Faster startup | Optimised for extended use |
| **Use Case** | Automation, batch | Research, exploration |
| **Output** | Direct results | Interactive responses |
| **Session Management** | None | Full session lifecycle |
| **Collaboration** | Individual | Multi-user support |
| **History** | No retention | Complete conversation history |
| **Commands** | Analysis only | Session management + analysis |

## Choosing the Right Mode

### Use Analyse Mode When:
- **One-off Questions**: Single analysis needs
- **Batch Processing**: Multiple independent analyses
- **Automated Workflows**: Scripting and integration
- **Performance Critical**: Fastest response time needed
- **Stateless Applications**: No need for memory
- **API Integration**: Programmatic access patterns

### Use Chat Mode When:
- **Research Projects**: Extended investigation periods
- **Exploratory Analysis**: Building on previous work
- **Collaborative Work**: Team-based materials design
- **Learning/Teaching**: Interactive educational sessions
- **Complex Queries**: Multi-step analysis workflows
- **Long-term Studies**: Days/weeks of investigation

## Technical Implementation

### Analyse Mode Architecture
```python
class CrystaLyseAgent:
    """Autonomous analysis agent - stateless operation"""
    
    async def discover_materials(self, query: str) -> dict:
        # Parse query
        # Generate candidates  
        # Validate with tools
        # Return results
        # No state retention
```

### Chat Mode Architecture
```python
class CrystaLyseSession:
    """Session-based agent with memory and context"""
    
    def __init__(self, session_id: str, user_id: str):
        self.conversation_history = []
        self.memory_system = SessionMemory()
        
    async def run_with_history(self, query: str) -> dict:
        # Retrieve conversation context
        # Enhanced query with history
        # Execute analysis
        # Store results in memory
        # Update conversation history
```

## Memory Systems Integration

### Analyse Mode Memory
- **No Persistence**: Results not retained between queries
- **Temporary Context**: Working memory only during execution  
- **Clean State**: Each analysis starts fresh
- **Cache Miss**: No benefit from previous calculations

### Chat Mode Memory
- **Full Persistence**: All conversations stored
- **Cross-Query Context**: Previous results inform new queries
- **Discovery Caching**: Computational results cached
- **Learning**: Pattern recognition across sessions

## Best Practices

### Analyse Mode Best Practices
1. **Clear Queries**: Be specific since no context is available
2. **Complete Information**: Include all relevant details in single query
3. **Batch Efficiently**: Group related analyses together
4. **Result Storage**: Save important results externally

### Chat Mode Best Practices  
1. **Session Names**: Use descriptive session identifiers
2. **Regular Summaries**: Generate periodic research summaries
3. **Clean Exits**: Use `/exit` to properly save session state
4. **Context Management**: Use `/clear` to reset when changing topics

## Migration Between Modes

### From Analyse to Chat
```python
# Start with autonomous analysis
result = await agent.discover_materials("Design battery cathode")

# Continue with interactive session
session = manager.create_session("battery_project", "user")
await session.run_with_history(
    f"Building on this analysis: {result['discovery_result']}, "
    f"what about thermal stability?"
)
```

### From Chat to Analyse
```python
# Export chat insights for autonomous processing
summary = session.generate_summary()

# Use in autonomous mode
result = await agent.discover_materials(
    f"Based on previous research: {summary}, "
    f"design optimised variants"
)
```

## Integration Patterns

### Hybrid Workflows
```python
# Research phase: Interactive exploration
session = manager.create_session("exploration", "researcher")
await session.run_with_history("Explore cathode materials")
await session.run_with_history("Focus on high-capacity options")

# Production phase: Batch autonomous analysis
candidates = session.get_discovered_materials()
for candidate in candidates:
    result = await agent.discover_materials(
        f"Detailed analysis of {candidate}"
    )
    store_result(result)
```

### API Integration
```python
# Web API endpoint using analyse mode
@app.post("/materials/analyse")
async def analyse_material(query: str):
    agent = CrystaLyse(AgentConfig(mode="rigorous"))
    result = await agent.discover_materials(query)
    await agent.cleanup()
    return result

# WebSocket endpoint using chat mode  
@app.websocket("/materials/chat")
async def chat_session(websocket, session_id: str):
    session = manager.get_or_create_session(session_id, user_id)
    await session.setup_agent("creative")
    
    async for message in websocket:
        result = await session.run_with_history(message)
        await websocket.send(result)
```

## Performance Considerations

### Analyse Mode Performance
- **Startup Time**: Minimal - no state to load
- **Memory Usage**: Low - no persistent storage
- **Scalability**: Excellent - stateless scaling
- **Throughput**: High - optimised for single queries

### Chat Mode Performance  
- **Startup Time**: Moderate - session state loading
- **Memory Usage**: Higher - conversation history retention
- **Scalability**: Good - session-based scaling
- **Throughput**: Optimised for sustained interaction

## Next Steps

- Explore [Dual-Mode System](dual_mode.md) for Creative vs Rigorous workflows
- Learn [Session Management](sessions.md) for chat mode operation
- Check [Memory Systems](memory.md) for persistence details
- Review [CLI Usage Guide](../guides/cli_usage.md) for practical examples