# Installation Guide

## Overview

This guide provides comprehensive instructions for installing Crystalyse on various platforms. Crystalyse requires Python 3.11 or higher and includes installation of all necessary chemistry tools and MCP servers.

## System Requirements

### Minimum Requirements

- **Python**: 3.11 or higher
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 5GB for installation + ~600MB for Chemeleon model checkpoints (auto-downloaded)
- **Network**: Internet connection for package downloads, API calls, and first-run Chemeleon checkpoint download (~523MB)
- **Operating System**: 
  - Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
  - macOS 11+ (Big Sur or later)
  - Windows 10/11 with WSL2 (recommended)

### Recommended Requirements

- **Python**: 3.11 (tested and verified)
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
cd Crystalyse

# Create conda environment (recommended)
conda create -n crystalyse python=3.11
conda activate crystalyse

# Install in development mode
pip install -e .
```

### MCP Server Installation

**Important**: Install core package first, then MCP servers (they depend on `crystalyse` package).

```bash
# Step 1: Install core package FIRST (required)
# From the dev/ directory where pyproject.toml is located
pip install -e .

# Step 2: Install MCP servers (they import from crystalyse.tools.*)
# MCP servers declare crystalyse as a dependency - no PYTHONPATH manipulation needed
pip install -e ./chemistry-unified-server      # Complete validation mode (SMACT + Chemeleon + MACE)
pip install -e ./chemistry-creative-server     # Fast exploration mode (Chemeleon + MACE)
pip install -e ./visualization-mcp-server      # 3D visualization and analysis
```

**Note**: MCP servers are thin wrappers over `crystalyse.tools.*` modules. Installation order matters!

### Chemeleon Model Checkpoints

Chemeleon requires ML model checkpoints (~600 MB) for crystal structure prediction.

#### Zero-Configuration Auto-Download (Recommended)

Checkpoints auto-download on first use - **no manual setup needed**:

- **Location**: `~/.cache/crystalyse/chemeleon_checkpoints/`
- **Download Source**: Figshare (automatic, ~523 MB total)
- **Time**: First-run download takes 2-5 minutes depending on connection
- **One-time**: Checkpoints cached permanently after download
- **No Configuration Needed**: Works automatically without environment variables

**First Run Experience**:
```bash
crystalyse analyse "Find stable perovskites"
# Downloads checkpoints on first use with progress bar:
# Downloading checkpoints.tar.gz: 100%|██████████| 523M/523M [00:05<00:00, 103MB/s]
# Extracting checkpoint files...
# Checkpoint setup complete: ~/.cache/crystalyse/chemeleon_checkpoints/
```

#### Custom Checkpoint Directory (Advanced)

If you need checkpoints in a specific location (e.g., shared lab server):

```bash
export CHEMELEON_CHECKPOINT_DIR="/path/to/existing/checkpoints"
crystalyse analyse "..."  # Uses custom directory
```

The directory must contain:
- `chemeleon_csp_alex_mp_20_v0.0.2.ckpt` (141 MB)
- `chemeleon_dng_alex_mp_20_v0.0.2.ckpt` (161 MB)

#### Manual Setup (Offline Installation)

For offline installations or to pre-download checkpoints:

```bash
# On machine with internet:
wget https://figshare.com/ndownloader/files/54966305 -O checkpoints.tar.gz

# Transfer to offline machine and extract:
mkdir -p ~/.cache/crystalyse/chemeleon_checkpoints
tar -xzf checkpoints.tar.gz -C ~/.cache/crystalyse/

# Verify:
ls ~/.cache/crystalyse/chemeleon_checkpoints/*.ckpt
# Should show:
#   chemeleon_csp_alex_mp_20_v0.0.2.ckpt
#   chemeleon_dng_alex_mp_20_v0.0.2.ckpt
```

Checkpoint management is handled by `crystalyse/tools/chemeleon/checkpoint_manager.py`.

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

```bash
pip install crystalyse
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

# Install Crystalyse
pip install crystalyse
```

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

# Install Crystalyse
pip install crystalyse
```

## Automated Installation Script

For convenience, use our installation script:

```bash
# Download and run installation script
curl -sSL https://install.crystalyse.ai | bash
```

The script automatically:
- Detects your operating system
- Checks Python version
- Creates virtual environment
- Installs Crystalyse and dependencies
- Configures initial settings

## Verification

After installation, verify everything works:

```bash
# Check installation
crystalyse --help

# Test basic functionality with a simple query
crystalyse discover "Find a perovskite material for solar cells" --mode creative
```

Expected output for working installation:
```bash
$ crystalyse --help
Usage: crystalyse [OPTIONS] COMMAND [ARGS]...

  Crystalyse - Computational Materials Design Platform

Commands:
  discover  Run non-interactive materials discovery
  chat      Start interactive chat session
  user-stats View user statistics
```

## Configuration

### API Key Configuration

Crystalyse requires an OpenAI API key:

```bash
# Set environment variable (recommended)
export OPENAI_API_KEY="your-api-key-here"

# Add to shell profile for persistence
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Test API connection
crystalyse discover "test query" --mode creative
```

### View Current Configuration

```bash
# Check configuration file
cat ~/.crystalyse/config.yaml
```

This will show the current configuration settings.

### Advanced Configuration

Edit the configuration file directly:

```yaml
# ~/.crystalyse/config.yaml
model:
  name: "gpt-4"
  temperature: 0.7
  max_tokens: 2000

chemistry_servers:
  creative:
    enabled: true
    port: 8001
    host: "localhost"
  unified:
    enabled: true
    port: 8002
    host: "localhost"
  visualisation:
    enabled: true
    port: 8003
    host: "localhost"

tools:
  rdkit:
    enabled: true
    timeout: 30
  pubchem:
    enabled: true
    rate_limit: 5

memory:
  type: "file"  # or "redis", "postgresql"
  location: "~/.crystalyse/memory"

ui:
  theme: "professional"
  colour: true
  verbose: false
```

## Dependency Management

### Core Dependencies

Crystalyse automatically installs:

- **openai**: OpenAI API client
- **rdkit**: Chemistry toolkit
- **requests**: HTTP client
- **pydantic**: Data validation
- **click**: Command-line interface
- **rich**: Terminal formatting
- **numpy**: Numerical computations
- **matplotlib**: Visualisation

### Optional Dependencies

Install additional features:

```bash

# All extras
pip install "crystalyse[all]"
```

### MCP Server Dependencies

The system uses a hierarchical MCP server architecture:

#### Individual Tool Servers (Required Dependencies)
1. **SMACT MCP Server** (`oldmcpservers/smact-mcp-server`)
   - **Tools**: Composition validation and screening
   - **Used by**: Chemistry Unified Server (rigorous mode)

2. **Chemeleon MCP Server** (`oldmcpservers/chemeleon-mcp-server`)
   - **Tools**: Crystal structure prediction
   - **Used by**: Both chemistry servers (creative and rigorous modes)

3. **MACE MCP Server** (`oldmcpservers/mace-mcp-server`)
   - **Tools**: Formation energy calculations
   - **Used by**: Both chemistry servers (creative and rigorous modes)

#### Unified Servers (Use Individual Tool Servers)
1. **Chemistry Creative Server** (`chemistry-creative-server`)
   - **Tools**: Imports from Chemeleon + MACE servers
   - **Use**: Creative mode (fast exploration)
   - **Dependencies**: chemeleon-mcp-server, mace-mcp-server

2. **Chemistry Unified Server** (`chemistry-unified-server`)
   - **Tools**: Imports from SMACT + Chemeleon + MACE servers
   - **Use**: Rigorous mode (complete validation)
   - **Dependencies**: smact-mcp-server, chemeleon-mcp-server, mace-mcp-server

3. **Visualisation Server** (`visualization-mcp-server`)
   - **Tools**: 3dmol.js integration, Pymatviz analysis plots
   - **Use**: Both modes (3D structures and analysis plots)
   - **Dependencies**: Direct tool imports (not dependent on oldmcpservers)

## Environment Validation

Test your installation:

```bash
# Basic functionality test
crystalyse analyse "test query" --mode creative

# Check help system
crystalyse --help

# View configuration
crystalyse config show
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

# Create conda environment with correct Python version
conda create -n crystalyse python=3.11
conda activate crystalyse
```

#### 2. Installation Failures

```
Error: Failed to install dependencies
```

**Solution:**
```bash
# Use conda environment (recommended)
conda create -n crystalyse python=3.11
conda activate crystalyse

# Clean install
pip install --upgrade pip
pip install -e .
```

#### 3. MCP Server Connection Issues

```
Error: MCP server not found or failed to start
```

**Solution:**
```bash
# Ensure all MCP servers are installed in correct order
# 1. Install individual tool servers first (dependencies)
pip install -e ./oldmcpservers/smact-mcp-server
pip install -e ./oldmcpservers/chemeleon-mcp-server
pip install -e ./oldmcpservers/mace-mcp-server

# 2. Install unified servers (depend on individual servers)
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server

# Test MCP server availability
crystalyse config show
```

#### 4. API Key Issues

```
Error: OpenAI API key not found
```

**Solution:**
```bash
# Set environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Verify API key is set
echo $OPENAI_API_KEY

# Test with simple query
crystalyse analyse "test" --mode creative
```

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

#### 5. Memory Issues

```
Error: Insufficient memory for large molecule analysis
```

**Solution:**
```bash
# Edit ~/.crystalyse/config.yaml
memory:
  max_molecule_size: 1000

# Use batch processing for large datasets
crystalyse batch discover molecules.txt --chunk-size 10
```

### Performance Optimisation

#### 1. Enable Caching

```bash
# Edit ~/.crystalyse/config.yaml
cache:
  enabled: true
  type: "redis"  # or "file"
```

#### 2. Parallel Processing

```bash
# Edit ~/.crystalyse/config.yaml
tools:
  parallel: true
  max_workers: 4
```

#### 3. Resource Monitoring

```bash
# Monitor resource usage
crystalyse monitor --realtime

# View performance statistics
crystalyse stats
```

## Updating

### Regular Updates

```bash
# Update to latest version
pip install --upgrade crystalyse


```

### Development Updates

```bash
# Update development installation
cd crystalyse
git pull origin main
pip install -e ".[dev]"
```

## Uninstallation

### Clean Uninstall

```bash
# Uninstall package
pip uninstall crystalyse

# Remove configuration (optional)
rm -rf ~/.crystalyse

# Remove virtual environment (if used)
rm -rf crystalyse-env
```

### Reset Configuration

```bash
# Reset to defaults
rm ~/.crystalyse/config.yaml
```

## GPU Support (Optional)

### CUDA Installation for MACE Acceleration

For faster MACE energy calculations, install CUDA support:

```bash
# Check for NVIDIA GPU
nvidia-smi

# Install PyTorch with CUDA support
conda activate crystalyse
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Performance with GPU

- **MACE calculations**: 3-5x speedup
- **Large structures**: Up to 10x speedup
- **Batch analysis**: Significant performance improvement

## Development Setup

### Additional Development Tools

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install testing framework
pip install pytest pytest-cov

# Install linting tools
pip install ruff mypy

# Run tests
python -m pytest
python test_session_system.py
```

## Next Steps

After successful installation:

1. **Follow the [Quickstart Guide](../quickstart.md)** - Get started with your first materials analysis
2. **Read the [CLI Usage Guide](cli_usage.md)** - Master the command-line interface
3. **Explore [Analysis Modes](../concepts/analysis_modes.md)** - Understand creative vs rigorous workflows
4. **Study [Tools Documentation](../tools/index.md)** - Learn about SMACT, Chemeleon, MACE, and visualisation tools

## Quick Start Verification

Test your installation with this simple workflow:

```bash
# Set your API key
export OPENAI_API_KEY="sk-your-key-here"

# Test creative mode
crystalyse discover "Find a stable perovskite for solar cells" --mode creative

# Test rigorous mode
crystalyse discover "Analyse CsSnI3 stability" --mode rigorous

# Start interactive session
crystalyse chat -u researcher -s test_session -m creative
```

## Support

If you encounter issues:

1. **Check this troubleshooting section** for common solutions
2. **Review the [CLI Usage Guide](cli_usage.md)** for command examples
3. **Check the GitHub repository** for known issues
4. **Create a detailed issue report** with:
   - Python version (`python --version`)
   - Installation method used
   - Error messages
   - Configuration file content (`~/.crystalyse/config.yaml`)