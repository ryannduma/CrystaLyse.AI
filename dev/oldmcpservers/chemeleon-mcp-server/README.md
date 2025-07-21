# Chemeleon MCP Server

MCP (Model Context Protocol) server for Chemeleon crystal structure prediction models.

## Features

- **Crystal Structure Prediction (CSP)**: Generate crystal structures from chemical formulas
- **Structure Analysis**: Analyse generated structures for symmetry and properties
- **Model Management**: Cache models for efficient reuse
- **CPU-Optimised**: Runs efficiently on CPU by default (GPU optional)

## Installation

```bash
# Navigate to the chemeleon-mcp-server directory
cd /home/ryan/crystalyseai/CrystaLyse.AI/chemeleon-mcp-server

# Install with pip (using conda environment 'perry')
conda activate perry
pip install -e .
```

## Usage

### As a standalone server

```bash
# Run the server directly
python -m chemeleon_mcp

# Or use the installed command
chemeleon-mcp
```

### With CrystaLyse.AI agent

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    name="Chemeleon CSP",
    params={
        "command": "python",
        "args": ["-m", "chemeleon_mcp"],
    },
) as server:
    agent = Agent(
        name="Materials Designer",
        instructions="Use Chemeleon to generate crystal structures",
        mcp_servers=[server],
    )
    
    result = await Runner.run(
        starting_agent=agent,
        input="Generate a crystal structure for NaCl"
    )
```

## Available Tools

### `generate_crystal_csp`
Generate crystal structures from chemical formulas using Crystal Structure Prediction.

**Parameters:**
- `formulas`: Chemical formula(s) to generate structures for
- `num_samples`: Number of structures to generate per formula (default: 1)
- `batch_size`: Batch size for generation (default: 16)
- `output_format`: Output format - "cif" (default), "dict", or "both"
- `checkpoint_path`: Optional path to custom checkpoint
- `prefer_gpu`: If True, use GPU if available. Otherwise use CPU (default: False)

### `analyse_structure`
Analyse a generated crystal structure.

**Parameters:**
- `structure_dict`: Structure dictionary from generation
- `calculate_symmetry`: Whether to calculate space group (default: True)
- `tolerance`: Tolerance for symmetry analysis (default: 0.1)

### `get_model_info`
Get information about available Chemeleon models and benchmarks.

### `clear_model_cache`
Clear all cached models from memory.

## Model Checkpoints

The server automatically downloads the required CSP model checkpoint on first use (~1GB).

Models are cached in memory for efficient reuse.

## Requirements

- Python 3.11+
- PyTorch 2.0+
- CUDA (optional, for GPU acceleration)
- ~4GB disk space for model checkpoints
- ~4GB RAM for model inference

## License

MIT License