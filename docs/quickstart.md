# Quickstart

Get up and running with Crystalyse in minutes. This guide covers installation, configuration, and your first materials analysis.

## Installation

### Prerequisites

- Python 3.12 (3.11 is the supported floor; CI tests both)
- An API key for at least one provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` or `MISTRAL_API_KEY`
- 8GB RAM recommended (4GB minimum)
- Internet connection for the automatic first-run cache downloads
- Storage: ~604 MB for Chemeleon checkpoints in `~/.cache/crystalyse/chemeleon_checkpoints/`, ~178 MB for the phase-diagram dataset in `~/.cache/crystalyse/`, plus MACE foundation models in `~/.cache/mace/`

### Quick Install

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ryannduma/CrystaLyse.AI.git
   cd CrystaLyse.AI
   ```

2. **Create environment:**
   ```bash
   conda create -n crystalyse python=3.12
   conda activate crystalyse
   ```

3. **Install Crystalyse:**
   ```bash
   # Step 1: Install core package FIRST (required).  The install must be
   # editable: Crystalyse is not on PyPI, and the agent locates the MCP
   # servers relative to the installed package.
   pip install -e .

   # Step 2: Install MCP servers from dev/, where the sub-projects live
   cd dev
   pip install -e ./chemistry-unified-server      # 20 tools - validate/auto modes
   pip install -e ./chemistry-creative-server     # 4 tools  - explore mode
   pip install -e ./visualization-mcp-server      # 5 tools  - structures and analysis plots

   # Optional: required for every non-OpenAI backbone (Anthropic, OpenRouter, Mistral)
   pip install -e ".[litellm]"
   ```

4. **Verify installation:**
   ```bash
   crystalyse --help
   crystalyse models check
   ```

**Note on First Run**: On first execution, Crystalyse auto-downloads ~604 MB of Chemeleon model checkpoints to `~/.cache/crystalyse/chemeleon_checkpoints/` (a ~523 MB archive) with a progress bar. Energy-above-hull calculations additionally need a ~178 MB Materials Project phase-diagram file; pre-fetch it with `crystalyse setup` so it does not download mid-query.

## Configuration

### Set an API Key

Crystalyse reaches models through four providers. Set the key for the backbone you
plan to use - you do not need all four:

```bash
export OPENAI_API_KEY="your-api-key-here"   # openai_o4_mini (default), openai_o3, openai_gpt4o_mini
export ANTHROPIC_API_KEY="sk-ant-..."       # anthropic_claude_opus / sonnet / haiku
export OPENROUTER_API_KEY="sk-or-..."       # openrouter_claude_opus, openrouter_llama3_70b
export MISTRAL_API_KEY="..."                # mistral_large
```

These must be real environment variables - there is no `.env` support anywhere in
the codebase. To persist a key on zsh, append the export to `~/.zshenv`, not
`~/.zshrc`: `~/.zshrc` is read only by interactive shells, and the MCP servers run
as non-interactive subprocesses that inherit the parent's environment.

### Choose a Model

```bash
# One run with a specific backbone.  --model is a global option, so it comes
# before the subcommand.
crystalyse --model anthropic_claude_sonnet discover "Find stable perovskites"
```

Or set a default in `.crystalyse/config.toml` - the project-level file wins over
`~/.crystalyse/config.toml`:

```toml
default_model = "openai_o4_mini"
default_mode = "explore"
```

### Verify Configuration

```bash
# Which backbones can your keys reach?
crystalyse models check

# The effective registry, with a Source column showing built-in vs config override
crystalyse models list
```

`crystalyse models check` exits non-zero if *any* registry entry's key is unset, so
a ✗ next to a provider you never intend to use is expected.

`crystalyse --help` shows the command list and global options; it does not report
MCP server status. For that, start a chat session and use `/mcp` or `/tools`.

## First Materials Analysis

### Quick Analysis

Analyse a perovskite material for solar cells:

```bash
crystalyse discover "Find a perovskite material for solar cells" --mode explore
```

Expected output:
```
Starting non-interactive discovery: Find a perovskite material for solar cells
Mode: explore | Project: crystalyse_session

╭──────────────────────────── Discovery Report ─────────────────────────────╮
│ Generated 5 perovskite candidates with formation energies:                │
│                                                                           │
│ 1. CsGeI3 - Formation energy: -2.558 eV/atom (most stable)                │
│ 2. CsPbI3 - Formation energy: -2.542 eV/atom                              │
│ 3. CsSnI3 - Formation energy: -2.529 eV/atom                              │
│ ...                                                                       │
╰───────────────────────────────────────────────────────────────────────────╯

                               Provenance Summary
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric           ┃ Value                                                     ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Session ID       │ crystalyse_explore_20260831_143012                        │
│ Materials Found  │ 5                                                         │
│ With Energy Data │ 5                                                         │
│ Energy Range     │ -2.558 to -2.529 eV/atom                                  │
│ Runtime          │ 50.3s                                                     │
│ MCP Tools Used   │ generate_crystal_structure, calculate_formation_energy    │
│ Output Location  │ provenance_output/runs/crystalyse_explore_20260831_143012 │
└──────────────────┴───────────────────────────────────────────────────────────┘
```

The report panel carries whatever the agent wrote; the Provenance Summary table
below it is generated from the captured run. Add `--hide-summary` to suppress the
table - the provenance data is still written to disk either way.

### Interactive Session

Start a conversation-based session:

```bash
crystalyse chat -u researcher -s solar_project
```

`chat` accepts only `--user/-u` and `--session/-s`. Mode is a global option, so it
goes before the subcommand:

```bash
crystalyse --mode explore chat -u researcher -s solar_project
```

Running `crystalyse` with no arguments starts `chat` with the defaults.

In the session:
```
🔬 You: Find lead-free perovskites for photovoltaics
🤖 Crystalyse: I'll explore lead-free perovskite alternatives...

🔬 You: What about tin-based alternatives?
🤖 Crystalyse: Excellent question! Based on the previous analysis...
```

Session commands:
- `/mode [show|explore|validate|auto]` - view or change the operating mode
- `/model [show|...]` - view or change the language model
- `/tools [desc|nodesc]` - list the MCP tools available
- `/mcp [status|servers|desc]` - MCP server status and details
- `/memory [show|clear|refresh]` - manage agent memory and conversation history
- `/stats` - session statistics and performance
- `/about` - version and system information
- `/help` - show available commands
- `/clear` - clear the terminal screen
- `/quit` or `/exit` - end session

## Analysis Modes

There are three modes - `explore`, `validate` and `auto` - and the CLI default is
`auto`. The old names `creative`, `rigorous` and `adaptive` still resolve as
deprecated aliases, but they emit a `DeprecationWarning` and are scheduled for
removal in v2.0.

### Explore Mode (Fast Exploration)

```bash
crystalyse discover "Design high-capacity battery materials" --mode explore
```

- **Server**: chemistry_creative (4 tools) plus the visualisation server
- **Tools Used**: Chemeleon + MACE
- **Timeout**: 120 s
- **Output**: Structure generation + energy calculation + structure files

### Validate Mode (Complete Validation)

```bash
crystalyse discover "Find stable electrolyte materials" --mode validate
```

- **Server**: chemistry_unified (20 tools) plus the visualisation server
- **Tools Used**: SMACT + Chemeleon + MACE + pymatgen analysis
- **Timeout**: 300 s
- **Output**: Composition validation + structures + energies + comprehensive analysis plots

### Auto Mode (Default)

```bash
crystalyse discover "Screen Na-ion cathodes"
```

- **Server**: chemistry_unified (20 tools) plus the visualisation server
- **Timeout**: 180 s
- **Output**: the balanced default used when you have not named a mode

## Command Reference

### Basic Commands

```bash
# One-shot discovery
crystalyse discover "your query" --mode [explore|validate|auto]

# Interactive chat - mode is a global option, so it comes before the subcommand
crystalyse --mode explore chat -u username -s session_name

# Pre-fetch the phase-diagram dataset
crystalyse setup

# Inspect a previous run's provenance
crystalyse analyse-provenance --latest

# Model registry
crystalyse models list
crystalyse models check
```

The full command set is `discover`, `setup`, `chat`, `analyse-provenance` and
`models list` / `models check`. The global options `--project/-p`, `--mode`,
`--model`, `--verbose/-v` and `--version` all belong before the subcommand.

### Unified Interface

Launch the interactive interface - `crystalyse` with no arguments starts `chat`:
```bash
crystalyse
```

Available in-session commands:
- `/mode explore|validate|auto` - Switch analysis modes
- `/model show` - View or change the language model
- `/tools`, `/mcp` - Inspect available tools and server status
- `/help` - Show help
- `/clear` - Clear screen
- `/exit` - Exit

## Understanding Output

### Explore Mode Output
- **Structure Files**: CIF files for each candidate structure
- **Energy Rankings**: Formation energies per atom for stability comparison
- **Quick Results**: Streamlined output focused on structure and stability

### Validate Mode Output
- **Comprehensive Analysis**: XRD patterns, RDF plots, coordination analysis
- **Validation Reports**: SMACT composition screening results
- **Professional Plots**: Publication-ready PDF analysis files
- **Complete Pipeline**: Full traceability from composition to properties

## Working with Results

### Output Files

Crystalyse writes structure and analysis files into your working directory:

```bash
# Structure files, one per candidate
CsGeI3.cif
CsPbI3.cif

# Analysis suite, written by create_pymatviz_analysis_suite
CsGeI3_analysis/
├── CsGeI3.cif                       # Structure file
├── XRD_Pattern_CsGeI3.pdf           # X-ray diffraction
├── RDF_Analysis_CsGeI3.pdf          # Radial distribution
├── Coordination_Analysis_CsGeI3.pdf # Coordination environment
└── 3D_Structure_CsGeI3.pdf          # Rendered structure
```

Interactive 3dmol.js HTML output is disabled for v2.0-alpha. The visualisation tool
writes a CIF file instead and reports that in its own result payload, so open the
CIF in VESTA, OVITO or any structure viewer.

### Session Management

```bash
# Named sessions keep conversation context across days.  The workspace project
# becomes <project>_<session>, and session state lives in ~/.crystalyse/sessions.
crystalyse chat -u battery_researcher -s lithium_study

# Provenance for one-shot runs lands in ./provenance_output/runs/
crystalyse discover "..." --provenance-dir ./my_research

# Inspect what a run actually did
crystalyse analyse-provenance --latest
crystalyse analyse-provenance --session crystalyse_validate_20260831_153834
```

## Example Workflows

### Battery Material Design

```bash
# Start a battery research session in validate mode
crystalyse --mode validate chat -u battery_researcher -s lithium_study

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
crystalyse discover "Screen perovskites with band gaps 1.2-1.6 eV" --mode explore

# Detailed analysis of promising candidates
crystalyse discover "Analyse CsSnI3 for photovoltaic applications" --mode validate
```

## Troubleshooting

### Common Issues

1. **MCP Server Connection Errors**

   Startup failures are logged as warnings (`⚠️ Could not start ... server`) and the
   run continues without that server, so the symptom is usually a run that is
   missing tools rather than a crash.

   ```bash
   # Most common cause: the interpreter cannot be found
   export CRYSTALYSE_PYTHON_PATH="$(which python)"

   # Second cause: the package was not installed editable from the clone
   pip install -e .

   # Then check status from inside a session, with /mcp and /tools
   crystalyse chat
   ```

2. **API Key Issues**
   ```bash
   # Check every registry entry's key at once
   crystalyse models check

   # Verify a specific key is exported into this shell
   echo $OPENAI_API_KEY
   ```

   No `.env` file is read, and on zsh the export belongs in `~/.zshenv` so
   non-interactive subprocesses inherit it.

3. **Memory Errors**
   - Use `explore` mode, which runs the lighter 4-tool chemistry server
   - Ask for fewer candidate structures in the query itself
   - Ensure 8GB+ RAM available

4. **GPU Issues**
   ```bash
   # MACE will automatically fall back to CPU
   python -c "import torch; print(torch.cuda.is_available())"
   ```

   torch is capped below 2.11 deliberately: 2.11 moved to a CUDA 13.0 runtime, and
   on a CUDA 12.x driver it falls back silently to CPU.

### Getting Help

- **Documentation**: Browse the complete [CLI Guide](guides/cli_usage.md)
- **Tool Issues**: Check individual tool documentation under [Tools](tools/index.md)
- **Verbose Output**: `--verbose`/`-v` is a global option, so it goes before the subcommand - `crystalyse --verbose discover "..."`. File logging is written to `crystalyse.log`.


## Next Steps

Now that you have Crystalyse running:

1. **Learn the Tools**: Explore [SMACT](tools/smact.md), [Chemeleon](tools/chemeleon.md), and [MACE](tools/mace.md) capabilities
2. **Understand Modes**: Read about [Analysis Modes](concepts/analysis_modes.md) and when to use each
3. **Advanced Features**: Check out [Session Management](concepts/sessions.md) for persistent research
4. **Integration**: Check [API Reference](reference/index.md) for programmatic usage

Ready to start designing materials? Try the [CLI Usage Guide](guides/cli_usage.md) for comprehensive examples.