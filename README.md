# CrystaLyse.AI

**Status**: Early Development - Core Infrastructure Only

CrystaLyse.AI is a computational materials discovery platform in early development. Currently, only the basic infrastructure and MCP server integrations exist.

## Current Status

### ✅ What Works
- Basic agent framework with OpenAI Agents SDK
- MCP server connections (SMACT, Chemeleon, MACE, Unified)
- Infrastructure components (connection pooling, session management)
- Anti-hallucination detection system

### ❌ What Doesn't Work
- **Chemeleon**: Generates structures with `nan` coordinates
- **MACE**: Cannot process malformed structures from Chemeleon
- **End-to-end discovery**: No successful material discovery workflows
- **CLI**: Removed (was broken)
- **Examples**: Removed (didn't work)

## Repository Structure

```
CrystaLyse.AI/
├── crystalyse/                    # Core package
│   ├── agents/                    # Agent implementations
│   ├── infrastructure/            # Connection pooling, retries
│   ├── prompts/                   # System prompts
│   ├── utils/                     # Chemistry utilities  
│   └── validation/                # Response validation
├── chemistry-unified-server/      # Unified MCP server
├── smact-mcp-server/              # SMACT composition validation
├── chemeleon-mcp-server/          # Structure prediction (broken output)
├── mace-mcp-server/               # Energy calculations (broken input)
└── memory-implementation/         # Memory system components
```

## Installation

```bash
# Clone repository
git clone <repository-url>
cd CrystaLyse.AI

# Create environment
conda create -n crystalyse python=3.11
conda activate crystalyse

# Install core package
pip install -e .

# Install MCP servers
pip install -e ./smact-mcp-server
pip install -e ./chemeleon-mcp-server  
pip install -e ./mace-mcp-server
pip install -e ./chemistry-unified-server
```

## Basic Usage

```python
from crystalyse.agents.crystalyse_agent import CrystaLyse, AgentConfig

# Create agent
config = AgentConfig(mode="creative", model="o4-mini")
agent = CrystaLyse(agent_config=config)

# Note: Discovery will fail due to broken tool pipeline
result = await agent.discover_materials("Find battery materials")
```

## Known Issues

1. **Chemeleon Structure Generation**: Outputs `nan` values instead of coordinates
2. **MACE Energy Calculation**: Cannot process malformed CIF structures  
3. **Tool Pipeline**: Composition → Structure → Energy workflow is broken
4. **No Working Examples**: All previous examples have been removed

## Next Steps

1. Fix Chemeleon to generate valid coordinates
2. Ensure MACE can process Chemeleon outputs
3. Validate complete discovery pipeline
4. Add minimal working examples

## License

MIT License - see LICENSE for details.