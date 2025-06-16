# CrystaLyse.AI CLI User Guide

## Table of Contents
1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Interactive Shell](#interactive-shell)
4. [Commands Reference](#commands-reference)
5. [Visualization Features](#visualization-features)
6. [Session Management](#session-management)
7. [Configuration](#configuration)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites
- Node.js 16+ 
- Python 3.8+
- A modern web browser for 3D visualization

### Setup
```bash
# From the main CrystaLyse.AI directory
cd crystalyse-cli

# Install dependencies
npm install

# Build the project
npm run build

# Test installation
node dist/index.js --help

# Or use the Python launcher (recommended)
cd ..
python crystalyse/cli_launcher.py --help
```

## Quick Start

### 1. Basic Usage
```bash
# Show help
crystalyse --help

# Start interactive shell
crystalyse shell

# Analyze a specific query
crystalyse analyze "Design a sodium-ion battery cathode"

# View structure (if you have a CIF file)
crystalyse view structure.cif
```

### 2. Your First Analysis
```bash
# Start the interactive shell
crystalyse shell

# In the shell, try these queries:
> Design a battery cathode material
> Find materials with band gap 2-3 eV
> /validate LiFePO4
> /status
> /help
```

## Interactive Shell

The interactive shell is the heart of CrystaLyse CLI, providing a conversational interface for materials discovery.

### Starting the Shell
```bash
crystalyse shell
```

You'll see the CrystaLyse ASCII banner and the prompt:
```
🔬 crystalyse > 
```

The emoji indicates the current mode:
- 🔬 Rigorous mode (default)
- 🎨 Creative mode

### Natural Language Queries
Simply type your materials research questions:

```
> Design a lead-free ferroelectric material
> Find perovskites with high dielectric constants  
> What are good cathode materials for sodium batteries?
> Analyze the stability of CsPbI3
```

### Shell Commands
All shell commands start with `/`:

#### Analysis Commands
- `/analyze <query>` - Full materials analysis
- `/screen <criteria>` - Batch screening mode
- `/predict <formula>` - Structure prediction only
- `/validate <composition>` - SMACT validation
- `/energy <structure>` - Energy calculation

#### Visualization Commands
- `/view [structure]` - Open 3D viewer in browser
- `/compare <struct1> <struct2>` - Side-by-side comparison
- `/export <format>` - Export results (CIF, JSON, HTML)

#### Session Commands
- `/save [name]` - Save current session
- `/load <session>` - Load previous session
- `/history` - Show command history
- `/fork` - Create session branch

#### System Commands
- `/mode [creative|rigorous]` - Switch analysis modes
- `/quick-view` - Toggle auto-view after analysis
- `/config` - View/edit configuration
- `/status` - System status
- `/help` - Show all commands
- `/exit` - Exit shell

### Modes

#### Rigorous Mode (🔬)
- Emphasis on validated, well-established materials
- Conservative predictions
- Detailed uncertainty quantification
- Literature-backed recommendations

#### Creative Mode (🎨)
- More exploratory and speculative suggestions
- Novel material combinations
- Higher risk, higher reward predictions
- Broader search space

Switch modes with:
```
> /mode creative
> /mode rigorous
```

## Commands Reference

### Shell Command
Start the interactive shell for conversational materials discovery.

```bash
crystalyse shell [options]

Options:
  --mode <mode>     Start in specific mode (creative|rigorous)
  --auto-view       Enable auto-view for structures
  --theme <theme>   Set visualization theme (light|dark)
```

### Analyze Command
Perform one-shot analysis from command line.

```bash
crystalyse analyze [options] <query>

Options:
  --mode <mode>     Analysis mode (creative|rigorous)
  --output <file>   Save results to file
  --format <fmt>    Output format (json|yaml|text)
  --view            Auto-open 3D viewer
```

Examples:
```bash
crystalyse analyze "sodium battery cathode" --mode rigorous --view
crystalyse analyze "high temperature superconductor" --output results.json
```

### View Command
Visualize crystal structures in 3D.

```bash
crystalyse view [options] <file>

Options:
  --style <style>   Visualization style (stick|sphere|cartoon)
  --theme <theme>   Color theme (light|dark)
  --labels          Show atom labels
  --unit-cell       Show unit cell
```

Examples:
```bash
crystalyse view structure.cif --style sphere --labels
crystalyse view structure.cif --theme dark --unit-cell
```

### Compare Command
Compare multiple crystal structures side-by-side.

```bash
crystalyse compare [options] <file1> <file2> [file3...]

Options:
  --property <prop> Highlight property differences
  --output <file>   Save comparison report
```

Example:
```bash
crystalyse compare LiFePO4.cif NaFePO4.cif --property voltage
```

## Visualization Features

### 3D Structure Viewer
The CLI automatically generates interactive 3D visualizations using 3Dmol.js:

#### Features
- **Rotate**: Click and drag to rotate
- **Zoom**: Mouse wheel or pinch to zoom
- **Pan**: Right-click and drag to pan
- **Styles**: Switch between stick, sphere, cartoon, surface
- **Labels**: Toggle atom/bond labels
- **Unit Cell**: Show/hide unit cell boundaries

#### Visualization Options
```javascript
// Available in visualization preferences
{
  style: 'stick' | 'sphere' | 'cartoon' | 'surface',
  showUnitCell: true | false,
  showLabels: true | false,
  backgroundColor: '#ffffff' | '#1a1a1a',
  autoRotate: true | false
}
```

### Auto-View
Enable automatic visualization after each analysis:

```
> /quick-view  # Toggle auto-view
```

When enabled, structures automatically open in your browser after analysis.

### Quick Actions
After each analysis, use quick actions for immediate follow-up:

- `[V]iew 3D` - Open 3D visualization
- `[E]xport` - Export structure/data
- `[S]ave` - Save to current session
- `[C]ontinue` - Return to shell

## Session Management

### Saving Sessions
```
> /save my_research_session
✅ Session saved as: my_research_session
```

### Loading Sessions
```
> /load my_research_session
✅ Session loaded: my_research_session
```

### Session Contents
Sessions include:
- Command history
- Analysis results
- Current mode settings
- Visualization preferences
- Bookmarked discoveries

### Session Files
Sessions are stored as JSON files in `~/.crystalyse/sessions/`

## Configuration

### CRYSTALYSE.md File
Create a `CRYSTALYSE.md` file in your working directory for project-specific settings:

```markdown
# Project Configuration
mode: rigorous
default_temperature: 0.7
auto_view: true
viewer_theme: dark

# Visual Feedback Preferences
feedback:
  show_progress: true
  show_estimates: true
  sound_alerts: false

# Visualization Preferences
viz_settings:
  style: ball_and_stick
  show_unit_cell: true
  background_color: "#1a1a1a"
  auto_rotate: false
  
# Chemical Systems of Interest
focus_elements: [Li, Na, K, Fe, Mn, Co, Ni]
exclude_elements: [Pb, Cd, Hg]

# Saved Criteria Sets
@battery_criteria:
  voltage: 2.5-4.0
  capacity: >100
  stability: >0.8

@solar_criteria:
  band_gap: 1.5-3.0
  absorption: >10^4
  stability: >0.9

# Workflow Shortcuts
@battery_screening: screen for cathode with @battery_criteria
@solar_search: find semiconductors with @solar_criteria
```

### Configuration Commands
```
> /config            # View current configuration
> /config edit       # Edit configuration file
> /theme dark        # Set visualization theme
```

## Examples

### Example 1: Battery Materials Research
```bash
# Start shell
crystalyse shell

# Set focus on battery materials
> /mode rigorous
> Design high-capacity cathode materials for sodium-ion batteries

# The system will analyze and provide results
# View the structure in 3D
> /view

# Save promising results
> /save sodium_cathodes_2024

# Compare with existing materials
> /compare current_result LiFePO4
```

### Example 2: Solar Cell Materials
```bash
crystalyse shell

# Creative exploration
> /mode creative
> Find lead-free perovskites for tandem solar cells

# Validate a specific composition
> /validate CH3NH3SnI3

# Screen for optimal band gaps
> /screen band_gap:1.2-1.8 stability:>0.8

# Export results for publication
> /export paper-ready
```

### Example 3: Ferroelectric Materials
```bash
crystalyse analyze "lead-free ferroelectric with high polarization" --mode rigorous --view

# Or in shell:
> Design lead-free ferroelectric materials for energy storage
> /validate BiFeO3
> /export computational-details
```

### Example 4: High-Throughput Screening
```bash
# From command line
crystalyse analyze "screen titanium oxides for photocatalysis" --output photocatalysts.json

# In shell with criteria sets
> /screen @solar_criteria titanium_compounds
> /export csv screening_results.csv
```

## Troubleshooting

### Common Issues

#### 1. Python Bridge Connection Failed
```
Error: Python bridge connection timeout
```

**Solutions:**
- Ensure Python 3.8+ is installed: `python3 --version`
- Check if CrystaLyse.AI modules are installed
- Try running in demo mode (automatic fallback)
- Verify firewall settings

#### 2. Browser Won't Open for Visualization
```
Warning: Could not open browser
```

**Solutions:**
- Manual open: The CLI provides file paths you can open manually
- Set default browser: `export BROWSER=firefox`
- Try alternative viewers: `crystalyse view --inline` (if supported)

#### 3. Command Not Recognized
```
Unknown command: /vieww
```

**Solutions:**
- Check spelling: `/view` not `/vieww`
- Use tab completion for commands
- Type `/help` to see all available commands

#### 4. Session Load Failed
```
Error: Session not found: my_session
```

**Solutions:**
- List available sessions: `/load` (without arguments)
- Check session directory: `~/.crystalyse/sessions/`
- Verify file permissions

#### 5. Export Failed
```
Error: Export format not supported
```

**Solutions:**
- Use supported formats: CIF, JSON, HTML, CSV
- Check output directory permissions
- Ensure disk space available

### Getting Help

1. **In-app help**: `/help` in shell or `crystalyse --help`
2. **Examples**: Check the `examples/` directory
3. **Logs**: Check `~/.crystalyse/logs/` for detailed error logs
4. **GitHub**: Report issues at the project repository

### Performance Tips

1. **Caching**: Results are cached automatically - repeat queries are faster
2. **Batch operations**: Use `/screen` for multiple similar queries
3. **Session management**: Save sessions to avoid re-running long analyses
4. **Close visualizations**: Close browser tabs to free memory

### Demo Mode

If CrystaLyse.AI modules aren't available, the CLI runs in demo mode:
- Sample data for testing interface
- All features work but with mock results
- Perfect for learning the interface
- Indicated by "Demo mode" messages

---

## Need More Help?

- **Documentation**: Check the technical implementation report
- **Examples**: See `examples/` directory for sample workflows
- **Community**: Join the CrystaLyse.AI community for discussions
- **Issues**: Report bugs or request features on GitHub

Happy materials discovery! 🔬✨