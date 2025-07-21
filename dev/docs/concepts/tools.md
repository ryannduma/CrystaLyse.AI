# Tool Integration

## Overview

CrystaLyse.AI's tool system provides agents with access to specialised materials science software, databases, and computational resources. The modular architecture allows seamless integration of diverse materials design tools through standardised Model Context Protocol (MCP) interfaces.

## Tool Architecture

### Tool Framework

```
┌─────────────────────────────────────────┐
│           Agent Core                    │
├─────────────────────────────────────────┤
│          Tool Manager                   │
├─────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │SMACT    │ │Chemeleon│ │MACE     │   │
│  │Tool     │ │Tool     │ │Tool     │   │
│  └─────────┘ └─────────┘ └─────────┘   │
├─────────────────────────────────────────┤
│          MCP Servers                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │Creative │ │Unified  │ │Visual.  │   │
│  │Server   │ │Server   │ │Server   │   │
│  └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────┘
```

### Tool Categories

#### 1. Core Materials Tools
- **SMACT**: Composition validation and screening
- **Chemeleon**: Crystal structure prediction
- **MACE**: Machine learning force fields
- **Visualisation Suite**: 3D structures and analysis plots (3dmol.js + Pymatviz)

#### 2. MCP Server Architecture
- **Chemistry Creative Server**: Fast structure generation (Chemeleon + MACE)
- **Chemistry Unified Server**: Complete validation (SMACT + Chemeleon + MACE)
- **Visualisation Server**: 3D structures and analysis plots
- **oldmcpservers**: Individual tool servers (SMACT, Chemeleon, MACE)

#### 3. Computational Framework
- **OpenAI Agents SDK**: Production-ready agent architecture
- **Model Context Protocol**: Seamless tool integration
- **Anti-hallucination**: 100% computational honesty validation
- **Session Management**: Persistent conversation and research tracking

#### 4. External Integration Capability
- **CIF File Support**: Standard crystallographic format
- **PDF Reports**: Professional analysis documentation
- **Interactive HTML**: Web-based 3D molecular viewers
- **Cross-platform**: Windows, macOS, Linux compatibility

## Built-in Tools

### SMACT Integration

Accessed through Chemistry Unified Server for composition validation:

```python
# Available through MCP server calls
# SMACT validates compositions based on chemical principles

# Example validation query
query = "Check if CsSnI3 is chemically feasible"
result = await unified_server.validate_composition("CsSnI3")

# SMACT screening pipeline:
# 1. Oxidation state analysis
# 2. Electronegativity ratios 
# 3. Chemical analogy to known compounds
# 4. Charge balance verification

# Output: Valid/invalid with confidence scores
```

### Chemeleon Integration

Accessed through both Creative and Unified servers for crystal structure prediction:

```python
# Available through MCP server calls
# Chemeleon generates high-quality crystal structures

# Example structure generation
query = "Generate crystal structures for CaTiO3"
result = await creative_server.predict_structure("CaTiO3")

# Chemeleon pipeline:
# 1. Composition analysis
# 2. Space group selection
# 3. Lattice parameter estimation
# 4. Atomic position optimisation
# 5. Structure refinement

# Output: Multiple candidate structures with CIF files
```

### MACE Integration

Accessed through both Creative and Unified servers for energy calculations:

```python
# Available through MCP server calls
# MACE provides fast, accurate energy calculations

# Example energy calculation
query = "Calculate formation energy for LiFePO4"
result = await unified_server.calculate_energy(structure_cif)

# MACE pipeline:
# 1. Structure input (CIF format)
# 2. Format conversion to MACE input
# 3. ML force field inference
# 4. Energy prediction with uncertainty
# 5. Result output with metadata

# Output: Formation energies with confidence estimates
```

## MCP Server Integration

### Visualisation Server Integration

Accessed through Visualisation MCP Server for 3D structures and analysis:

```python
# Available through MCP server calls
# Combines 3dmol.js with Pymatviz analysis suite

# Example visualisation request
query = "Visualise LiFePO4 structure with XRD pattern"
result = await viz_server.create_analysis(structure_cif)

# Visualisation pipeline:
# 1. 3D structure rendering (3dmol.js)
# 2. XRD pattern generation (Pymatviz)
# 3. RDF analysis (coordination environment)
# 4. Interactive HTML output generation
# 5. Professional PDF report creation

# Output: Interactive 3D viewer + analysis plots
```

### Complete Analysis Workflow

Integrated pipeline using all available tools:

```python
# Example complete materials design workflow
# Available through CrystaLyse.AI agent interface

# Rigorous mode (complete validation):
# 1. SMACT composition validation
# 2. Chemeleon structure generation  
# 3. MACE energy calculations
# 4. Visualisation with analysis plots

query = "Design a perovskite solar cell material"
result = await agent.analyse(query, mode="rigorous")

# Creative mode (fast exploration):
# 1. Chemeleon structure generation
# 2. MACE energy calculations
# 3. Basic visualisation

result = await agent.analyse(query, mode="creative")
```

### MCP Server Architecture

CrystaLyse.AI uses multiple MCP servers for tool access:

```python
# Server configuration in CrystaLyse.AI
servers = {
    "chemistry-creative-server": {
        "tools": ["chemeleon", "mace", "basic_visualisation"],
        "purpose": "Fast exploration (~50 seconds)"
    },
    "chemistry-unified-server": {
        "tools": ["smact", "chemeleon", "mace", "comprehensive_analysis"],
        "purpose": "Complete validation (2-5 minutes)"
    },
    "visualization-mcp-server": {
        "tools": ["3dmol_viewer", "pymatviz_analysis", "pdf_reports"],
        "purpose": "Interactive 3D and analysis plots"
    }
}

# Accessed through natural language interface
# No direct API calls - tools invoked by AI agent
```

## Custom Tool Development

### Creating Custom Tools

```python
from crystalyse.tools import BaseTool, ToolResult

class CustomAnalysisTool(BaseTool):
    name = "custom_analysis"
    description = "Performs custom materials analysis"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.setup_external_software()
    
    def execute(self, material, parameters=None):
        try:
            # Tool implementation
            result = self.run_analysis(material, parameters)
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "tool_version": self.version,
                    "execution_time": time.time() - start
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )
    
    def validate_input(self, material):
        # Input validation logic
        if not self.is_valid_formula(material):
            raise ValueError("Invalid chemical formula")
```

### Tool Registration

```python
from crystalyse import ToolManager

# Register custom tool
tool_manager = ToolManager()
tool_manager.register_tool(CustomAnalysisTool())

# Use in agent
agent = CrystaLyseAgent(tools=["rdkit", "custom_analysis"])
```

### MCP Server Development

Create custom MCP servers:

```python
from crystalyse.mcp import BaseMCPServer

class CustomMCPServer(BaseMCPServer):
    def __init__(self, port=8004):
        super().__init__(name="custom_server", port=port)
        self.register_endpoints()
    
    def register_endpoints(self):
        @self.route("/analyse", methods=["POST"])
        def analyse_endpoint():
            material = request.json.get("material")
            result = self.perform_analysis(material)
            return {"result": result}
    
    def perform_analysis(self, material):
        # Custom materials analysis implementation
        return analysis_results

# Start server
server = CustomMCPServer()
server.start()
```

## Tool Configuration

### Basic Configuration

```python
# Configure tools
tool_config = {
    "chemistry_unified_server": {
        "timeout": 120,
        "cache_enabled": True,
        "tools": ["smact", "chemeleon", "mace"]
    },
    "chemistry_creative_server": {
        "timeout": 60,
        "cache_enabled": True,
        "tools": ["chemeleon", "mace"]
    },
    "visualization_server": {
        "timeout": 90,
        "cache_enabled": True,
        "tools": ["3dmol", "pymatviz"]
    },
    "creative_server": {
        "host": "localhost",
        "port": 8001,
        "max_generations": 100
    }
}

agent = CrystaLyseAgent(tool_config=tool_config)
```

### Advanced Configuration

```python
# MCP Server-specific parameters
creative_server_config = {
    "chemeleon": {
        "num_structures": 3,
        "space_groups": "auto",
        "optimization_steps": 100
    },
    "mace": {
        "calculation_type": "formation_energy",
        "uncertainty_quantification": False
    }
}

unified_server_config = {
    "smact": {
        "use_pauling_test": True,
        "include_alloys": True,
        "oxidation_states_set": "icsd24"
    },
    "chemeleon": {
        "num_structures": 5,
        "space_groups": "all",
        "optimization_steps": 500
    },
    "mace": {
        "calculation_type": "formation_energy",
        "uncertainty_quantification": True
    }
}
```

## Tool Orchestration

### Sequential Tool Execution

```python
# CrystaLyse.AI handles workflow automatically
# Rigorous mode workflow:
rigorous_workflow = [
    "SMACT composition validation",
    "Chemeleon structure generation", 
    "MACE energy calculations",
    "Comprehensive visualisation and analysis"
]

# Creative mode workflow:
creative_workflow = [
    "Chemeleon structure generation",
    "MACE energy calculations", 
    "Basic 3D visualisation"
]

# Execute through natural language
results = await agent.analyse("Analyse LiFePO4 for battery applications", mode="rigorous")
```

### Parallel Tool Execution

```python
# CrystaLyse.AI automatically parallelises where possible
# Creative mode: Chemeleon + MACE run in parallel for multiple structures
# Unified mode: Full pipeline with optimised tool orchestration
# Visualisation: 3D rendering + analysis plots generated concurrently

# Tools are invoked automatically based on query and mode
# No manual parallel task management required
results = await agent.analyse("Compare olivine vs spinel structures for LiFePO4")
```

### Conditional Tool Selection

```python
# CrystaLyse.AI automatically selects appropriate tools based on:
# 1. Analysis mode (creative vs rigorous)
# 2. Query requirements (structure, energy, validation)
# 3. Material complexity (number of elements, structure type)

# Mode-based tool selection:
mode_tools = {
    "creative": ["chemeleon", "mace", "basic_viz"],
    "rigorous": ["smact", "chemeleon", "mace", "comprehensive_viz"]
}

# Automatic selection - no manual configuration needed
query = "Design cathode materials for Na-ion batteries"
results = await agent.analyse(query, mode="rigorous")  # Auto-selects full tool suite
```

## Error Handling and Resilience

### Tool Failure Management

```python
from crystalyse.tools import ToolManager

tool_manager = ToolManager(
    fallback_strategy="graceful",
    retry_attempts=3,
    timeout_seconds=60
)

# Fallback configuration
# CrystaLyse.AI built-in resilience
fallbacks = {
    "chemistry_unified_server": ["chemistry_creative_server", "individual_tools"],
    "chemistry_creative_server": ["individual_oldmcpservers"],
    "visualization_server": ["basic_cif_output", "text_descriptions"]
}

# Individual tool fallbacks from oldmcpservers
individual_fallbacks = {
    "smact-mcp-server": ["basic_composition_validation"],
    "chemeleon-mcp-server": ["simple_structure_templates"],
    "mace-mcp-server": ["approximate_energy_estimates"]
}

tool_manager.configure_fallbacks(fallbacks)
```

### Monitoring and Logging

```python
# Enable tool monitoring
tool_manager.enable_monitoring(
    log_level="INFO",
    track_performance=True,
    alert_on_failures=True
)

# Get tool statistics
stats = tool_manager.get_statistics()
print(f"Success rate: {stats.success_rate}%")
print(f"Average response time: {stats.avg_response_time}ms")
print(f"Tool usage: {stats.tool_usage}")
```

## Performance Optimisation

### Caching

```python
# Enable result caching
tool_manager.enable_caching(
    cache_type="redis",
    ttl_seconds=3600,
    max_cache_size="1GB"
)

# Cache hit monitoring
cache_stats = tool_manager.get_cache_statistics()
print(f"Cache hit rate: {cache_stats.hit_rate}%")
```

### Rate Limiting

```python
# Configure rate limits
# CrystaLyse.AI MCP server rate limits
rate_limits = {
    "chemistry_unified_server": {"requests_per_minute": 10},
    "chemistry_creative_server": {"requests_per_minute": 20},
    "visualization_server": {"requests_per_minute": 15}
}

# Local computation limits
computation_limits = {
    "max_concurrent_structures": 5,
    "max_atoms_per_structure": 200,
    "timeout_per_calculation": 300  # seconds
}

tool_manager.configure_rate_limits(rate_limits)
```

### Async Execution

```python
# CrystaLyse.AI handles async execution internally
# Agent automatically manages:
# - Concurrent MCP server connections
# - Parallel structure generation and energy calculations
# - Asynchronous visualisation rendering
# - Session persistence and memory management

# Simple interface for complex async operations
result = await agent.analyse(
    "Find stable perovskites for photovoltaic applications",
    mode="rigorous"
)

# Result includes all tool outputs integrated and validated
```

## Best Practices

### 1. Tool Selection

- Use minimal tool set for efficiency
- Configure fallbacks for critical tools
- Monitor tool performance regularly
- Update tools and configurations periodically

### 2. Data Flow

```python
# CrystaLyse.AI optimised data flow
# Tools communicate through standardised CIF format:
# SMACT (composition) -> Chemeleon (structure/CIF) -> MACE (energy) -> Visualisation

# Memory-efficient streaming:
# - Structures passed as CIF strings
# - Incremental result building
# - Automatic cleanup of intermediate files
# - Session-based caching for repeated queries

# Single interface for complete pipeline
result = await agent.analyse(material_query)
```

### 3. Resource Management

- Set appropriate timeouts
- Limit concurrent tool executions
- Monitor memory usage
- Clean up temporary files

### 4. Security

```python
# Secure tool configuration
# CrystaLyse.AI security configuration
tool_config = {
    "mcp_servers": {
        "chemistry_unified_server": {
            "host": "localhost",
            "port": 8001,
            "timeout": 120
        },
        "chemistry_creative_server": {
            "host": "localhost",  
            "port": 8002,
            "timeout": 60
        },
        "visualization_server": {
            "host": "localhost",
            "port": 8003,
            "timeout": 90
        }
    },
    "sandbox_enabled": True,
    "local_computation_only": True,
    "no_external_apis": True
}
```

## Next Steps

- Explore [Agent Integration](agents.md) with tools
- Learn about [MCP Server Development](../guides/mcp_development.md)
- Check [API Reference](../reference/tools/) for detailed documentation
- Read [Performance Guide](../guides/performance.md) for optimisation