# Quick Start Guide

## Installation

### Prerequisites
- Python 3.11+
- Conda environment manager (recommended)
- OpenAI API key

### From PyPI (Stable)
```bash
pip install crystalyse
export OPENAI_MDG_API_KEY="your-api-key-here"
crystalyse --help
```

### From Source (Development)
```bash
# Clone repository
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI/dev

# Create and activate environment
conda create -n crystalyse python=3.11
conda activate crystalyse

# Install core package first
pip install -e .

# Install MCP servers
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server

# Configure
export OPENAI_MDG_API_KEY="your-api-key-here"
```

## First Run

On first execution, Crystalyse automatically downloads:
- Chemeleon model checkpoints (~600 MB)
- Materials Project phase diagrams (~170 MB, 271,617 entries)

Files are cached in `~/.cache/crystalyse/` and never downloaded again.

## Basic Usage

### Non-Interactive Discovery
```bash
# Creative mode (fast exploration, ~50s)
crystalyse analyse "Find lead-free perovskite for solar cells" --mode creative

# Rigorous mode (complete validation, 2-5min)
crystalyse analyse "Explore battery cathode materials" --mode rigorous
```

### Interactive Session
```bash
# Start research session
crystalyse chat -u researcher -s project_name

# In session:
> Find stable oxide perovskites
> What's the formation energy of the most promising candidate?
> Generate crystal structure visualisation
> /history
> /exit
```

### Session Management
```bash
# View learning progress
crystalyse user-stats -u researcher

# List sessions
crystalyse sessions -u researcher

# Resume session
crystalyse resume project_name -u researcher
```

## Analysis Modes

### Creative Mode
- **Duration**: ~50s per query
- **Tools**: Chemeleon + MACE + basic visualisation
- **Use case**: Rapid screening, initial exploration
- **Structures**: ~3 candidates per composition

```bash
crystalyse analyse "Find perovskites" --mode creative
```

### Rigorous Mode
- **Duration**: 2-5min per query
- **Tools**: SMACT + Chemeleon + MACE + analysis + visualisation
- **Use case**: Publication-quality results, detailed analysis
- **Structures**: 30+ candidates per composition

```bash
crystalyse analyse "Analyse CsSnI3" --mode rigorous
```

### Adaptive Mode (Default)
- **Behaviour**: Automatic balancing of speed and accuracy
- **Logic**: Context-aware tool selection and clarification
- **Use case**: General research, mixed workflows

```bash
crystalyse analyse "Battery materials"  # Adaptive by default
```

## Example Workflows

### Battery Materials Research
```bash
crystalyse chat -u researcher -s battery_cathodes

# Example queries:
> Find high-capacity cathode materials for Li-ion batteries
> Compare formation energies of LiCoO2 variants
> What happens if we substitute Ni for Co?
> Generate XRD patterns for the most stable structure
```

### Solar Cell Materials
```bash
crystalyse chat -u researcher -s solar_materials -m creative

# Example queries:
> Find lead-free perovskites with optimal band gaps
> Screen for materials stable at 150°C
> Visualise crystal structure and electronic properties
> What synthesis routes would work?
```

### Catalyst Discovery
```bash
crystalyse chat -u researcher -s catalysts -m adaptive

# Example queries:
> Find oxide catalysts for CO2 reduction
> Focus on earth-abundant elements only
> Calculate surface energies for the (100) facet
```

## Understanding Results

### Computational Honesty
All numerical results trace to actual tool computations:
- Valid: "MACE calculated formation energy: -2.45 eV"
- Valid: "SMACT validation confirms charge balance"
- Invalid: "Formation energy is approximately -2.5 eV" (no tool basis)

### Result Components
1. **Composition Validation** - SMACT screening for chemical plausibility
2. **Structure Prediction** - Chemeleon-generated crystal structures
3. **Energy Calculations** - MACE formation energy with uncertainty
4. **Stability Analysis** - PyMatGen energy above hull calculations
5. **Visualisation** - 3D structures, XRD patterns, RDF analysis

### Interpreting Outputs
- **Formation Energy**: More negative = more stable
- **Energy Above Hull**: <25 meV/atom likely synthesisable, 25-200 meV/atom metastable
- **Confidence Scores**: Chemeleon structure prediction confidence
- **Provenance**: Every value traces to specific tool invocation

## Tips for Success

### Query Practices
1. Be specific about constraints (temperature, composition, properties)
2. Let adaptive clarification refine ambiguous requests
3. Use creative mode for exploration, rigorous for validation
4. Specify units when asking for numerical properties

### Session Management
1. Use descriptive session names for organisation
2. User profiles track expertise and preferences
3. Cross-session context informs new research
4. Resume sessions for long-term projects

### Troubleshooting
- **Tool failures**: System reports errors clearly, suggests alternatives
- **Slow performance**: Creative mode faster, check network for downloads
- **Clarification loops**: Provide more specific initial queries
- **Missing checkpoints**: Allow first-run auto-download to complete

## Advanced Usage

### Custom Data Paths
```bash
# Custom checkpoint directory
export CHEMELEON_CHECKPOINT_DIR=/path/to/checkpoints

# Custom phase diagram data
export CRYSTALYSE_PPD_PATH=/path/to/ppd.pkl.gz
```

### Mode Switching
```bash
# In interactive session:
/mode creative    # Switch to creative mode
/mode rigorous    # Switch to rigorous mode
/mode adaptive    # Switch to adaptive mode
```

### Programmatic API
```python
from crystalyse.agents import EnhancedCrystaLyseAgent
from crystalyse.config import CrystaLyseConfig

config = CrystaLyseConfig()
agent = EnhancedCrystaLyseAgent(config=config, mode="rigorous")

result = agent.query(
    "Analyse CsSnI3 perovskite for photovoltaic applications",
    user_id="researcher"
)

print(result.response)
```

## Performance Expectations

### Computational Time
- Simple query (creative): ~50s
- Simple query (rigorous): 2-3min
- Complex analysis (creative): 1-2min
- Complex analysis (rigorous): 3-5min
- Batch processing (10 materials, creative): 5-10min
- Batch processing (10 materials, rigorous): 15-30min

### Resource Requirements
- Python: 3.11+
- RAM: 8GB minimum, 16GB recommended
- Storage: ~2GB (installation + cache)
- Network: Required for first-run downloads
- GPU: Optional (accelerates MACE calculations)

## Next Steps

- **[CLI Usage Guide](cli_usage.md)** - Comprehensive command reference
- **[Analysis Modes](../concepts/analysis_modes.md)** - Mode selection strategies
- **[Provenance System](../concepts/provenance_system.md)** - Computational honesty architecture
- **[Tool Documentation](../tools/)** - SMACT, Chemeleon, MACE, PyMatGen details

---

**Version**: 1.0.0-dev
**PyPI Stable**: 1.0.1
