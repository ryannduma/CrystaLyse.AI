# Render Gate System Documentation

## Overview

The Render Gate is an intelligent anti-hallucination system for CrystaLyse that detects unprovenanced material property claims while ignoring legitimate contextual information, derived calculations, and literature references. This system implements the concepts described in the CrystaLyse paper with enhanced intelligent classification.

!!! warning "Detect-and-log, not block"
    In the current implementation the gate does not modify, redact or withhold anything.
    `_process_text` counts and logs each flagged value and returns the text unchanged —
    the code carries a `TODO: Implement actual text replacement`. Treat the gate as an
    audit signal: it tells you a number lacked provenance, it does not stop the number
    from reaching the user.

## Key Concepts

### 1. Provenance Tuples
Every material property value should have a provenance tuple:
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
   - Two or more derived-value indicators in the surrounding text, or a mathematical
     expression with digits on both sides of the operator
   - Example: "The difference between 2 and 5 gives 3"

4. **STATISTICAL**: Counts, percentages, and summaries
   - Analysis results and screening outcomes
   - Example: "5 out of 10 structures were stable"

5. **CONTEXTUAL**: General explanatory or typical values
   - Educational content and general knowledge
   - Example: "Perovskites typically have tolerance factors 0.8-1.0"

6. **UNKNOWN**: Values that need further analysis

Only MATERIAL_PROPERTY values are looked up in the registry; every other class is left
alone.

## Architecture

### Components

```
dev/crystalyse/provenance/
├── artifact_tracker.py      # Tracks computational artifacts
├── value_registry.py        # Central provenance registry
├── render_gate.py           # Intelligent classification and detection
├── core/                    # Shared provenance models
├── handlers/                # Trace handlers that register tool outputs
└── integration/             # Wiring helpers
```

### Data Flow

1. **Tool Execution** → Artifacts registered with hashes
2. **Value Extraction** → Numerical values extracted and indexed
3. **LLM Response** → Output analyzed for numerical claims
4. **Classification** → Each number classified by type
5. **Provenance Check** → Material properties verified against registry
6. **Reporting** → Unprovenanced material properties flagged, counted and logged

## Configuration

### Environment Variables

Two variables are actually read by the code:

```bash
# Enable/disable render gate (default: true)
CRYSTALYSE_RENDER_GATE=true

# Log a warning when violations are detected (default: true)
CRYSTALYSE_RENDER_GATE_LOG=true
```

Two more are parsed into `config.render_gate` but never consumed anywhere, so setting
them has no effect today:

```bash
CRYSTALYSE_RENDER_GATE_STRICTNESS=intelligent   # read, never used
CRYSTALYSE_BLOCK_UNPROVENANCED=true             # read, never used
```

### Config File

The render gate is environment-variable-only. Project configuration lives in
`.crystalyse/config.toml` (project) over `~/.crystalyse/config.toml` (user) over the
`CrystalyseSettings` defaults, and that dataclass has no `render_gate` field. There is no
YAML configuration anywhere in the package.

## Usage

### Where It Runs

The gate runs in exactly one place: at the end of `EnhancedCrystaLyseAgent.discover()`,
guarded by `config.render_gate["enabled"]`:

```python
gate = IntelligentRenderGate(provenance_tracker=get_global_registry())
processed_response, detected_numbers, has_violations = gate.analyze_output(final_response)
```

Its outcome is attached to the result dictionary:

```python
result["render_gate"] = {
    "enabled": True,
    "violations_detected": has_violations,
    "blocked_count": gate.blocked_count,
    "allowed_count": gate.allowed_count,   # always 0, see Statistics
}
```

Because `crystalyse chat` calls the same `discover()`, both the chat and discovery paths
are covered.

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
# processed == response; inspect `detected` and `has_violations` for the findings
```

### In CLI Modes

The render gate is active in every command that runs a discovery:

```bash
# Discovery - render gate active
crystalyse discover "What is the formation energy of LiCoO2?"

# Chat - render gate active (same discover() path)
crystalyse chat -u user -s session

# Inspect a captured session afterwards
crystalyse analyse-provenance --latest
```

Modes are `explore`, `validate` and `auto`; `creative`, `rigorous` and `adaptive` still
resolve with a `DeprecationWarning`. There is no `analyze` command, and `discover` takes
a query string rather than a file path.

## Intelligent Classification

### Material Property Detection

The system recognizes 73 material-property keyword entries, counting underscore and
space spellings of the same term (`formation_energy` / `formation energy`) and unit
strings such as `eV/atom`:

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

Classification thresholds matter: LITERATURE needs two indicators (or a database id like
`MP-`), DERIVED needs two indicators (or a mathematical expression), while a single
STATISTICAL indicator is enough. Words such as "total", "count", "stable" and "materials"
are STATISTICAL indicators, so a sentence containing them is classified as statistical
before any material-property check runs.

## Examples

### What Gets Flagged

```python
# Unprovenanced material property claims
"The formation energy is -3.456 eV/atom"  # No calculation performed
"Band gap: 2.1 eV"  # No source or calculation
"Lattice parameter = 3.89 Å"  # No provenance

# Each of these logs a warning, increments blocked_count and sets
# violations_detected -- the response text itself is returned unchanged
```

### What Gets Allowed

```python
# ✅ Provenanced values (from actual calculations)
"The band gap is 3 eV"  # matched, if 3 is registered

# ✅ Literature references
"According to Materials Project (MP-19009), band gap is 2.0 eV"
"ICSD-51688 reports lattice parameter of 2.816 Å"

# ✅ Derived calculations
"The difference between 4 Li atoms and 2 gives 2"

# ✅ Statistical summaries
"5 out of 10 structures were stable"
"75% passed stability criteria"

# ✅ Contextual information
"Perovskites typically have tolerance factors 0.8-1.0"
"Battery cathodes usually operate around 3.7 V"
```

Note that "Total energy = -2.345 + (-1.234) = -3.579 eV" is allowed, but as STATISTICAL
rather than DERIVED: "total" is a statistical indicator, and the mathematical-expression
patterns need digits immediately either side of the operator, which the decimal-split
tokens do not provide.

A registered *decimal* value is a different matter. Detection splits the text on `.`, so
"-2.345 eV/atom" is examined as the tokens "-2" and "345 eV"; neither matches the
registered `-2.345` within the tolerance the gate uses, and a correctly provenanced
decimal is flagged anyway. Verified by registering
`{"formation_energy": -2.345}` and analysing "MACE calculated formation energy:
-2.345 eV/atom": `has_violations` is `True`. Integer values match as expected.

## Testing

There is currently no automated test coverage for the render gate: `dev/tests/` (unit,
integration, contract, mcp_servers) contains no render-gate tests, and the demo scripts
earlier documented here do not exist. To exercise it, drive it directly:

```python
from crystalyse.provenance.render_gate import IntelligentRenderGate

gate = IntelligentRenderGate()
for text in ["The formation energy is -3.456 eV/atom", "5 out of 10 were stable"]:
    processed, detected, violations = gate.analyze_output(text)
    print(violations, [(d.value, d.number_type) for d in detected])
```

### Paper Claims

The following are claims from the CrystaLyse paper, not measurements of this
implementation:

- **Baseline**: 14% unprovenanced material properties
- **With Render Gate**: 0% unprovenanced material properties
- **Contextual values preserved**: 100%
- **False positive rate**: < 5%

No benchmark in the repository reproduces these figures, and the 0% claim describes
behaviour the current detect-and-log implementation does not provide.

## Monitoring

### Violation Logs

Detection logs a warning from `crystalyse.provenance.render_gate`:

```
WARNING:crystalyse.provenance.render_gate:Unprovenanced material property detected: -3
  in context: 'The formation energy is -3'
```

followed by an info line per flagged value:

```
INFO:crystalyse.provenance.render_gate:[BLOCKED] Unprovenanced material property: -3
```

When `log_violations` is enabled the agent adds one summary warning per run: "Render gate
detected unprovenanced material properties".

### Statistics

```python
gate.get_statistics()
# Returns:
{
    "blocked_count": 5,
    "allowed_count": 0,          # never incremented anywhere; always 0
    "blocked_values": ["-3", "2", ...]   # the matched token strings, not floats
}
```

## Future Enhancements

1. **Actual gating**: implement the text replacement the code marks as TODO
2. **Confidence Scores**: Add confidence levels to classifications
3. **User Feedback Loop**: Learn from user corrections
4. **Cross-session Learning**: Share provenance across sessions
5. **Explain Decisions**: Provide explanations for flagged values
6. **Custom Rules**: User-defined classification rules

## Troubleshooting

### Common Issues

1. **Values not being found in registry**
   - The gate always calls `lookup_provenance(..., tolerance=0.001)`, ignoring the
     method's own default of `0.01`
   - Number detection splits text on `.`, so "-3.456 eV/atom" is examined as the separate
     tokens "-3" and "456 eV"; the value looked up is not the one you wrote
   - For any `|value| < 0.01` the registry widens the window to ±0.5 and returns the first
     candidate even when the material does not match, so near-zero values can match the
     wrong record
   - Digits inside chemical formulas are detected as numbers too: "LiCoO2" contributes a
     `2` that can be classified as a material property and flagged
   - Verify tool output registration and material context extraction

2. **False positives (values flagged although legitimate)**
   - Review classification logic and indicator thresholds
   - Add more context indicators
   - Check for literature patterns

3. **False negatives (values not flagged)**
   - Add material property keywords
   - Check whether a STATISTICAL indicator is short-circuiting the classification
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
    def __init__(self, provenance_tracker=None):
        """provenance_tracker is a ProvenanceValueRegistry."""

    def analyze_output(
        self, text: str, provenance_data: dict | None = None
    ) -> tuple[str, list[DetectedNumber], bool]:
        """Analyze LLM output for numerical claims.

        Returns (processed_text, detected_numbers, has_violations).
        processed_text is currently always the input text unchanged.
        """

    def get_statistics(self) -> dict:
        """Get render gate statistics."""
```

### ProvenanceValueRegistry

```python
class ProvenanceValueRegistry:
    def register_tool_output(
        self, tool_name, tool_call_id, input_data, output_data, timestamp=None
    ) -> str:
        """Register a tool output, extract values, return the artifact id."""

    def lookup_provenance(self, value, tolerance=0.01, material=None):
        """Find provenance for a numerical value.

        Below |value| < 0.01 the tolerance is widened to 0.5 internally.
        """

    def lookup_material_properties(self, material: str) -> dict:
        """Get all provenanced properties for a material."""
```

## Best Practices

1. **Always register tool outputs** immediately after execution
2. **Include material context** when looking up provenance
3. **Monitor violation logs** to tune classification
4. **Read `result["render_gate"]`** in automation rather than assuming the text was cleaned
5. **Test with representative queries** before deployment

## Conclusion

The Render Gate provides an audit signal for material property hallucination: it
distinguishes between types of numerical claim and reports which material properties
reached the user without provenance. Enforcement — removing or annotating those values in
the response — remains to be implemented.
