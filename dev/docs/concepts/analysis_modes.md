# Analysis Modes - CrystaLyse.AI v1.0.0

CrystaLyse.AI v1.0.0 provides three intelligent analysis modes powered by multi-agent orchestration and enhanced UX, allowing you to balance speed, accuracy, and user experience based on your research needs.

## Overview

| Mode | Speed | Tools Used | Use Case | v1.0.0 Features |
|------|-------|------------|----------|---------------------|
| **Adaptive** (Default) | Variable | Context-aware selection | General research, learning preferences | Enhanced clarification, workspace management |
| **Creative** | ~50 seconds | Chemeleon + MACE + Basic Viz | Fast exploration, initial screening | Multi-agent coordination, transparent operations |
| **Rigorous** | 2-5 minutes | SMACT + Chemeleon + MACE + Advanced Viz + Analysis | Complete validation, publication-ready | Specialized agent validation, anti-hallucination |

## Adaptive Mode (Default) - NEW in v1.0.0

### Purpose
Intelligent balance of speed and accuracy with enhanced user experience. Features:
- **Enhanced Clarification**: LLM-powered adaptive questioning based on expertise level
- **Context-Aware Tool Selection**: Automatically chooses optimal tools for each query
- **Learning Preferences**: Adapts behavior based on user patterns and feedback
- **Workspace Management**: Transparent file operations with preview/approval
- **Intelligent Tool Coordination**: Single agent manages specialized tools seamlessly

### Enhanced Agent Capabilities
Adaptive mode leverages the full feature set of EnhancedCrystaLyseAgent:
- **Intelligent Tool Selection**: Automatically chooses optimal MCP servers and tools
- **Context-Aware Processing**: Adapts responses based on query complexity and user expertise
- **Workspace Coordination**: Manages file operations with transparent preview/approval
- **Memory Integration**: Utilizes session history and discovery cache for informed decisions
- **Anti-Hallucination Validation**: Ensures all numerical results have computational basis

### Enhanced UX Features
```bash
# Adaptive clarification examples:
User: "Find battery materials"
System: "What type of battery application? (Li-ion cathode, Na-ion anode, solid electrolyte, etc.)"

User: "Perovskites for solar cells"  
System: "For single-junction or tandem cells? Any specific efficiency targets?"
```

## Creative Mode

### Purpose
Fast materials exploration with multi-agent coordination. Enhanced in v1.0.0 for:
- Initial concept exploration with transparent operations
- Rapid prototyping with workspace management
- Interactive sessions with real-time progress visualization
- Educational demonstrations with adaptive explanations

### MCP Server Mapping
Creative mode uses the **Chemistry Creative Server** (`chemistry-creative-server`):

```python
# Tools available in creative mode
- Chemeleon CSP: Crystal structure prediction
- MACE: Formation energy calculations  
- Visualisation: 3D structure rendering
# Not included: SMACT validation (for speed)
```

### Workflow
1. **Input**: Natural language materials query
2. **Structure Generation**: Chemeleon generates multiple candidate structures
3. **Energy Evaluation**: MACE calculates formation energies for ranking
4. **Visualisation**: Automatic 3D structure files created
5. **Output**: Ranked structures with energies and interactive visualisations

### Example Usage

```bash
# Command line
crystalyse analyse "Find perovskite solar cell materials" --mode creative

# In unified interface
crystalyse
> /mode creative
> Design high-capacity battery cathodes

# In chat session
crystalyse chat -m creative
```

### Output Structure
```
Creative Mode Results:
├── Structure Generation: 3-5 candidates per composition
├── Energy Ranking: Formation energies (eV/atom)
├── 3D Visualisations: Interactive HTML files
└── Summary: Most stable structures identified
```

## Rigorous Mode

### Purpose
Complete materials validation with specialized agent validation. Enhanced in v1.0.0 for:
- Publication-quality research with anti-hallucination safeguards
- Detailed materials characterisation with multi-agent cross-validation
- Validation of creative/adaptive mode results with specialized agents
- Professional materials design projects with comprehensive documentation

### MCP Server Mapping
Rigorous mode uses the **Chemistry Unified Server** (`chemistry-unified-server`):

```python
# Complete tool suite in rigorous mode
- SMACT: Composition validation and screening
- Chemeleon CSP: Crystal structure prediction
- MACE: Formation energy calculations
- Visualisation: 3D structures + analysis plots
- Pymatviz: XRD patterns, RDF analysis, coordination analysis
```

### Workflow
1. **Input**: Natural language materials query
2. **Composition Validation**: SMACT screens for chemically reasonable compositions
3. **Structure Generation**: Chemeleon generates structures for valid compositions
4. **Energy Evaluation**: MACE calculates detailed energetics
5. **Comprehensive Analysis**: XRD patterns, radial distribution functions, coordination analysis
6. **Visualisation**: 3D structures + professional analysis plots
7. **Output**: Complete materials characterisation package

### Example Usage

```bash
# Command line
crystalyse analyse "Validate CsSnI3 for photovoltaic applications" --mode rigorous

# In unified interface
crystalyse
> /mode rigorous
> Analyse LiCoO2 cathode stability

# In chat session
crystalyse chat -m rigorous -s detailed_study
```

### Output Structure
```
Rigorous Mode Results:
├── SMACT Validation: Composition feasibility screening
├── Structure Generation: Multiple candidates with validation
├── Energy Analysis: Formation energies + stability metrics
├── 3D Visualisations: Interactive molecular viewers
├── Analysis Suite:
│   ├── XRD_Pattern_[formula].pdf
│   ├── RDF_Analysis_[formula].pdf
│   ├── Coordination_Analysis_[formula].pdf
│   └── [formula].cif
└── Comprehensive Report: Complete materials characterisation
```

## Mode Switching

### In Unified Interface

```bash
crystalyse  # Launch unified interface

# Switch modes during session
> /mode creative    # Fast exploration
> /mode rigorous    # Complete validation
```

### In Chat Sessions

```bash
crystalyse chat -u researcher -s project_name

# Switch modes within session
🔬 You: /mode rigorous
✅ System: Mode switched to Rigorous
🔬 You: Now analyse the stability in detail
```

### Command Line

```bash
# Specify mode per analysis
crystalyse analyse "query" --mode creative
crystalyse analyse "query" --mode rigorous
```

## Choosing the Right Mode

### Use Adaptive Mode When: (Recommended Default)
- **General research**: Most research scenarios benefit from intelligent tool selection
- **Learning systems**: System adapts to your expertise level and preferences  
- **Mixed workflows**: Combining exploration with validation in one session
- **First-time users**: Enhanced clarification helps guide effective queries
- **Project organization**: Workspace management keeps research organized

### Use Creative Mode When:
- **Rapid exploration**: Need many quick results for initial screening
- **Time-sensitive**: Presentations or decision-making with tight deadlines
- **Brainstorming**: Generating ideas and concepts rapidly
- **Educational demos**: Quick visual feedback for teaching
- **Iterative design**: Fast cycles of concept → evaluation → refinement

### Use Rigorous Mode When:
- **Research publications**: Need comprehensive validation with cross-checking
- **Professional projects**: Client work requiring complete documentation
- **Critical validation**: High-stakes decisions requiring maximum confidence
- **Regulatory submissions**: Complete traceability and anti-hallucination safeguards
- **Deep analysis**: Understanding complex materials properties in detail

## Performance Characteristics

### Creative Mode Performance
```bash
Typical Execution Times:
├── Simple queries: 30-50 seconds
├── Complex materials: 1-2 minutes
├── Multiple compositions: 2-3 minutes
└── Batch analysis: 5-10 minutes

Resource Usage:
├── CPU: Moderate (structure prediction)
├── GPU: Optional (MACE calculations)
├── Memory: 4-6 GB
└── Storage: ~50 MB per analysis
```

### Rigorous Mode Performance
```bash
Typical Execution Times:
├── Simple queries: 2-3 minutes
├── Complex materials: 3-5 minutes
├── Detailed analysis: 5-10 minutes
└── Batch analysis: 15-30 minutes

Resource Usage:
├── CPU: High (full analysis suite)
├── GPU: Recommended (MACE + visualisation)
├── Memory: 6-8 GB
└── Storage: ~200 MB per analysis
```

## Technical Implementation

### MCP Server Architecture

```mermaid
graph TB
    A[CrystaLyse Agent] --> B{Mode Selection}
    B -->|Creative| C[Chemistry Creative Server]
    B -->|Rigorous| D[Chemistry Unified Server]
    
    C --> E[Chemeleon CSP]
    C --> F[MACE Energy]
    C --> G[Basic Visualisation]
    
    D --> H[SMACT Validation]
    D --> I[Chemeleon CSP]
    D --> J[MACE Energy]
    D --> K[Comprehensive Visualisation]
    D --> L[Analysis Suite]
```

### Tool Availability by Mode

| Tool | Creative Mode | Rigorous Mode | Purpose |
|------|---------------|---------------|---------|
| SMACT | ❌ | ✅ | Composition validation |
| Chemeleon | ✅ | ✅ | Structure prediction |
| MACE | ✅ | ✅ | Energy calculations |
| 3D Visualisation | ✅ | ✅ | Interactive structures |
| XRD Analysis | ❌ | ✅ | Diffraction patterns |
| RDF Analysis | ❌ | ✅ | Structural analysis |
| Coordination Analysis | ❌ | ✅ | Local environment |

## Best Practices

### Mode Selection Strategy

1. **Start with Creative**: Use for initial exploration and idea generation
2. **Validate with Rigorous**: Confirm promising results with complete analysis
3. **Iterate**: Use creative mode for rapid iteration, rigorous for final validation
4. **Match Context**: Consider time constraints, audience, and required detail level

### Workflow Recommendations

```bash
# Recommended research workflow
1. Initial Exploration (Creative)
   crystalyse analyse "broad query" --mode creative

2. Focused Investigation (Creative)
   crystalyse chat -m creative
   > Refine based on initial results

3. Detailed Validation (Rigorous)
   crystalyse analyse "specific material" --mode rigorous

4. Final Analysis (Rigorous)
   crystalyse chat -m rigorous -s final_study
   > Complete characterisation
```

### Performance Optimisation

- **Creative Mode**: Reduce `num_samples` for faster iteration
- **Rigorous Mode**: Use GPU acceleration for MACE calculations
- **Both Modes**: Enable result caching to avoid redundant calculations
- **Batch Processing**: Group similar queries for efficiency

## Examples

### Creative Mode Example

```bash
crystalyse analyse "Design sodium-ion battery cathodes" --mode creative
```

Output focus:
- Quick structure generation (3-5 candidates)
- Energy ranking for stability
- 3D visualisations for immediate insight
- Recommendations for further investigation

### Rigorous Mode Example

```bash
crystalyse analyse "Characterise Na2FePO4F cathode material" --mode rigorous
```

Output focus:
- SMACT validation of composition
- Multiple structure polymorphs
- Detailed energetic analysis
- Complete structural characterisation
- Professional analysis plots
- Publication-ready results

The choice between creative and rigorous modes allows CrystaLyse.AI to adapt to your specific research needs, from rapid exploration to comprehensive validation.