# SMACT MCP Server Implementation Notes

## Status: ✅ COMPLETED

Both SMACT MCP servers have been successfully implemented:

### 1. **smact-mcp-server** (Full Implementation)
- **Location**: `/home/ryan/crystalyseai/smact-mcp-server/`
- **Tools Implemented**:
  - `check_smact_validity` - Full validity checking with multiple options
  - `calculate_neutral_ratios` - Charge-neutral stoichiometry calculation
  - `parse_chemical_formula` - Parse formulas into element counts
  - `get_element_info` - Detailed element properties
  - `test_pauling_rule` - Electronegativity test

### 2. **smact-minimal-mcp** (Minimal Implementation) 
- **Location**: `/home/ryan/crystalyseai/smact-minimal-mcp/`
- **Tools Implemented**:
  - `smact_validity_check` - Simple validity checking tool
- **Purpose**: Testing and demonstration

## Installation Instructions

### Prerequisites
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

### Full Server Setup
```bash
cd /home/ryan/crystalyseai/smact-mcp-server
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Minimal Server Setup
```bash
cd /home/ryan/crystalyseai/smact-minimal-mcp
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Claude Desktop Configuration

### For Full Server
Add to `claude_desktop_config.json`:
```json
{
    "mcpServers": {
        "smact": {
            "command": "/path/to/uv",
            "args": [
                "run",
                "--directory",
                "/FULL/PATH/TO/smact-mcp-server",
                "smact-mcp"
            ]
        }
    }
}
```

### For Minimal Server
```json
{
    "mcpServers": {
        "smact-minimal": {
            "command": "/path/to/uv",
            "args": [
                "run",
                "--directory", 
                "/FULL/PATH/TO/smact-minimal-mcp",
                "smact-minimal"
            ]
        }
    }
}
```

## Testing Commands

Once configured in Claude Desktop, try these prompts:

### Basic Validity Testing
- "Is LiFePO4 a valid composition?"
- "Check if CaTiO3 is chemically valid"
- "Validate these compositions: NaCl, CaF3, Li2SO4"

### Advanced Testing (Full Server Only)
- "Parse the formula Ca(OH)2 and tell me about each element"
- "Calculate neutral ratios for oxidation states [2, -1]"
- "Get detailed information about the element Iron"
- "Test if Li (+1) and O (-2) satisfy Pauling's rule"

## Key Features

### Error Handling
- Graceful degradation when SMACT data is missing
- Detailed error messages for debugging
- JSON-formatted responses for consistency

### Performance Optimizations
- Pre-loaded element dictionary on startup
- Efficient SMACT path resolution
- Minimal dependencies for faster startup

### Architecture Benefits
- **Isolation**: SMACT runs in separate process
- **Modularity**: Easy to add/remove tools
- **Compatibility**: Works with any MCP client
- **Scalability**: Can run multiple instances

---

# Next Steps: Building the Agent Side

## Phase 1: Basic Agent Setup

### 1. Create CrystaLyse Agent Structure
```bash
mkdir -p /home/ryan/crystalyseai/crystalyse-agent/src/crystalyse_agent
```

### 2. Required Dependencies
```toml
[project]
dependencies = [
    "agents>=0.1.0",  # OpenAI Agents SDK
    "mcp>=0.5.0",     # MCP client
    "pymatgen>=2024.1.0",
    "pandas>=2.0.0",
    "asyncio-mqtt>=0.11.0",  # For async operations
]
```

### 3. Core Components to Implement

#### A. MCP Client Wrapper (`mcp_client.py`)
```python
class MaterialsDesignMCPClient:
    """Enhanced MCP client for materials design."""
    
    async def connect(self):
        # Connect to SMACT MCP server
        
    async def validate_composition_batch(self, compositions: List[str]):
        # Batch validation with intelligent interpretation
        
    async def generate_neutral_combinations(self, elements: List[str]):
        # Generate valid compositions from elements
```

#### B. CrystaLyse Agent (`agent.py`)
```python
from agents import Agent

crystalyse_agent = Agent(
    name="CrystaLyse",
    model="gpt-4",
    instructions=SYSTEM_PROMPT,  # From agent_implementation_scp.md
    temperature=0.7
)

@tool
async def design_material_for_application(
    ctx: AgentContext,
    application: str,
    constraints: Dict[str, Any] = None
) -> str:
    # Main orchestration tool
```

#### C. Materials Knowledge Base (`knowledge.py`)
```python
class MaterialsKnowledgeBase:
    """Chemical reasoning and structure prediction."""
    
    def predict_structure_types(self, composition: str) -> List[Dict]:
        # Perovskite, spinel, layered structure prediction
        
    def analyse_application_requirements(self, app: str) -> Dict:
        # Map applications to element/property requirements
        
    def suggest_synthesis_routes(self, composition: str) -> List[str]:
        # Basic synthesis pathway suggestions
```

## Phase 2: Tool Implementation

### Core Tools to Implement

1. **`generate_compositions`**
   - Input: elements, constraints, target_count
   - Uses SMACT + creative chemical reasoning
   - Returns ranked candidates with validation status

2. **`predict_structure_types`**
   - Input: composition, application
   - Heuristics: tolerance factors, ionic radii, coordination
   - Returns structure predictions with confidence

3. **`design_material_for_application`**
   - Main orchestration tool
   - Combines element selection, generation, validation, ranking
   - Returns top 5 candidates with structures

4. **`explain_chemical_reasoning`**
   - Justifies agent decisions
   - Explains SMACT overrides
   - Provides synthesis feasibility

## Phase 3: Integration Strategy

### Agent-MCP Integration Pattern
```python
# 1. Agent proposes candidates using chemical knowledge
candidates = await agent.generate_creative_compositions(requirements)

# 2. MCP validates candidates
validation_results = await mcp_client.validate_composition_batch(candidates)

# 3. Agent decides: accept, override with justification, or revise
for candidate in candidates:
    if validation_results[candidate]["smact_valid"]:
        accept_candidate(candidate)
    elif can_override_with_justification(candidate, validation_results):
        override_with_reasoning(candidate, "Intermetallic exception")
    else:
        revise_candidate(candidate)
```

### Override Decision Logic
```python
def can_override_smact(composition: str, validation_data: Dict) -> bool:
    """Determine if agent can override SMACT with justification."""
    
    reasons = []
    
    # High metallicity -> likely intermetallic
    if validation_data.get("metallicity_score", 0) > 0.9:
        reasons.append("High metallicity indicates intermetallic compound")
    
    # Known structural families with exceptions
    if is_heusler_family(composition):
        reasons.append("Heusler alloy family known to violate standard rules")
        
    # Application-specific relaxed rules
    if context.get("application") == "superconductor":
        reasons.append("Unconventional compositions viable for superconductivity")
        
    return len(reasons) > 0, reasons
```

## Phase 4: Testing & Validation

### Test Cases to Implement

1. **Known Valid Compositions**
   - LiFePO4, BaTiO3, NaCl
   - Should be accepted by both SMACT and agent

2. **Known Invalid Compositions**  
   - CaF3, Li3O2
   - Should be rejected unless override justified

3. **Edge Cases for Override Testing**
   - TiNi (intermetallic)
   - YBa2Cu3O7 (superconductor)
   - Should trigger intelligent override

4. **Application-Driven Design**
   - "Na-ion battery cathode" → layered oxides
   - "Lead-free ferroelectric" → perovskite alternatives
   - "Thermoelectric" → complex structures

### Integration Testing
```python
async def test_full_workflow():
    """Test complete agent-MCP workflow."""
    
    query = "Design a stable cathode material for a Na-ion battery"
    
    # Run agent
    response = await crystalyse_agent.run(
        messages=[{"role": "user", "content": query}],
        context={"mcp_client": mcp_client}
    )
    
    # Verify response structure
    assert "top_candidates" in response
    assert len(response["top_candidates"]) == 5
    
    # Check each candidate has required fields
    for candidate in response["top_candidates"]:
        assert "formula" in candidate
        assert "validation" in candidate
        assert "proposed_structures" in candidate
```

## Phase 5: Future Enhancements

### Chemeleon Integration (Phase 6)
- 3D structure generation from compositions
- CIF file output for experimental planning
- Structure optimization and stability prediction

### ML Property Prediction (Phase 7)
- Band gap estimation
- Formation energy prediction
- Thermal stability assessment

### Synthesis Planning (Phase 8)
- Experimental pathway suggestions
- Precursor selection
- Reaction condition optimization

### Feedback Loop (Phase 9)
- Incorporate experimental results
- Update knowledge base
- Improve override decision logic

---

## Implementation Priority Order

1. **Immediate (Next Session)**:
   - Set up agent directory structure
   - Implement basic MCP client wrapper
   - Create minimal working agent with one tool

2. **Short Term (1-2 days)**:
   - Implement all core tools
   - Add materials knowledge base
   - Test with known compositions

3. **Medium Term (1 week)**:
   - Advanced structure prediction
   - Override logic refinement
   - Comprehensive testing suite

4. **Long Term (1 month)**:
   - Chemeleon integration
   - ML property models
   - Production deployment

## Notes for Implementation

- **Start Simple**: Begin with minimal agent, add complexity gradually
- **Test Early**: Validate each component before moving to next
- **Document Decisions**: Record all chemical reasoning and override logic
- **Performance Monitor**: Track response times and accuracy
- **User Feedback**: Collect evaluation from materials scientists

The MCP server foundation is solid - now we build the intelligent agent that leverages it creatively!