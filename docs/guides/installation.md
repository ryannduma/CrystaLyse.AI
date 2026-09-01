# Installation Guide

## Overview

This guide provides comprehensive instructions for installing Crystalyse on various platforms. Crystalyse requires Python 3.11 or higher and includes installation of all necessary chemistry tools and MCP servers.

## System Requirements

### Minimum Requirements

- **Python**: 3.11 or higher
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 5GB for installation + ~604 MB for Chemeleon model checkpoints and ~178 MB for the Materials Project phase-diagram cache (both auto-downloaded)
- **Network**: Internet connection for package downloads, API calls, and the first-run cache downloads (~523 MB Chemeleon archive, ~178 MB phase-diagram file)
- **Operating System**: 
  - Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
  - macOS 11+ (Big Sur or later)
  - Windows 10/11 with WSL2 (recommended)

### Recommended Requirements

- **Python**: 3.12 (the version the project is developed and tested on; CI runs the matrix on 3.11 and 3.12)
- **RAM**: 16GB for complex materials analysis
- **CPU**: Multi-core processor (4+ cores recommended)
- **GPU**: NVIDIA GPU with CUDA support (optional, for MACE acceleration)
- **Storage**: 10GB for full installation with models and databases

## Installation Methods

### Repository Installation (Current Method)

Clone and install from the repository:
```bash
# Clone repository
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI

# Create conda environment (recommended)
conda create -n crystalyse python=3.12
conda activate crystalyse

# Install in development mode
pip install -e .
```

**The editable install is required.** Crystalyse is not published to PyPI, and the
agent resolves the MCP server working directories relative to the installed
package (`<base_dir>/chemistry-unified-server/src`). A non-editable install into
`site-packages` cannot find them, and `get_server_config` raises
`FileNotFoundError: MCP server directory not found: <path>`.

### MCP Server Installation

**Important**: Install core package first, then MCP servers (they depend on `crystalyse` package).

```bash
# Step 1: Install core package FIRST (required)
# From the repository root - the root pyproject.toml points setuptools at dev/
pip install -e .

# Step 2: Install MCP servers (they import from crystalyse.tools.*)
# The three server sub-projects live under dev/, so install them from there.
# MCP servers declare crystalyse as a dependency - no PYTHONPATH manipulation needed
cd dev
pip install -e ./chemistry-unified-server      # 20 tools - validate/auto modes (SMACT + Chemeleon + MACE + pymatgen analysis)
pip install -e ./chemistry-creative-server     # 4 tools  - explore mode (Chemeleon + MACE)
pip install -e ./visualization-mcp-server      # 5 tools  - structure files and analysis plots
```

**Note**: MCP servers are thin wrappers over `crystalyse.tools.*` modules - 29 tools in total. Installation order matters!

The directory name `chemistry-creative-server` is a package name kept for
compatibility. It is unrelated to the retired `creative` mode name; the mode it
serves is now called `explore`.

### Chemeleon Model Checkpoints

Chemeleon requires ML model checkpoints (~604 MB on disk) for crystal structure prediction.

#### Zero-Configuration Auto-Download (Recommended)

Checkpoints auto-download on first use - **no manual setup needed**:

- **Location**: `~/.cache/crystalyse/chemeleon_checkpoints/`
- **Download Source**: Figshare (automatic, ~523 MB total)
- **Time**: First-run download takes 2-5 minutes depending on connection
- **One-time**: Checkpoints cached permanently after download
- **No Configuration Needed**: Works automatically without environment variables

**First Run Experience**:
```bash
crystalyse discover "Find stable perovskites"
# Downloads checkpoints on first use with progress bar:
# Downloading checkpoints.tar.gz: 100%|██████████| 523M/523M [00:05<00:00, 103MB/s]
# Extracting checkpoint files...
# Checkpoint setup complete: ~/.cache/crystalyse/chemeleon_checkpoints/
```

#### Custom Checkpoint Directory (Advanced)

If you need checkpoints in a specific location (e.g., shared lab server):

```bash
export CHEMELEON_CHECKPOINT_DIR="/path/to/existing/checkpoints"
crystalyse discover "..."  # Uses custom directory
```

The directory must contain:
- `chemeleon_csp_alex_mp_20_v0.0.2.ckpt` (141 MB)
- `chemeleon_dng_alex_mp_20_v0.0.2.ckpt` (161 MB)

#### Manual Setup (Offline Installation)

For offline installations or to pre-download checkpoints:

```bash
# On machine with internet:
wget https://ndownloader.figshare.com/files/54966305 -O chemeleon_ckpts.tar.gz

# Transfer to offline machine.  The archive wraps the checkpoints in a top-level
# ckpts/ directory, so extract to a staging directory and flatten the .ckpt files
# into the cache - extracting straight into ~/.cache/crystalyse/ puts them one
# level too deep and the loader will not find them.
mkdir -p ~/.cache/crystalyse/chemeleon_checkpoints
mkdir -p /tmp/chemeleon_extract
tar -xzf chemeleon_ckpts.tar.gz -C /tmp/chemeleon_extract
find /tmp/chemeleon_extract -name '*.ckpt' -exec mv {} ~/.cache/crystalyse/chemeleon_checkpoints/ \;
rm -rf /tmp/chemeleon_extract

# Verify:
ls ~/.cache/crystalyse/chemeleon_checkpoints/*.ckpt
# Should include:
#   chemeleon_csp_alex_mp_20_v0.0.2.ckpt
#   chemeleon_dng_alex_mp_20_v0.0.2.ckpt
```

Checkpoint management is handled by `crystalyse/tools/chemeleon/checkpoint_manager.py`.

### Phase Diagram Data

Energy-above-hull calculations need the Materials Project phase-diagram dataset
(~178 MB, 271,617 entries). It auto-downloads on first use, but you can pre-fetch
it so no download happens mid-run:

```bash
crystalyse setup           # download if missing
crystalyse setup --force   # re-download even if present
```

- **Location**: `~/.cache/crystalyse/ppd-mp_all_entries_uncorrected_250409.pkl.gz`
- **Integrity**: the file is MD5-verified before use
- **Override**: set `CRYSTALYSE_PPD_PATH` to point at a copy elsewhere

Without this file the rest of the system still runs, but energy-above-hull
calculations are unavailable.

### MACE Foundation Models

MACE fetches its foundation-model weights on first use and caches them in
`~/.cache/mace/`. No configuration is needed.

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

#### 1. Install Python 3.11+

```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-pip python3.11-venv

# Verify installation
python3.11 --version
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv crystalyse-env

# Activate environment
source crystalyse-env/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### 3. Install Crystalyse

Crystalyse is not published to PyPI, so install it editable from a clone:

```bash
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI
pip install -e .

# Then the three MCP servers, from dev/
cd dev
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server
```

### macOS

#### 1. Install Python 3.11+ using Homebrew

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Verify installation
python3.11 --version
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv crystalyse-env

# Activate environment
source crystalyse-env/bin/activate

# Install Crystalyse (not on PyPI - editable from a clone)
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI
pip install -e .

# Then the three MCP servers, from dev/
cd dev
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server
```

**macOS uses zsh.** When you persist your API key later in this guide, put the
export in `~/.zshenv`, not `~/.bashrc` - see [API Key Configuration](#api-key-configuration).

### Windows

#### Option 1: Using WSL2 (Recommended)

```bash
# Enable WSL2 and install Ubuntu
wsl --install

# Open Ubuntu terminal and follow Linux instructions above
```

#### Option 2: Native Windows Installation

```powershell
# Install Python 3.11 from python.org or Microsoft Store
# Verify installation
python --version

# Create virtual environment
python -m venv crystalyse-env

# Activate environment
crystalyse-env\Scripts\activate

# Install Crystalyse (not on PyPI - editable from a clone)
git clone https://github.com/ryannduma/CrystaLyse.AI.git
cd CrystaLyse.AI
pip install -e .

# Then the three MCP servers, from dev/
cd dev
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server
```

## Verification

After installation, verify everything works:

```bash
# Check installation
crystalyse --help

# Check which model backbones your API keys unlock
crystalyse models check

# Test basic functionality with a simple query
crystalyse discover "Find a perovskite material for solar cells" --mode explore
```

Expected output for working installation:
```bash
$ crystalyse --help
Usage: crystalyse [OPTIONS] COMMAND [ARGS]...

 Crystalyse v1.0.0-dev - Intelligent Scientific AI Agent for Inorganic Materials Design

Options:
  --project  -p   Project name for workspace. [default: crystalyse_session]
  --mode          Agent operating mode (explore, validate, auto). [default: auto]
  --model         Language model to use.
  --version       Show version and exit.
  --verbose  -v   Enable verbose output

Commands:
  discover            Run a single, non-interactive discovery query with automatic provenance capture.
  setup               Download and set up required data files (e.g., phase diagrams).
  chat                Start an interactive chat session for materials discovery.
  analyse-provenance  Analyse provenance data from previous discovery sessions.
  models              Inspect and validate available model backbones.
```

`--project`, `--mode`, `--model` and `--verbose` are global options on the
`crystalyse` callback, so they must come **before** the subcommand:

```bash
crystalyse --mode validate --model anthropic_claude_sonnet discover "..."
```

`discover` additionally accepts its own `--mode` and `--project/-p`, which
override the global values for that one run.

## Configuration

### API Key Configuration

Crystalyse reaches its language models through four providers. You only need the
key for the backbone you actually select:

| Environment variable | Registry entries it unlocks |
|---|---|
| `OPENAI_API_KEY` | `openai_o4_mini` (default), `openai_o3`, `openai_gpt4o_mini` |
| `ANTHROPIC_API_KEY` | `anthropic_claude_opus`, `anthropic_claude_sonnet`, `anthropic_claude_haiku` |
| `OPENROUTER_API_KEY` | `openrouter_claude_opus`, `openrouter_llama3_70b` |
| `MISTRAL_API_KEY` | `mistral_large` |

`ollama_llama3_70b_direct` needs no key - it talks to a local Ollama server.

```bash
# Set environment variable (recommended)
export OPENAI_API_KEY="your-api-key-here"

# Persist it - bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Persist it - zsh (the default shell on macOS)
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshenv
source ~/.zshenv

# Confirm which keys the model registry can see
crystalyse models check

# Test API connection
crystalyse discover "test query" --mode explore
```

**Use `~/.zshenv`, not `~/.zshrc`.** `~/.zshrc` is read only by interactive
shells. The MCP servers are launched as non-interactive subprocesses that inherit
`os.environ` from the parent process, so a key set only in `~/.zshrc` is invisible
to them.

**There is no `.env` support.** Nothing in the codebase loads a `.env` file - keys
must be real environment variables.

`crystalyse models check` walks the whole registry and prints a ✓ or ✗ per entry,
exiting non-zero if *any* entry's key is unset. A ✗ against a provider you never
intend to use is expected and harmless.

### Selecting a Model

```bash
# Use a specific backbone for one run (global option, before the subcommand)
crystalyse --model anthropic_claude_sonnet discover "Find stable perovskites"

# See the effective registry and where each entry came from
crystalyse models list
```

`crystalyse models list` prints one row per backbone with the columns **Name**,
**Backend**, **Model ID**, **Context**, **Modes**, **Env Var**, **Source** and
**Usable**. Source is `built-in`, `user-override` or `user-defined`.

Every Anthropic, OpenRouter and Mistral entry routes through LiteLLM, which is an
optional extra declared in `dev/pyproject.toml`, so install it from `dev/`:

```bash
cd dev
pip install -e ".[litellm]"
```

### View Current Configuration

Configuration is TOML, not YAML. Two files are read, project first:

1. `<project>/.crystalyse/config.toml` - project level, highest precedence
2. `~/.crystalyse/config.toml` - user level

```bash
# Check configuration file
cat ~/.crystalyse/config.toml
```

Neither file is created for you; both are optional, and the built-in defaults work
out of the box.

### Advanced Configuration

The recognised runtime keys are exactly these five. Unrecognised top-level keys are
silently dropped.

```toml
# ~/.crystalyse/config.toml
default_model = "openai_o4_mini"   # any name from `crystalyse models list`
default_mode = "explore"           # explore | validate | auto
plan_mode = "auto"                 # on | off | auto
plans_directory = ".crystalyse/plans"
plans_cleanup_days = 30
```

`[models.<name>]` tables either adjust a built-in registry entry or define a new
one:

```toml
# Override value-like fields of a built-in entry
[models.openai_o4_mini]
reasoning_effort = "high"
context_window = 200000

# Define a completely new entry
[models.my_local_model]
backend = "openai-compat"
model_id = "qwen2.5:32b"
api_key_env_var = ""
base_url = "http://localhost:11434/v1"
```

Only value-like fields may be overridden on a built-in: `model_id`, `base_url`,
`context_window`, `max_tokens`, `temperature`, `reasoning_effort`,
`thinking_budget_tokens` and `notes`. Capability fields (`backend`,
`api_key_env_var`, `supports_tool_calling`, `supports_structured_output`,
`supported_modes`) may only be set when defining a *new* entry. Anything invalid
raises `ModelOverrideError` at startup rather than being quietly ignored.

### Runtime Environment Variables

Everything else is tuned with environment variables rather than a config file. The
MCP servers run as stdio subprocesses launched by the agent - they are not HTTP
services, so there are no ports or hosts to configure.

| Variable | Effect |
|---|---|
| `CRYSTALYSE_PYTHON_PATH` | Interpreter used to launch the chemistry-unified MCP server |
| `CRYSTALYSE_PROVENANCE_DIR` | Where provenance runs are written (default `./provenance_output`) |
| `CRYSTALYSE_SHOW_PROVENANCE_SUMMARY` | Show the provenance summary table after `discover` (default `true`) |
| `CRYSTALYSE_SESSION_PREFIX` | Prefix for generated session IDs (default `crystalyse`) |
| `CRYSTALYSE_CAPTURE_RAW` | Save raw tool outputs into the provenance run (default `true`) |
| `CRYSTALYSE_CAPTURE_MCP_LOGS` | Capture MCP server logs (default `false`) |
| `CRYSTALYSE_VISUAL_TRACE` | Live visual trace of tool calls (default `true`) |
| `CRYSTALYSE_PPD_PATH` | Explicit path to the phase-diagram file |
| `CHEMELEON_CHECKPOINT_DIR` | Custom Chemeleon checkpoint directory |
| `CRYSTALYSE_DEBUG` | Debug mode, also propagated into the MCP subprocesses (default `false`) |

## Dependency Management

### Core Dependencies

Installing `crystalyse` pulls in:

| Package | Declared pin | Installed |
|---|---|---|
| `openai` | `>=3.0.0,<4` | 3.3.1 |
| `openai-agents` | `>=0.22.0,<0.23` | 0.22.0 |
| `smact` | `>=4.0.0,<5.0.0` | 4.0.0 |
| `chemeleon-dng` | `>=0.1.5,<0.2.0` | 0.1.5, from PyPI - no longer a git dependency |
| `torch` | `>=2.1.0,<2.11` | 2.10.0 |
| `mace-torch` | `>=0.3.0` | |
| `pymatgen` | `>=2024.1.0` | |
| `ase` | `>=3.22.0` | |
| `numpy` | `>=1.24.0,<3.0.0` | |
| `pandas` | `>=2.0.0` | |
| `pydantic` | `>=2.0.0` | |
| `rich`, `click`, `typer`, `prompt-toolkit`, `typing-extensions` | | |

The MCP servers add their own: `chemistry-unified-server` and
`chemistry-creative-server` require `mcp>=2.0.0,<3.0.0` (2.0.0 installed - mcp 2.0
renamed `FastMCP` to `MCPServer`), and `visualization-mcp-server` requires
`pymatviz<0.19.0` (0.18.0 installed).

The `torch<2.11` ceiling is deliberate: torch 2.11.0 moved to a CUDA 13.0 runtime,
which needs a driver reporting maxCuda >= 13.0. Drivers pinned at CUDA 12.x - the
common HPC case - fall back silently to CPU, and every Chemeleon or MACE call then
takes the slow path.

### Optional Dependencies

Five extras are declared in `dev/pyproject.toml`, so run these from `dev/`:

```bash
cd dev
pip install -e ".[visualization]"  # plotly, py3Dmol, kaleido, pymatviz
pip install -e ".[litellm]"        # litellm==1.83.0 - needed for every non-OpenAI backbone
pip install -e ".[docs]"           # mkdocs and friends
pip install -e ".[dev]"            # pytest, ruff, mypy, pyright, pre-commit, codespell
pip install -e ".[all]"            # currently an alias for [visualization]
```

`[all]` does **not** include `litellm`. Every Anthropic, OpenRouter and Mistral
registry entry uses the LiteLLM backend, so those need `.[litellm]` explicitly.
`litellm` is pinned to exactly `1.83.0` - the only release whose `openai`
requirement is satisfiable alongside openai-agents 0.22's `openai>=3.0.0`.

### MCP Server Dependencies

There are exactly three MCP servers, all under `dev/`, and all thin wrappers over
`crystalyse.tools.*`. Each declares `crystalyse` as a dependency, which is why the
core package must be installed first.

1. **Chemistry Unified Server** (`dev/chemistry-unified-server`)
   - **Tools**: 20 - SMACT screening, Chemeleon structure prediction, MACE energies, pymatgen analysis
   - **Used by**: `validate` and `auto` modes

2. **Chemistry Creative Server** (`dev/chemistry-creative-server`)
   - **Tools**: 4 - Chemeleon + MACE
   - **Used by**: `explore` mode

3. **Visualisation Server** (`dev/visualization-mcp-server`)
   - **Tools**: 5 - CIF output and pymatviz analysis suites
   - **Used by**: every mode, alongside whichever chemistry server the mode selects

That is 29 tools in total. All three run as stdio subprocesses launched by the
agent; there are no intermediate per-tool servers.

## Environment Validation

Test your installation:

```bash
# Check help system
crystalyse --help

# Confirm which backbones your keys unlock
crystalyse models check

# Inspect the effective model registry
crystalyse models list

# Basic functionality test
crystalyse discover "test query" --mode explore
```

MCP server status is not exposed as a top-level command. Start a chat session and
use the slash commands instead:

```
crystalyse chat
/mcp      # server status
/tools    # the tools each server exposes
```

## Troubleshooting

### Common Issues

#### 1. Python Version Error

```
Error: Crystalyse requires Python 3.11 or higher
```

**Solution:**
```bash
# Check current Python version
python --version

# Create conda environment with a supported Python version
conda create -n crystalyse python=3.12
conda activate crystalyse
```

#### 2. Installation Failures

```
Error: Failed to install dependencies
```

**Solution:**
```bash
# Use conda environment (recommended)
conda create -n crystalyse python=3.12
conda activate crystalyse

# Clean install
pip install --upgrade pip
pip install -e .
```

#### 3. MCP Server Connection Issues

```
Error: MCP server not found or failed to start
```

Startup failures are logged as warnings (`⚠️ Could not start {server_name} server`)
and the run continues without that server, so the visible symptom is usually a run
that is missing tools rather than a hard crash.

**Solution:**
```bash
# Most common cause: the interpreter cannot be found.
#   FileNotFoundError: Python executable not found: ...
#   Set CRYSTALYSE_PYTHON_PATH environment variable if using a specific conda environment.
export CRYSTALYSE_PYTHON_PATH="$(which python)"

# Second cause: the server directory is missing, which means the package was not
# installed editable from the repository.
#   FileNotFoundError: MCP server directory not found: <path>
cd /path/to/CrystaLyse.AI
pip install -e .
cd dev
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server
```

Then check server status from inside a chat session:

```
crystalyse chat
/mcp
```

#### 4. API Key Issues

```
RuntimeError: ModelConfig 'openai_o4_mini' requires env var 'OPENAI_API_KEY', but it is not set.
```

**Solution:**
```bash
# Set the key for the provider your chosen model uses
export OPENAI_API_KEY="sk-your-key-here"      # openai_* entries
export ANTHROPIC_API_KEY="sk-ant-..."         # anthropic_* entries
export OPENROUTER_API_KEY="sk-or-..."         # openrouter_* entries
export MISTRAL_API_KEY="..."                  # mistral_large

# Verify what the registry can see
crystalyse models check

# Test with simple query
crystalyse discover "test" --mode explore
```

Keys must be real environment variables - a `.env` file is not read. On zsh, put
the exports in `~/.zshenv` so non-interactive subprocesses inherit them.

#### 5. Import Errors

```
Error: No module named 'crystalyse'
```

**Solution:**
```bash
# Ensure you're in the correct environment
conda activate crystalyse

# Reinstall in development mode
pip install -e .

# Check installation
python -c "import crystalyse; print('Success')"
```

#### 6. Memory Issues

```
Error: Insufficient memory for large structure analysis
```

**Solution:**
```bash
# Use explore mode, which runs the lighter 4-tool chemistry server
crystalyse discover "..." --mode explore
```

Structure generation dominates memory use, so asking for fewer candidate
structures in the query itself is the most effective lever. Allow at least 16 GB of
RAM for `validate` runs.

### Performance Optimisation

#### 1. Pre-fetch the Caches

```bash
# Phase diagram data (~178 MB) - avoids a download in the middle of a run
crystalyse setup
```

The Chemeleon checkpoints (~604 MB) are fetched on first structure prediction; run
one throwaway `discover` query to warm them before timing anything.

#### 2. Choose the Cheaper Mode

`explore` connects the 4-tool chemistry-creative server with a 120 s timeout;
`validate` connects the 20-tool chemistry-unified server with a 300 s timeout.
`auto` uses the unified server with a 180 s timeout.

#### 3. Review Where the Time Went

```bash
# Performance metrics for the most recent run: total runtime,
# time to first byte, and total tool calls
crystalyse analyse-provenance --latest
```

## Updating

### Regular Updates

Crystalyse is not published to PyPI, so updates come from the repository:

```bash
cd /path/to/CrystaLyse.AI
git pull origin master
pip install -e .
```

### Development Updates

```bash
# Update development installation (extras are declared in dev/pyproject.toml)
cd /path/to/CrystaLyse.AI
git pull origin master
cd dev
pip install -e ".[dev]"
```

## Uninstallation

### Clean Uninstall

```bash
# Uninstall the core package and the three MCP servers
pip uninstall crystalyse chemistry-unified-server chemistry-creative-server visualization-mcp

# Remove configuration and session databases (optional)
rm -rf ~/.crystalyse

# Remove cached checkpoints and datasets (optional, ~800 MB)
rm -rf ~/.cache/crystalyse ~/.cache/mace

# Remove virtual environment (if used)
rm -rf crystalyse-env
```

### Reset Configuration

```bash
# Reset to defaults
rm ~/.crystalyse/config.toml
```

## GPU Support (Optional)

### CUDA Installation for MACE Acceleration

For faster MACE energy calculations, install CUDA support:

```bash
# Check for NVIDIA GPU
nvidia-smi

# Install PyTorch with CUDA 12 support, respecting the project's <2.11 ceiling.
# Pick the cu12x index matching your driver from https://pytorch.org/get-started/locally/
conda activate crystalyse
pip install "torch>=2.1.0,<2.11" --index-url https://download.pytorch.org/whl/cu126

# Verify GPU availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

Do not drop the `<2.11` constraint: torch 2.11.0 requires a CUDA 13 driver, and on
a CUDA 12.x driver it falls back silently to CPU. torch 2.10.x still ships cu12x
wheels, which is why the ceiling exists.

### Performance with GPU

- **MACE calculations**: 3-5x speedup
- **Large structures**: Up to 10x speedup
- **Batch analysis**: Significant performance improvement

## Development Setup

### Additional Development Tools

```bash
# Install development dependencies from dev/, where the extras are declared.
# The dev extra already provides pytest, pytest-asyncio, pytest-cov,
# pytest-timeout, anyio, ruff, mypy, pyright, pre-commit and codespell -
# no manual installs needed.
cd dev
pip install -e ".[dev]"

# Run tests from dev/, where testpaths points at tests/
python -m pytest
```

## Next Steps

After successful installation:

1. **Follow the [Quickstart Guide](../quickstart.md)** - Get started with your first materials analysis
2. **Read the [CLI Usage Guide](cli_usage.md)** - Master the command-line interface
3. **Explore [Analysis Modes](../concepts/analysis_modes.md)** - Understand explore vs validate workflows
4. **Study [Tools Documentation](../tools/index.md)** - Learn about SMACT, Chemeleon, MACE, and visualisation tools

## Quick Start Verification

Test your installation with this simple workflow:

```bash
# Set your API key (on zsh, put this in ~/.zshenv to persist it)
export OPENAI_API_KEY="sk-your-key-here"

# Confirm the key is visible to the model registry
crystalyse models check

# Test explore mode (fast)
crystalyse discover "Find a stable perovskite for solar cells" --mode explore

# Test validate mode (thorough)
crystalyse discover "Analyse CsSnI3 stability" --mode validate

# Start an interactive session.  chat has no --mode option: mode is a global
# option and goes before the subcommand.
crystalyse --mode explore chat -u researcher -s test_session
```

`creative`, `rigorous` and `adaptive` still resolve as deprecated aliases for
`explore`, `validate` and `auto`, but they emit a `DeprecationWarning` and are
scheduled for removal in v2.0.

## Support

If you encounter issues:

1. **Check this troubleshooting section** for common solutions
2. **Review the [CLI Usage Guide](cli_usage.md)** for command examples
3. **Check the GitHub repository** for known issues
4. **Create a detailed issue report** with:
   - Python version (`python --version`)
   - Installation method used
   - Error messages
   - Configuration file content (`~/.crystalyse/config.toml`, if you have one)
   - Output of `crystalyse models check`