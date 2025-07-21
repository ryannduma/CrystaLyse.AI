# Quickstart

Get up and running with CrystaLyse.AI in minutes. This guide covers installation, configuration, and your first materials analysis.

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- 8GB RAM recommended (4GB minimum)
- Internet connection for model downloads

### Quick Install

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ryannduma/CrystaLyse.AI.git
   cd CrystaLyse.AI
   ```

2. **Create environment:**
   ```bash
   conda create -n crystalyse python=3.11
   conda activate crystalyse
   ```

3. **Install CrystaLyse.AI:**
   ```bash
   # Install core package
   pip install -e .
   
   # Install individual tool servers (required dependencies)
   pip install -e ./oldmcpservers/smact-mcp-server
   pip install -e ./oldmcpservers/chemeleon-mcp-server
   pip install -e ./oldmcpservers/mace-mcp-server
   
   # Install unified MCP servers
   pip install -e ./chemistry-unified-server
   pip install -e ./chemistry-creative-server
   pip install -e ./visualization-mcp-server
   ```

4. **Verify installation:**
   ```bash
   crystalyse --help
   ```

## Configuration

### Set OpenAI API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Verify Configuration

Check that all components are working:
```bash
crystalyse config show
```

This should display your configuration including available MCP servers.

## First Materials Analysis

### Quick Analysis

Analyse a perovskite material for solar cells:

```bash
crystalyse analyse "Find a perovskite material for solar cells" --mode creative
```

Expected output:
```
╭──────────────────────────────────────────────────────────────────────────────╮
│                 CrystaLyse.AI - Materials Discovery Platform                 │
│                 v1.0.0 - AI-Powered Materials Discovery                      │
╰──────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────────╮
│ ✅ Analysis Complete          │
│ Completed in 50.3s            │
╰───────────────────────────────╯

╭─────────────────────── Discovery Results ────────────────────────────╮
│ Generated 5 perovskite candidates with formation energies:            │
│                                                                        │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)           │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                         │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                         │
│ ...                                                                    │
│                                                                        │
│ 3D visualisations saved: CsGeI3_3dmol.html, CsPbI3_3dmol.html        │
╰────────────────────────────────────────────────────────────────────────╯
```

### Interactive Session

Start a conversation-based session:

```bash
crystalyse chat -u researcher -s solar_project -m creative
```

In the session:
```
🔬 You: Find lead-free perovskites for photovoltaics
🤖 CrystaLyse: I'll explore lead-free perovskite alternatives...

🔬 You: What about tin-based alternatives?
🤖 CrystaLyse: Excellent question! Based on the previous analysis...
```

Session commands:
- `/mode rigorous` - Switch to rigorous validation mode
- `/agent analyse` - Switch to one-shot analysis mode
- `/help` - Show available commands
- `/exit` - End session

## Analysis Modes

### Creative Mode (Fast Exploration)

```bash
crystalyse analyse "Design high-capacity battery materials" --mode creative
```

- **Tools Used**: Chemeleon + MACE
- **Speed**: ~50 seconds
- **Output**: Structure generation + energy calculation + 3D visualisation

### Rigorous Mode (Complete Validation)

```bash
crystalyse analyse "Find stable electrolyte materials" --mode rigorous
```

- **Tools Used**: SMACT + Chemeleon + MACE + Analysis Suite
- **Speed**: 2-5 minutes  
- **Output**: Composition validation + structures + energies + comprehensive analysis plots

## Command Reference

### Basic Commands

```bash
# One-shot analysis
crystalyse analyse "your query" --mode [creative|rigorous]

# Interactive chat
crystalyse chat -u username -s session_name -m [creative|rigorous]

# Resume previous session
crystalyse resume session_name -u username

# List all sessions
crystalyse sessions -u username

# Run demonstration
crystalyse demo

# Show examples
crystalyse examples
```

### Unified Interface

Launch the unified interface for mode switching:
```bash
crystalyse
```

Available in-session commands:
- `/mode creative` or `/mode rigorous` - Switch analysis modes
- `/agent chat` or `/agent analyse` - Switch agent types
- `/help` - Show help
- `/clear` - Clear screen
- `/exit` - Exit

## Understanding Output

### Creative Mode Output
- **3D Visualisations**: Interactive HTML files with molecular structures
- **Energy Rankings**: Formation energies per atom for stability comparison
- **Quick Results**: Streamlined output focused on structure and stability

### Rigorous Mode Output
- **Comprehensive Analysis**: XRD patterns, RDF plots, coordination analysis
- **Validation Reports**: SMACT composition screening results
- **Professional Plots**: Publication-ready PDF analysis files
- **Complete Pipeline**: Full traceability from composition to properties

## Working with Results

### Visualisation Files

CrystaLyse.AI automatically creates visualisation files in your current directory:

```bash
# 3D structure viewers
CsGeI3_3dmol.html          # Interactive 3D structure
CsPbI3_3dmol.html

# Analysis plots (rigorous mode)
CsGeI3_analysis/
├── CsGeI3.cif                      # Structure file
├── XRD_Pattern_CsGeI3.pdf          # X-ray diffraction
├── RDF_Analysis_CsGeI3.pdf         # Radial distribution
└── Coordination_Analysis_CsGeI3.pdf # Coordination environment
```

### Session Management

```bash
# List your sessions
crystalyse sessions -u researcher

# Resume previous work
crystalyse resume solar_project -u researcher

# Continue multi-day projects with full context
```

## Example Workflows

### Battery Material Design

```bash
# Start a battery research session
crystalyse chat -u battery_researcher -s lithium_study -m rigorous

# In session:
🔬 You: Analyse LiCoO2 cathode material properties
🔬 You: What happens during delithiation to CoO2?
🔬 You: Calculate volume changes and energy density
🔬 You: Compare with experimental values from Materials Project

# Results persist across sessions
```

### Solar Cell Materials

```bash
# Quick perovskite screening
crystalyse analyse "Screen perovskites with band gaps 1.2-1.6 eV" --mode creative

# Detailed analysis of promising candidates
crystalyse analyse "Analyse CsSnI3 for photovoltaic applications" --mode rigorous
```

## Troubleshooting

### Common Issues

1. **MCP Server Connection Errors**
   ```bash
   # Check server status
   crystalyse config show
   
   # Look for "available" status for each tool
   ```

2. **API Key Issues**
   ```bash
   # Verify key is set
   echo $OPENAI_API_KEY
   
   # Check for valid key format (starts with sk-)
   ```

3. **Memory Errors**
   - Reduce `num_samples` in structure generation
   - Use creative mode for faster analysis
   - Ensure 8GB+ RAM available

4. **GPU Issues**
   ```bash
   # MACE will automatically fall back to CPU
   # Check GPU availability in logs
   ```

### Getting Help

- **Documentation**: Browse the complete [CLI Guide](guides/cli_usage.md)
- **Tool Issues**: Check individual tool documentation under [Tools](tools/)
- **Verbose Output**: Add `--verbose` to any command for detailed logging
- **Demo Mode**: Run `crystalyse demo` to test the complete pipeline

## Next Steps

Now that you have CrystaLyse.AI running:

1. **Learn the Tools**: Explore [SMACT](tools/smact.md), [Chemeleon](tools/chemeleon.md), and [MACE](tools/mace.md) capabilities
2. **Understand Modes**: Read about [Analysis Modes](concepts/analysis_modes.md) and when to use each
3. **Advanced Features**: Check out [Session Management](concepts/sessions.md) for persistent research
4. **Integration**: See the [API Reference](reference/) for programmatic usage

Ready to start designing materials? Try the [CLI Usage Guide](guides/cli_usage.md) for comprehensive examples.