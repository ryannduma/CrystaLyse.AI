# Quick Start Guide - CrystaLyse.AI v2.0-alpha

## Installation

### Prerequisites
- Python 3.11+ (required for v2.0-alpha)
- Conda environment manager
- OpenAI API key

### Setup
```bash
# Clone repository
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI

# Create and activate environment
conda create -n crystalyse python=3.11
conda activate crystalyse

# Navigate to dev directory (where pyproject.toml is located)
cd dev

# Step 1: Install core package in development mode FIRST
pip install -e .

# Step 2: Install MCP servers (they depend on core package)
pip install -e ./chemistry-unified-server      # Complete validation mode
pip install -e ./chemistry-creative-server     # Fast exploration mode
pip install -e ./visualization-mcp-server      # 3D visualization

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

## First Steps

### 1. Quick Discovery
```bash
# Simple one-shot discovery
crystalyse discover "Find a lead-free perovskite for solar cells" --mode creative

# Rigorous analysis
crystalyse discover "Explore battery cathode materials" --mode rigorous
```

### 2. Interactive Session
```bash
# Start a research session with enhanced clarification system
crystalyse chat -u researcher1 -s my_project -m adaptive

# In the session:
> Find stable oxide perovskites
> What's the formation energy of the most promising candidate?
> Generate 3D visualisation of the crystal structure
> /history  # View conversation
> /exit     # Save and exit
```

### 3. User Stats & Session Management
```bash
# View your learning progress and preferences
crystalyse user-stats -u researcher1

# List your sessions
crystalyse sessions -u researcher1

# Resume a specific session
crystalyse resume my_project -u researcher1
```

## Discovery Modes

### Creative Mode (Fast Exploration)
- **Speed**: ~50 seconds per query
- **Tools**: Chemeleon + MACE + Basic Visualization
- **Use case**: Rapid screening, initial exploration

```bash
crystalyse discover "Find perovskites" --mode creative
crystalyse chat --mode creative
```

### Rigorous Mode (Complete Validation)  
- **Speed**: 2-5 minutes per query
- **Tools**: SMACT + Chemeleon + MACE + Analysis Suite + Advanced Visualization
- **Use case**: Publication-quality results, detailed analysis

```bash
crystalyse discover "Analyze CsSnI3" --mode rigorous
crystalyse chat --mode rigorous
```

### Adaptive Mode (Intelligent Selection) - DEFAULT
- **Behaviour**: Automatically balances speed and accuracy
- **Logic**: Context-aware tool selection and clarification
- **Use case**: General research, mixed workflows, enhanced UX

```bash
crystalyse discover "Battery materials"  # Uses adaptive by default
crystalyse chat  # Default mode
```

## Example Workflows

### Battery Materials Research
```bash
# Start battery-focused session with adaptive mode
crystalyse chat -u researcher1 -s battery_cathodes -m adaptive

# Example queries with enhanced clarification:
> Find high-capacity cathode materials for Li-ion batteries
# System may ask: "What voltage range are you targeting?" or "Any specific capacity requirements?"
> Compare formation energies of LiCoO2 variants
> What happens if we substitute Ni for Co?
> Generate XRD patterns and coordination analysis for the most stable structures
> Save the top 3 candidates to my research workspace
```

### Solar Cell Materials
```bash  
# Start photovoltaic session with creative mode
crystalyse chat -u researcher1 -s solar_materials -m creative

# Example queries with workspace management:
> Find lead-free perovskites with optimal band gaps
# System may clarify: "For single-junction or tandem cells?" and save preferences
> Screen for materials stable at 150°C  
> Visualise the crystal structure and electronic properties of the most promising candidate
> What synthesis routes would work for these materials?
```

### Catalyst Discovery
```bash
# Start catalysis session with enhanced tool coordination
crystalyse chat -u researcher1 -s catalysts -m adaptive

# Example queries demonstrating intelligent tool coordination:
> Find oxide catalysts for CO2 reduction
# EnhancedCrystaLyseAgent coordinates chemistry tools for comprehensive analysis
> Focus on earth-abundant elements only
> What about defect sites in these structures?
> Calculate surface energies for the (100) facet
```

## Understanding Results

### Computational Honesty with Anti-Hallucination
All numerical results trace to actual tool computations with validation:
- ✅ "MACE calculated formation energy: -2.45 ± 0.03 eV (confidence: high)" 
- ✅ "Enhanced tool validation: SMACT + Chemeleon + MACE confirm stability"
- ❌ "Formation energy is approximately -2.5 eV" (no computational basis)

### v2.0-alpha Result Components
1. **Enhanced Tool Validation**: Intelligent coordination and cross-validation of chemistry tools
2. **Enhanced Clarification**: Context-aware questions based on expertise level
3. **Workspace Integration**: Transparent file operations with preview/approval
4. **Structure Prediction**: Chemeleon-generated crystal structures with multiple candidates
5. **Energetics**: MACE formation energy calculations with uncertainty quantification
6. **Comprehensive Analysis**: XRD patterns, RDF analysis, coordination studies
7. **Advanced Visualization**: Interactive 3D molecular views and professional plots

### Interpreting v2.0-alpha Outputs
- **Formation Energy**: More negative = more stable (with uncertainty bounds)
- **Tool Coordination**: Single enhanced agent validates findings through multiple chemistry tools
- **Adaptive Recommendations**: System learns your preferences and adjusts suggestions
- **Workspace State**: Clear tracking of generated files and analysis results
- **Cross-Session Learning**: System builds understanding across research sessions

## Tips for Success with v2.0-alpha

### Enhanced Query Practices
1. **Leverage Clarification**: Let the system ask follow-up questions to refine your request
2. **Use Adaptive Mode**: Default mode balances speed with accuracy and learns your preferences
3. **Workspace Awareness**: Review file previews before approval, organize by project
4. **Enhanced Tool Benefits**: Complex queries automatically coordinate multiple specialized chemistry tools

### Advanced Session Management
1. **User Profiles**: System learns your expertise level and research patterns
2. **Cross-Session Context**: Previous discoveries inform new research directions
3. **Preference Learning**: Adaptive behavior based on your typical workflows
4. **Research Continuity**: Long-term project support with intelligent context management

### v2.0-alpha Troubleshooting
- **Tool Coordination**: If one chemistry tool fails, others continue and provide partial results
- **Clarification Loops**: If system asks too many questions, provide more specific initial queries
- **Workspace Management**: Use file organization features to maintain clean project structure
- **Performance Optimization**: Adaptive mode automatically selects optimal tools for speed vs accuracy