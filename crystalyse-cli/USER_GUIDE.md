# CrystaLyse.AI Python CLI User Guide

Welcome to CrystaLyse.AI! This comprehensive guide will help you master the Python CLI for materials discovery and crystal structure analysis.

## 📚 Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Getting Started](#getting-started)
3. [Interactive Shell](#interactive-shell)
4. [Command Reference](#command-reference)
5. [Analysis Modes](#analysis-modes)
6. [Visualization](#visualization)
7. [Session Management](#session-management)
8. [Advanced Usage](#advanced-usage)
9. [Tips & Best Practices](#tips--best-practices)
10. [Example Workflows](#example-workflows)

## 🛠 Installation & Setup

### Prerequisites
- Python 3.10 or higher
- OpenAI API key with Materials Discovery Gateway access

### Installation
```bash
# Navigate to the CrystaLyse.AI directory
cd /path/to/CrystaLyse.AI

# Install in development mode
pip install -e .

# Install with visualization dependencies (optional)
pip install -e ".[visualization]"
```

### API Key Configuration
```bash
# Set your OpenAI MDG API key
export OPENAI_MDG_API_KEY="your_mdg_api_key_here"

# Alternative: Regular OpenAI API key (lower rate limits)
export OPENAI_API_KEY="your_api_key_here"
```

### Verify Installation
```bash
# Check status
crystalyse status

# Should show ✅ Configured for API connection
```

## 🚀 Getting Started

### Quick Start
```bash
# Start CrystaLyse.AI (launches interactive shell by default)
crystalyse
```

You'll see the welcome banner and prompt:
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           🔬 CrystaLyse.AI Shell 🔬                         ║
║                     Interactive Materials Discovery                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

🔬 crystalyse (rigorous) > 
```

### Your First Query
Try asking for a specific material:
```
🔬 crystalyse (rigorous) > Design a cathode material for sodium-ion batteries
```

CrystaLyse.AI will analyze your request and provide:
- Suggested compositions
- Crystal structures
- Properties and validation
- Detailed analysis
- Recommendations

## 🖥 Interactive Shell

The interactive shell is the primary interface for CrystaLyse.AI, offering a conversational approach to materials discovery.

### Shell Features

#### Command History
- **Up/Down arrows**: Browse previous queries
- **Ctrl+R**: Search command history
- **Auto-save**: History automatically saved between sessions

#### Auto-completion
- **Tab**: Complete commands and common queries
- **Smart suggestions**: Based on your usage patterns

#### Real-time Progress
- **Streaming output**: Watch analysis progress in real-time
- **Progress indicators**: Visual feedback for long operations
- **Interrupt**: Use Ctrl+C to interrupt analysis

### Shell Commands

All shell commands start with `/`:

```bash
/help           # Show detailed help
/mode creative  # Switch to creative mode
/mode rigorous  # Switch to rigorous mode (default)
/view           # View last structure in 3D browser
/export         # Export session to JSON
/export my_results.json  # Export with custom filename
/history        # Show analysis history
/clear          # Clear the screen
/status         # Show system status
/examples       # Show example queries
/exit           # Exit the shell
```

## 📖 Command Reference

### Core Commands

#### `crystalyse` (default)
Starts the interactive shell.
```bash
crystalyse
```

#### `crystalyse shell`
Explicitly starts the interactive shell.
```bash
crystalyse shell
```

#### `crystalyse analyze`
Performs one-time analysis without entering the shell.
```bash
crystalyse analyze "Design a battery cathode material"

# With options
crystalyse analyze "Find lead-free ferroelectrics" \
  --model gpt-4o \
  --temperature 0.3 \
  --stream \
  --output results.json
```

**Options:**
- `--model`: AI model to use (default: gpt-4o)
- `--temperature`: Creativity vs precision (0.0-1.0, default: 0.7)
- `--output, -o`: Save results to JSON file
- `--stream`: Enable real-time streaming output

#### `crystalyse status`
Shows configuration and system status.
```bash
crystalyse status
```

#### `crystalyse examples`
Displays example queries for inspiration.
```bash
crystalyse examples
```

#### `crystalyse server`
Starts SMACT MCP server for testing (development only).
```bash
crystalyse server
```

## 🎯 Analysis Modes

CrystaLyse.AI offers two complementary analysis modes:

### Rigorous Mode (Default)
- **Focus**: Scientific accuracy and validation
- **Speed**: Slower but thorough
- **Use cases**: 
  - Research publications
  - Experimental design
  - Critical applications
  - Detailed property calculations

```bash
# In shell
/mode rigorous
Design a cathode for commercial lithium-ion batteries
```

### Creative Mode
- **Focus**: Novel ideas and exploration
- **Speed**: Faster analysis
- **Use cases**:
  - Brainstorming sessions
  - Novel material concepts
  - Quick feasibility checks
  - Educational purposes

```bash
# In shell
/mode creative
What if we could make transparent metals?
```

### Switching Modes
```bash
# In interactive shell
/mode creative    # Switch to creative mode
/mode rigorous    # Switch to rigorous mode

# Current mode is shown in the prompt:
🎨 crystalyse (creative) >   # Creative mode
🔬 crystalyse (rigorous) >   # Rigorous mode
```

## 🔍 Visualization

### 3D Structure Viewer
When CrystaLyse.AI generates crystal structures, you can visualize them in 3D:

```bash
# After running an analysis that generates a structure
/view
```

This will:
1. Generate an interactive HTML viewer
2. Open it in your default web browser
3. Display the crystal structure with:
   - Rotatable 3D model
   - Atom labels and bonds
   - Unit cell visualization
   - Property information

### Structure Viewer Features
- **Interactive rotation**: Click and drag to rotate
- **Zoom**: Mouse wheel or pinch gestures
- **Atom information**: Click atoms for details
- **Export**: Save structure in various formats

## 💾 Session Management

### Session Features
- **Automatic tracking**: All queries and results are tracked
- **Session ID**: Unique identifier for each session
- **History persistence**: Command history saved between sessions

### Export Session Data
```bash
# Export current session
/export

# Export with custom filename
/export my_battery_research.json
```

### Session Data Structure
Exported JSON contains:
```json
{
  "session_id": "20241216_143052",
  "export_time": "2024-12-16T14:35:22.123456",
  "mode": "rigorous",
  "total_queries": 5,
  "history": [
    {
      "timestamp": "2024-12-16T14:30:52.123456",
      "query": "Design a cathode for sodium-ion batteries",
      "mode": "rigorous",
      "result": {
        "composition": "Na2FePO4F",
        "properties": {...},
        "structure": "...",
        "analysis": "...",
        "confidence": 0.85
      }
    }
  ]
}
```

### View Session History
```bash
# In shell
/history
```

Shows a table with:
- Timestamp of each query
- Analysis mode used
- Query text (truncated)
- Resulting composition

## 🔧 Advanced Usage

### Environment Variables
```bash
# API Configuration
export OPENAI_MDG_API_KEY="your_mdg_key"     # Preferred (high rate limits)
export OPENAI_API_KEY="your_regular_key"     # Alternative (lower limits)

# Model Configuration
export CRYSTALYSE_DEFAULT_MODEL="gpt-4o"     # Override default model
export CRYSTALYSE_TEMPERATURE="0.7"          # Override default temperature

# Debugging
export CRYSTALYSE_DEBUG="true"               # Enable debug logging
export CRYSTALYSE_VERBOSE="true"             # Verbose output
```

### Batch Processing
For processing multiple queries:

```bash
# Create a file with queries
echo "Design a battery cathode" > queries.txt
echo "Find superconducting materials" >> queries.txt
echo "Suggest photovoltaic semiconductors" >> queries.txt

# Process each query
while read query; do
  crystalyse analyze "$query" --output "result_$(date +%s).json"
done < queries.txt
```

### Integration with Other Tools
```bash
# Pipe results to analysis tools
crystalyse analyze "Design solar cell materials" --output - | jq '.composition'

# Use with version control
crystalyse analyze "Research query" --output results.json
git add results.json
git commit -m "Analysis results for research query"
```

## 💡 Tips & Best Practices

### Query Formulation

#### ✅ Good Queries
- **Specific application**: "Design a cathode for sodium-ion batteries"
- **Clear constraints**: "Find lead-free ferroelectric materials"
- **Property targets**: "Suggest semiconductors with bandgap around 1.5 eV"
- **Synthesis constraints**: "Create materials synthesizable below 800°C"

#### ❌ Avoid These
- **Too vague**: "Find good materials"
- **Contradictory**: "Find materials that are both insulating and conducting"
- **Impossible constraints**: "Create room-temperature superconductors with infinite critical current"

### Performance Optimization

#### For Faster Results
1. Use **creative mode** for exploration
2. Ask **focused questions**
3. Limit **property requirements**
4. Use **streaming mode** for long analyses

#### For Detailed Analysis
1. Use **rigorous mode**
2. Ask for **specific properties**
3. Request **validation details**
4. Include **synthesis considerations**

### Session Organization
```bash
# Use descriptive export filenames
/export battery_cathode_research_2024.json
/export lead_free_ferroelectrics_study.json

# Start new sessions for different projects
# Exit and restart CLI for clean sessions
```

## 📝 Example Workflows

### Workflow 1: Battery Material Design
```bash
# Start CrystaLyse.AI
crystalyse

# Set rigorous mode for accuracy
/mode rigorous

# Explore cathode materials
> Design a high-capacity cathode for lithium-ion batteries with operating voltage above 4V

# Analyze the results, then explore variations
> Can you optimize the previous composition for better thermal stability?

# View the structure
/view

# Export results
/export li_battery_cathode_study.json
```

### Workflow 2: Novel Material Exploration
```bash
# Start in creative mode for exploration
crystalyse

/mode creative

# Brainstorm novel concepts
> What would happen if we combined the piezoelectric properties of quartz with the superconductivity of cuprates?

> Can you design materials that change color under stress?

# Switch to rigorous mode for feasibility
/mode rigorous

> Evaluate the thermodynamic stability of the color-changing material concept

/export novel_materials_exploration.json
```

### Workflow 3: Research Validation
```bash
# One-time analysis with file output
crystalyse analyze "Validate the stability of CsPbI3 perovskite for solar cells" \
  --stream \
  --output perovskite_validation.json

# Review results
cat perovskite_validation.json | jq '.analysis'
```

### Workflow 4: Educational Use
```bash
crystalyse

# Start with examples
/examples

# Try a simple query
> Explain why diamonds are hard but graphite is soft

# Explore structure-property relationships
> How does crystal structure affect electrical conductivity?

# Interactive learning
> Design a material to demonstrate the relationship between structure and properties
```

## 🔍 Advanced Query Examples

### Property-Specific Queries
```bash
# Electrical properties
> Find oxide materials with high ionic conductivity for solid electrolytes

# Mechanical properties
> Design lightweight but strong materials for aerospace applications

# Optical properties
> Suggest transparent conductors for flexible displays

# Magnetic properties
> Find materials with high magnetic anisotropy for data storage
```

### Application-Specific Queries
```bash
# Energy storage
> Design electrode materials for next-generation batteries
> Find electrolyte materials for fuel cells

# Electronics
> Suggest materials for high-frequency electronics
> Design materials for quantum computing applications

# Environmental
> Find photocatalysts for water purification
> Design materials for carbon capture and storage
```

### Constraint-Based Queries
```bash
# Synthesis constraints
> Find materials that can be synthesised using solution processing
> Design materials stable in ambient conditions

# Cost constraints  
> Suggest low-cost alternatives to indium tin oxide
> Find earth-abundant materials for solar cells

# Environmental constraints
> Design non-toxic materials for biomedical applications
> Find recyclable materials for sustainable electronics
```

## 🚨 Troubleshooting

### Common Issues

#### API Key Issues
```bash
# Check status
crystalyse status

# Should show ✅ Configured, not ❌ Missing
```

#### Installation Issues
```bash
# Reinstall dependencies
pip install -e ".[all]"

# Check Python version
python --version  # Should be 3.10+
```

#### Performance Issues
```bash
# Use creative mode for faster responses
/mode creative

# Check internet connection
# Large models require stable connection
```

For more troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

Happy materials discovery! 🔬✨