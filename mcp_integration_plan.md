# CrystaLyse MCP Integration Plan

## Essential SMACT Tools to Expose (Based on Analysis)

### Core Validation & Screening (Highest Priority)
1. **`check_smact_validity`** - Primary composition validation using SMACT rules
   - Wraps `smact_validity()` from `smact.screening`
   - Critical for validating material compositions
   - Includes Pauling test and metallicity checking

2. **`calculate_neutral_ratios`** - Stoichiometry calculation
   - Wraps `neutral_ratios()` from `smact.__init__`
   - Essential for generating charge-neutral compositions
   - Core to composition generation workflow

3. **`parse_chemical_formula`** - Formula parsing
   - Wraps `parse_formula()` from `smact.utils.composition`
   - Fundamental utility used throughout
   - Needed for processing user input

### Element Data & Properties (Medium Priority)
4. **`get_element_info`** - Element property lookup
   - Wraps `Element` class functionality
   - Provides oxidation states, electronegativity, radii
   - Essential for chemical reasoning

5. **`test_pauling_rule`** - Electronegativity validation
   - Wraps `pauling_test()` from `smact.screening`
   - Key chemical heuristic for screening
   - Important for validation justification

## Integration Strategy

### Phase 1: Fix MCP Server Connection
- Move server into main project ✅
- Fix MCPServerStdio initialization and connection
- Implement proper async context manager pattern
- Test basic tool listing and calling

### Phase 2: Optimize Server Performance
Based on SMACT analysis bottlenecks:
- Cache Element objects to avoid repeated creation
- Optimize combinatorial generation in neutral_ratios
- Add early termination for large searches
- Implement proper error handling

### Phase 3: Replace Simulated Tools
- Update CrystaLyse tools to call MCP server
- Remove hardcoded validation logic
- Integrate real SMACT screening results
- Add proper result interpretation

### Phase 4: Advanced Integration
- Add property prediction tools if needed
- Integrate structure prediction capabilities
- Connect to materials databases
- Add synthesis route suggestions

## Connection Pattern (Following OpenAI Agents Examples)

```python
async with MCPServerStdio(
    name="SMACT Tools",
    params={
        "command": "python",
        "args": ["-m", "smact_mcp.server"],
        "cwd": str(smact_server_path)
    }
) as server:
    agent = Agent(
        name="CrystaLyse",
        mcp_servers=[server],
        tools=[custom_tools...]
    )
    
    result = await Runner.run(starting_agent=agent, input=query)
```

## Performance Optimizations for MCP Server

### Critical Fixes Based on SMACT Analysis:
1. **Element Caching**: Implement singleton pattern for Element objects
2. **Generator Usage**: Replace `itertools.product()` with lazy generators
3. **Early Termination**: Short-circuit when valid combinations found
4. **Result Caching**: Cache expensive calculations
5. **Reduced I/O**: Pre-load essential data at server startup

### Tool-Specific Optimizations:
- `check_smact_validity`: Cache validation results for repeated compositions
- `calculate_neutral_ratios`: Limit combinatorial explosion with early exit
- `parse_chemical_formula`: Cache parsed formulas
- `get_element_info`: Pre-load all element data at startup
- `test_pauling_rule`: Vectorize electronegativity calculations

## Expected Integration Benefits

### Real SMACT Capabilities:
- ✅ Actual charge neutrality validation
- ✅ Real electronegativity testing  
- ✅ Proper oxidation state handling
- ✅ Metallicity classification
- ✅ Element property lookups
- ✅ Formula parsing and validation

### Performance Improvements:
- Eliminate combinatorial bottlenecks
- Cache frequently accessed data
- Use generators for large searches
- Early termination for efficiency

### Enhanced Chemical Intelligence:
- Real chemical rules vs. heuristics
- Proper handling of edge cases
- Scientific justification for decisions
- Integration with materials databases