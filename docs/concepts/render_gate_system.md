# Render Gate System Documentation

## Overview

The Render Gate is an intelligent anti-hallucination system for CrystaLyse that prevents the generation of unprovenanced material property claims while allowing legitimate contextual information, derived calculations, and literature references. This system implements the concepts described in the CrystaLyse paper with enhanced intelligent classification.

## Key Concepts

### 1. Provenance Tuples
Every material property value must have a provenance tuple:
```
(value, unit, source_tool, artifact_hash, timestamp)
```

- **value**: The numerical value (e.g., -2.345)
- **unit**: Unit of measurement (e.g., "eV/atom")
- **source_tool**: Tool that generated it (e.g., "calculate_formation_energy")
- **artifact_hash**: SHA256 hash of the computational output
- **timestamp**: ISO timestamp of calculation

### 2. Number Classification

The render gate classifies numerical values into six categories:

1. **MATERIAL_PROPERTY**: Specific material properties that MUST have provenance
   - Formation energy, band gap, lattice parameters, bulk modulus, etc.
   - Example: "The formation energy is -3.456 eV/atom"

2. **LITERATURE**: Values from published sources with attribution
   - References to databases (Materials Project, ICSD, COD)
   - Citations to papers or research
   - Example: "According to MP-19009, the band gap is 2.0 eV"

3. **DERIVED**: Values calculated from provenanced sources
   - Mathematical operations on known values
   - Arithmetic expressions and formulas
   - Example: "Total energy = -2.345 + (-1.234) = -3.579 eV"

4. **STATISTICAL**: Counts, percentages, and summaries
   - Analysis results and screening outcomes
   - Example: "5 out of 10 structures were stable"

5. **CONTEXTUAL**: General explanatory or typical values
   - Educational content and general knowledge
   - Example: "Perovskites typically have tolerance factors 0.8-1.0"

6. **UNKNOWN**: Values that need further analysis

## Architecture

### Components

```
render_gate/
├── artifact_tracker.py      # Tracks computational artifacts
├── value_registry.py        # Central provenance registry
└── render_gate.py          # Intelligent classification and gating
```

### Data Flow

1. **Tool Execution** → Artifacts registered with hashes
2. **Value Extraction** → Numerical values extracted and indexed
3. **LLM Response** → Output analyzed for numerical claims
4. **Classification** → Each number classified by type
5. **Provenance Check** → Material properties verified against registry
6. **Gating Decision** → Block unprovenanced material properties

## Configuration

### Environment Variables

```bash
# Enable/disable render gate
CRYSTALYSE_RENDER_GATE=true

# Strictness level: intelligent, strict, permissive
CRYSTALYSE_RENDER_GATE_STRICTNESS=intelligent

# Log violations for monitoring
CRYSTALYSE_RENDER_GATE_LOG=true

# Block unprovenanced values (vs just warning)
CRYSTALYSE_BLOCK_UNPROVENANCED=true
```

### Config File (config.yaml)

```yaml
render_gate:
  enabled: true
  strictness: intelligent
  log_violations: true
  block_unprovenanced: true
```

## Usage

### Basic Integration

```python
from crystalyse.provenance.render_gate import IntelligentRenderGate
from crystalyse.provenance.value_registry import get_global_registry

# Get the global registry
registry = get_global_registry()

# Register tool outputs
registry.register_tool_output(
    tool_name="calculate_formation_energy",
    tool_call_id="call_123",
    input_data={"structure": "LiCoO2"},
    output_data={"formation_energy": -2.345, "unit": "eV/atom"}
)

# Create render gate with registry
gate = IntelligentRenderGate(provenance_tracker=registry)

# Analyze LLM output
response = "The formation energy is -2.345 eV/atom"
processed, detected, has_violations = gate.analyze_output(response)
```

### In CLI Modes

The render gate is automatically integrated into all CLI modes:

```bash
# Discovery mode - render gate active
crystalyse discover "What is the formation energy of LiCoO2?"

# Chat mode - render gate active
crystalyse chat -u user -s session

# Analysis mode - render gate active
crystalyse analyze structure.cif --mode rigorous
```

## Intelligent Classification

### Material Property Detection

The system recognizes ~50+ material property keywords:

- **Energy**: formation_energy, binding_energy, cohesive_energy, etc.
- **Electronic**: band_gap, HOMO, LUMO, fermi_level, work_function
- **Structural**: lattice_parameter, space_group, cell_volume, density
- **Mechanical**: bulk_modulus, young_modulus, hardness, stress, strain
- **Thermodynamic**: melting_point, heat_capacity, entropy, enthalpy
- **Electrochemical**: voltage, capacity, coulombic_efficiency

### Context Analysis

The system analyzes surrounding text for context clues:

```python
CONTEXTUAL_INDICATORS = {
    'typically', 'usually', 'generally', 'approximately',
    'roughly', 'around', 'often', 'commonly', 'tend to',
    'literature', 'reported', 'known', 'established'
}

DERIVED_INDICATORS = {
    'calculated from', 'derived from', 'based on calculation',
    'sum of', 'difference between', 'product of', 'times'
}

LITERATURE_INDICATORS = {
    'Materials Project', 'MP-', 'ICSD', 'according to',
    'reported in', 'published', 'et al.', 'journal'
}
```

## Examples

### What Gets Blocked

```python
# ❌ Unprovenanced material property claims
"The formation energy is -3.456 eV/atom"  # No calculation performed
"Band gap: 2.1 eV"  # No source or calculation
"Lattice parameter = 3.89 Å"  # No provenance

# These trigger warnings and can be blocked
```

### What Gets Allowed

```python
# ✅ Provenanced values (from actual calculations)
"MACE calculated formation energy: -2.345 eV/atom"  # If -2.345 in registry

# ✅ Literature references
"According to Materials Project (MP-19009), band gap is 2.0 eV"
"ICSD-51688 reports lattice parameter of 2.816 Å"

# ✅ Derived calculations
"Total energy = -2.345 + (-1.234) = -3.579 eV"
"The sum of 4 Li atoms at 6.94 g/mol gives 27.76 g/mol"

# ✅ Statistical summaries
"5 out of 10 structures were stable"
"75% passed stability criteria"

# ✅ Contextual information
"Perovskites typically have tolerance factors 0.8-1.0"
"Battery cathodes usually operate around 3.7 V"
```

## Testing

### Run Tests

```bash
# Basic render gate demo
python dev/test_render_gate_demo.py

# Integration tests
python dev/test_render_gate_integration.py

# Enhanced classification tests
python dev/test_enhanced_render_gate.py
```

### Validation Metrics

Based on the CrystaLyse paper claims:

- **Baseline**: 14% unprovenanced material properties
- **With Render Gate**: 0% unprovenanced material properties
- **Contextual values preserved**: 100%
- **False positive rate**: < 5%

## Performance Impact

- **Latency**: < 10ms per response analysis
- **Memory**: ~100MB for typical session (10k values)
- **CPU**: Negligible (regex and dictionary lookups)

## Monitoring

### Violation Logs

When violations are detected, they are logged:

```
WARNING:render_gate:Unprovenanced material property detected: 3.456
  in context: 'The formation energy is -3.456 eV/atom'
```

### Statistics

```python
gate.get_statistics()
# Returns:
{
    "blocked_count": 5,
    "allowed_count": 42,
    "blocked_values": [3.456, 2.1, ...]
}
```

## Future Enhancements

1. **Confidence Scores**: Add confidence levels to classifications
2. **User Feedback Loop**: Learn from user corrections
3. **Cross-session Learning**: Share provenance across sessions
4. **Explain Decisions**: Provide explanations for blocks
5. **Custom Rules**: User-defined classification rules

## Troubleshooting

### Common Issues

1. **Values not being found in registry**
   - Check tolerance settings (default 0.001)
   - Verify tool output registration
   - Check material context extraction

2. **False positives (blocking legitimate values)**
   - Review classification logic
   - Add more context indicators
   - Check for literature patterns

3. **False negatives (allowing hallucinations)**
   - Add material property keywords
   - Tighten classification rules
   - Review provenance lookup logic

### Debug Mode

```python
import logging
logging.getLogger('crystalyse.provenance').setLevel(logging.DEBUG)
```

## API Reference

### IntelligentRenderGate

```python
class IntelligentRenderGate:
    def analyze_output(text: str) -> Tuple[str, List[DetectedNumber], bool]:
        """Analyze LLM output for numerical claims."""

    def get_statistics() -> Dict:
        """Get render gate statistics."""
```

### ProvenanceValueRegistry

```python
class ProvenanceValueRegistry:
    def register_tool_output(tool_name, tool_call_id, input_data, output_data):
        """Register a tool output and extract values."""

    def lookup_provenance(value, tolerance=0.01, material=None):
        """Find provenance for a numerical value."""

    def lookup_material_properties(material: str) -> Dict:
        """Get all provenanced properties for a material."""
```

## Best Practices

1. **Always register tool outputs** immediately after execution
2. **Use appropriate tolerance** for fuzzy matching (0.001-0.01)
3. **Include material context** when looking up provenance
4. **Monitor violation logs** to tune classification
5. **Test with representative queries** before deployment

## Conclusion

The Render Gate system provides intelligent protection against material property hallucination while preserving natural conversational flow. By distinguishing between different types of numerical claims, it maintains scientific rigor without compromising user experience.