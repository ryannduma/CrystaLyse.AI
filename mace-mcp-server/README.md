# MACE MCP Server for CrystaLyse.AI

Production-ready MACE force field calculations for materials discovery via Model Context Protocol (MCP).

## Features

### Core Capabilities
- **Energy Calculations**: Single-point energy with uncertainty quantification
- **Structure Relaxation**: With detailed convergence monitoring  
- **Formation Energy**: Stability analysis from elemental references
- **Chemical Substitutions**: Energy-guided substitution suggestions
- **Phonon Calculations**: Dynamical stability assessment
- **Active Learning**: Uncertainty + diversity-based target identification
- **Batch Processing**: Adaptive resource-aware batch processing
- **Descriptor Extraction**: Comprehensive structural descriptors

### Production Features
- **Resource Monitoring**: Real-time CPU, memory, and GPU metrics
- **Error Handling**: Robust validation and graceful failure recovery
- **Model Caching**: Automatic caching for performance optimisation
- **Uncertainty Quantification**: Committee models for prediction confidence
- **Adaptive Batching**: Dynamic batch size adjustment based on system resources

## Installation

### Prerequisites
```bash
# Python 3.8+ required
python --version

# Install base dependencies
pip install torch>=1.12.0 ase>=3.22.0 numpy>=1.21.0 scipy>=1.7.0
```

### Install MACE
```bash
# Install MACE force field package
pip install mace-torch

# Or install from source for latest features
git clone https://github.com/ACEsuit/mace.git
cd mace && pip install .
```

### Install MCP Framework
```bash
# Install Model Context Protocol
pip install mcp
```

### Install MACE MCP Server
```bash
# From CrystaLyse.AI repository
cd CrystaLyse.AI/mace-mcp-server
pip install -e .

# Or install optional GPU monitoring
pip install -e .[gpu]
```

## Testing

### Offline Tests (No MACE Required)
```bash
cd mace-mcp-server
python test_server_offline.py
```

### Full Tests (MACE Required)
```bash
python test_server.py
```

## Usage

### Start the Server
```bash
# Command line
mace-mcp

# Or as Python module
python -m mace_mcp

# Or with custom settings
python -c "from mace_mcp.server import main; main()"
```

### Available Tools

#### 1. Resource Monitoring
```python
get_server_metrics()
# Returns: CPU, memory, GPU usage, model cache stats
```

#### 2. Energy Calculations
```python
calculate_energy(structure_dict, model_type="mace_mp", size="medium")
# Returns: Energy, forces, stress tensor

calculate_energy_with_uncertainty(structure_dict, committee_size=5)
# Returns: Energy with uncertainty estimation for active learning
```

#### 3. Structure Relaxation
```python
relax_structure(structure_dict, fmax=0.01, optimiser="BFGS")
# Returns: Relaxed structure, energy change, convergence info

relax_structure_monitored(structure_dict, monitor_interval=10)
# Returns: Detailed convergence trajectory and analysis
```

#### 4. Formation Energy & Stability
```python
calculate_formation_energy(structure_dict, element_references=None)
# Returns: Formation energy and stability assessment
```

#### 5. Chemical Substitutions
```python
suggest_substitutions(structure_dict, target_elements=None, max_suggestions=5)
# Returns: Ranked substitution suggestions with energy changes
```

#### 6. Phonon Analysis
```python
calculate_phonons_supercell(structure_dict, supercell_size=[2,2,2])
# Returns: Phonon frequencies and dynamical stability
```

#### 7. Active Learning
```python
identify_active_learning_targets(structure_list, uncertainty_threshold=0.05)
# Returns: Structures ranked by uncertainty and diversity
```

#### 8. Batch Processing
```python
batch_energy_calculation(structure_list, include_forces=True)
# Returns: Fast batch energy calculations

adaptive_batch_calculation(structure_list, memory_limit_gb=8.0)
# Returns: Resource-aware adaptive batch processing
```

#### 9. Descriptor Extraction
```python
extract_descriptors_robust(structure_dict, descriptor_types=None)
# Returns: Comprehensive structural descriptors for ML
```

## Integration with CrystaLyse.AI

### Structure Format
All tools expect structures in this format:
```python
structure_dict = {
    "numbers": [3, 9],  # Atomic numbers
    "positions": [[0.0, 0.0, 0.0], [2.0, 2.0, 2.0]],  # Cartesian coordinates
    "cell": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]],  # Unit cell
    "pbc": [True, True, True]  # Periodic boundary conditions (optional)
}
```

### Integration Example
```python
# From Chemeleon CSP output to MACE analysis
chemeleon_structure = get_structure_from_chemeleon()
mace_energy = calculate_energy(chemeleon_structure)
mace_relaxed = relax_structure(chemeleon_structure)
mace_stability = calculate_formation_energy(mace_relaxed["relaxed_structure"])
```

### Multi-fidelity Workflow
```python
# 1. Fast MACE screening
structures = get_candidate_structures()
energies = batch_energy_calculation(structures)

# 2. Uncertainty-based filtering  
uncertain = identify_active_learning_targets(structures)
high_priority = [s for s in uncertain["recommended_targets"] 
                if s["recommendation"] == "high_priority"]

# 3. Route high-uncertainty to DFT
for structure in high_priority:
    if structure["uncertainty"] > 0.1:
        submit_to_dft_queue(structure)
```

## Performance

### Benchmarks
- **Single Energy**: ~0.1-1s per structure (GPU) / ~1-10s (CPU)
- **Batch Processing**: 100-1000+ structures/minute (depending on size)
- **Memory Usage**: ~500MB-2GB per cached model
- **Accuracy**: Within ~1-10 meV/atom of DFT (depending on system)

### Model Options
- **mace_mp** (Materials Project): General materials, 89 elements
- **mace_off** (Organic molecules): C, H, N, O focused  
- **Custom models**: Load your own trained MACE models

## Configuration

### Model Settings
```python
# High-accuracy mode
calculator = get_mace_calculator(
    model_type="mace_mp", 
    size="large",
    device="cuda",
    default_dtype="float64"
)

# Fast screening mode  
calculator = get_mace_calculator(
    model_type="mace_mp",
    size="small", 
    device="cuda",
    default_dtype="float32"
)
```

### Resource Limits
```python
# Adaptive batching settings
adaptive_batch_calculation(
    structures,
    initial_batch_size=20,
    memory_limit_gb=8.0,
    calculation_type="energy"
)
```

## Development

### Project Structure
```
mace-mcp-server/
├── pyproject.toml          # Project configuration
├── README.md               # This file
├── test_server_offline.py  # Offline tests
├── test_server.py          # Full tests
└── src/mace_mcp/
    ├── __init__.py         # Package initialization
    ├── __main__.py         # Module entry point
    ├── server.py           # FastMCP server setup
    └── tools.py            # Tool implementations
```

### Adding New Tools
1. Add tool function to `tools.py` with `@mcp.tool` decorator
2. Follow existing patterns for validation and error handling
3. Return JSON string with comprehensive results
4. Add tests to verify functionality

### Debugging
```bash
# Enable debug logging
export MACE_MCP_LOG_LEVEL=DEBUG
python -m mace_mcp

# Check tool registration
python -c "from mace_mcp.server import mcp; print([t.name for t in mcp.get_tools()])"
```

## Contributing

1. Follow existing code patterns and documentation style
2. Add comprehensive error handling and validation  
3. Include tests for new functionality
4. Update this README for new features

## License

Part of CrystaLyse.AI - Advanced materials discovery platform.

## Related

- [MACE Force Fields](https://github.com/ACEsuit/mace)
- [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk)
- [ASE - Atomic Simulation Environment](https://wiki.fysik.dtu.dk/ase/)
- [CrystaLyse.AI Main Repository](../README.md)