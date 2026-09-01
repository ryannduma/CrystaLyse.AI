# Tool Integration

## Overview

Crystalyse's tool system provides agents with access to specialised materials science software, databases, and computational resources. The modular architecture allows seamless integration of diverse materials design tools through standardised Model Context Protocol (MCP) interfaces.

## Tool Architecture

### Tool Framework

```
┌─────────────────────────────────────────┐
│      EnhancedCrystaLyseAgent            │
│      (OpenAI Agents SDK runner)         │
├─────────────────────────────────────────┤
│  Workspace tools (in-process)           │
│  read_file · write_file · list_files    │
├─────────────────────────────────────────┤
│  MCP servers (stdio subprocesses)       │
│  ┌──────────────────┐ ┌──────────────┐  │
│  │ chemistry server │ │ visualization│  │
│  │ (mode-selected)  │ │  (always)    │  │
│  └──────────────────┘ └──────────────┘  │
├─────────────────────────────────────────┤
│  crystalyse.tools                       │
│  SMACT · Chemeleon · MACE · pymatgen ·  │
│  pymatviz wrappers                      │
└─────────────────────────────────────────┘
```

Exactly two MCP servers run per discovery: the chemistry server the mode selects, plus the visualisation server. Both are launched as stdio subprocesses with `MCPServerStdio` and shut down when the run finishes.

The servers are thin MCP wrappers: `chemistry_unified.server` imports its calculators
(`SMACTValidator`, `ChemeleonPredictor`, `MACECalculator`, `PyMatgenAnalyzer`, ...) and its
result models from the `crystalyse.tools` package, so the science lives in the package and
the server only exposes it.

### Tool Categories

#### 1. Core Materials Tools
- **SMACT**: Composition validation and screening
- **Chemeleon**: Crystal structure prediction
- **MACE**: Machine learning force fields
- **pymatgen**: Symmetry, coordination and hull analysis
- **Visualisation Suite**: CIF output plus pymatviz analysis plots

#### 2. MCP Server Architecture
- **chemistry_creative** (`chemistry-creative-server`): fast structure generation (Chemeleon + MACE), 4 tools
- **chemistry_unified** (`chemistry-unified-server`): complete validation (SMACT + Chemeleon + MACE + pymatgen), 20 tools
- **visualization** (`visualization-mcp-server`): CIF output and pymatviz analysis plots, 5 tools

These three are the only MCP servers in the repository, and all three are declared in `CrystaLyseConfig.mcp_servers`.

#### 3. Computational Framework
- **OpenAI Agents SDK**: Production-ready agent architecture
- **Multi-provider model registry**: OpenAI, Anthropic, OpenRouter, Mistral and local Ollama backbones (see [Model Selection](#model-selection))
- **Model Context Protocol**: Seamless tool integration
- **Provenance capture**: MCP tool outputs are hashed and indexed in a value registry; the [render gate](render_gate_system.md) then detects and logs unprovenanced material-property numbers
- **Session Management**: Persistent conversation memory via the SDK's `SQLiteSession`

#### 4. External Integration Capability
- **CIF File Support**: Standard crystallographic format, written to your working directory
- **Analysis PDFs**: Four pymatviz plots per material (3D structure, XRD, RDF, coordination)
- **Provenance artefacts**: `events.jsonl`, `materials_catalog.json` and `summary.json` per session
- **Platforms**: developed and tested on Python 3.12; CI covers Linux (3.11, 3.12) and macOS (3.11). Windows is not tested.

## Built-in Tools

### SMACT Integration

Accessed through the chemistry_unified server for composition validation:

```python
# Available through MCP server calls
# SMACT validates compositions based on chemical principles

# MCP tool signature (chemistry_unified)
validate_composition(
    composition="CsSnI3",
    use_pauling_test=True,
    include_alloys=True,
    oxidation_states_set="icsd24",
)

# SMACT screening pipeline:
# 1. Charge neutrality
# 2. Pauling electronegativity rules
# 3. Valid oxidation state combinations

# Output: ValidationResult with per-rule detail
```

Related SMACT-backed tools on the same server: `analyze_stability`, `predict_band_gap`,
`smact_validate_fast`, `filter_compositions`, `predict_dopants`, `generate_ml_representation`.

### Chemeleon Integration

Accessed through both chemistry servers for crystal structure prediction:

```python
# chemistry_creative (fast exploration)
generate_crystal_structure(formula="CaTiO3", num_samples=3, prefer_gpu=True)

# chemistry_unified (validation runs)
generate_crystal_csp(formulas="CaTiO3", num_samples=1, prefer_gpu=True)

# Chemeleon pipeline:
# 1. Composition analysis
# 2. Diffusion-model structure generation

# Output: Multiple candidate structures, convertible to CIF
```

Model checkpoints download automatically from Figshare to
`~/.cache/crystalyse/chemeleon_checkpoints/` (~604 MB) on first use.

### MACE Integration

Accessed through both chemistry servers for energy calculations:

```python
# chemistry_unified: takes a structure dict (numbers, positions, cell, pbc)
calculate_formation_energy(structure_dict, model_type="mace_mp", size="medium")

# chemistry_creative: takes CIF content directly
calculate_formation_energy(cif_content, prefer_gpu=True)

# MACE pipeline:
# 1. Structure input
# 2. ML force field inference
# 3. Formation and total energy output

# Output: EnergyResult with formation_energy, total_energy and metadata
```

MACE foundation models cache in `~/.cache/mace/`. Related tools: `relax_structure`,
`calculate_stress`, `fit_equation_of_state`, `list_foundation_models`.

Hull-based stability (`calculate_energy_above_hull`) uses phase-diagram data that
auto-downloads to `~/.cache/crystalyse/` (~178 MB, 271617 entries).

## MCP Server Integration

### Visualisation Server Integration

Accessed through the visualization MCP server for CIF output and analysis plots:

```python
# Save the structure as a CIF file in the working directory
create_3dmol_visualization(cif_content, formula, output_dir)
# note: "3dmol.js visualization disabled for v2.0-alpha - CIF file provided instead"

# Full analysis suite
create_pymatviz_analysis_suite(cif_content, formula, output_dir)

# Writes into <output_dir>/<formula>_analysis/:
#   <formula>.cif
#   3D_Structure_<formula>.pdf
#   XRD_Pattern_<formula>.pdf
#   RDF_Analysis_<formula>.pdf
#   Coordination_Analysis_<formula>.pdf
```

Interactive 3dmol.js output is disabled: `create_3dmol_visualization` writes the CIF
file and nothing else. The config defaults match (`enable_html=false`, `cif_only=true`,
overridable with `CRYSTALYSE_ENABLE_HTML_VIZ` and `CRYSTALYSE_CIF_ONLY`). Existing
outputs are reused rather than regenerated, so repeated runs on the same formula are cheap.

The convenience wrappers `create_creative_visualization` (CIF only),
`create_rigorous_visualization` (CIF plus the pymatviz suite) and
`create_mode_aligned_visualization` still take the pre-rename mode words
(`"creative"`, `"rigorous"`, `"adaptive"`) as tool arguments, even though the
user-facing modes are now `explore`, `validate` and `auto`.

### Complete Analysis Workflow

Integrated pipeline using all available tools:

```python
from crystalyse import EnhancedCrystaLyseAgent

# validate mode (complete validation):
# 1. SMACT composition validation
# 2. Chemeleon structure generation
# 3. MACE energy calculations
# 4. Visualisation with the pymatviz analysis suite

agent = EnhancedCrystaLyseAgent(mode="validate")
result = await agent.discover("Design a perovskite solar cell material")

# explore mode (fast exploration):
# 1. Chemeleon structure generation
# 2. MACE energy calculations
# 3. CIF output

agent = EnhancedCrystaLyseAgent(mode="explore")
result = await agent.discover("Design a perovskite solar cell material")
```

`discover(query, history=None, trace_handler=None)` is the agent's only public entry
point; it returns a dict with `status`, `query`, `response`, `render_gate` and, when
provenance capture succeeds, `provenance`.

### MCP Server Architecture

Every server is a stdio subprocess described by `command`, `args` and `cwd` — there is
no host, port or HTTP listener:

```python
# CrystaLyseConfig.mcp_servers
{
    "chemistry_unified": {
        "command": os.getenv("CRYSTALYSE_PYTHON_PATH", sys.executable),
        "args": ["-m", "chemistry_unified.server"],
        "cwd": "<base_dir>/chemistry-unified-server/src",
    },
    "chemistry_creative": {
        "command": sys.executable,
        "args": ["-m", "chemistry_creative.server"],
        "cwd": "<base_dir>/chemistry-creative-server/src",
    },
    "visualization": {
        "command": sys.executable,
        "args": ["-m", "visualization_mcp.server"],
        "cwd": "<base_dir>/visualization-mcp-server/src",
    },
}

# Accessed through natural language interface
# No direct API calls - tools invoked by the agent
```

### Tool Inventory

29 tools across the three servers:

| Server | Tools |
| ------ | ----- |
| `chemistry_unified` (20) | `validate_composition`, `analyze_stability`, `predict_band_gap`, `generate_crystal_csp`, `calculate_formation_energy`, `relax_structure`, `analyze_space_group`, `calculate_energy_above_hull`, `analyze_coordination`, `validate_oxidation_states`, `save_cif_file`, `create_analysis_suite`, `smact_validate_fast`, `generate_ml_representation`, `filter_compositions`, `predict_dopants`, `calculate_stress`, `fit_equation_of_state`, `list_foundation_models`, `get_server_info` |
| `chemistry_creative` (4) | `generate_crystal_structure`, `calculate_formation_energy`, `creative_discovery_pipeline`, `comprehensive_materials_analysis` |
| `visualization` (5) | `create_3dmol_visualization`, `create_pymatviz_analysis_suite`, `create_creative_visualization`, `create_rigorous_visualization`, `create_mode_aligned_visualization` |

In addition, three workspace tools run in-process rather than over MCP:
`read_file`, `write_file` and `list_files`, all scoped to a project workspace. Writes go
through an approval callback that the CLI wires to the user prompt.

## Model Selection

Backbones live in a registry (`crystalyse.config.models.MODEL_REGISTRY`), one
`ModelConfig` per entry:

```python
@dataclass(frozen=True)
class ModelConfig:
    name: str
    backend: ModelBackend        # openai | litellm | openai-compat
    model_id: str
    api_key_env_var: str
    context_window: int = 128_000
    reasoning_effort: str | None = None       # low | medium | high
    thinking_budget_tokens: int | None = None
    supported_modes: frozenset[str] = frozenset({"explore", "validate", "auto"})
    ...
```

Registered entries cover OpenAI (`openai_o4_mini`, `openai_o3`, `openai_gpt4o_mini`),
Anthropic (`anthropic_claude_opus`, `anthropic_claude_sonnet`, `anthropic_claude_haiku`),
OpenRouter, Mistral and a local Ollama backbone. Resolution goes through
`resolve_model_name()` and `resolve_model_config()`; `get_effective_registry()` adds any
`[models.<name>]` tables from `.crystalyse/config.toml`.

```bash
# Inspect the effective registry
# Columns: Name, Backend, Model ID, Context, Modes, Env Var, Source, Usable
crystalyse models list

# Check that every entry's API key env var is set
crystalyse models check

# Select a backbone for one run
crystalyse --model anthropic_claude_sonnet discover "Find stable perovskites"
```

With no `--model`, the mode picks the default: `openai_o4_mini` for `explore` and
`auto`, `openai_o3` for `validate` (`MODE_DEFAULTS`). An unregistered string is passed
through untouched, so a full LiteLLM model string works as an escape hatch.

Some entries declare a narrower `supported_modes` — the Haiku and open-weights entries are
`explore`/`auto` only, the local Ollama entry `explore` only. That field is declarative:
it appears in the Modes column and is validated for config overrides, but resolution does
not refuse a model whose modes exclude the one you asked for.

API keys are read from real environment variables — `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`. There is no `.env` file
support. Each entry's declared `reasoning_effort` / `thinking_budget_tokens` is carried
into the provider call by `ModelConfig.agent_model_settings()`.

## Custom Tool Development

### Adding a Tool to a Server

Tools are supplied by the MCP servers, so a new tool is a decorated function in a
server module. There is no in-package tool registry, base class or plugin loader:

```python
# dev/chemistry-unified-server/src/chemistry_unified/server.py
from mcp.server.mcpserver import MCPServer   # mcp 2.0 renamed FastMCP -> MCPServer

mcp = MCPServer("Chemistry Unified")


@mcp.tool(description="Comprehensive stability analysis using SMACT")
def analyze_stability(
    composition: str,
    check_electronegativity: bool = True,
    electronegativity_threshold: float = 0.5,
) -> StabilityResult:
    """Docstring and type hints become the tool schema the model sees."""
    ...
```

Return types are Pydantic models where the server defines one (`ValidationResult`,
`EnergyResult`, ...) or a plain `dict`; the visualisation server returns JSON strings.
Shared result models live in `crystalyse.tools.models` — `ToolResult` there carries
`success`, `timestamp`, `computation_time`, `errors` and `warnings`.

### MCP Server Development

A server is a module that builds an `MCPServer`, registers tools and runs over stdio:

```python
from mcp.server.mcpserver import MCPServer

from .tools import create_pymatviz_analysis_suite

mcp = MCPServer("visualization")
mcp.tool()(create_pymatviz_analysis_suite)

if __name__ == "__main__":
    mcp.run()
```

Register it in `CrystaLyseConfig.mcp_servers` with `command`, `args` and `cwd`, and the
agent can start it alongside the others.

## Tool Configuration

### Basic Configuration

`CrystaLyseConfig` is the whole configuration surface for tools; individual tool
parameters are per-call arguments on the MCP tools themselves:

```python
from crystalyse.config import CrystaLyseConfig

config = CrystaLyseConfig.load()

config.mcp_servers        # command / args / cwd per server
config.mode_timeouts      # {"explore": 120, "auto": 180, "validate": 300}
config.visualization      # enable_html, cif_only, default_color_scheme
config.provenance         # output_dir, capture_raw, show_summary, ...
config.render_gate        # enabled, log_violations (see render gate doc)
```

`CrystaLyseConfig` also carries `default_model`, `max_turns`, `parallel_batch_size`,
`max_candidates` and `structure_samples`, but nothing in the agent path reads them: the
model comes from `--model` or the per-mode default, and the turn cap is a hard-coded 1000.
The `strictness` and `block_unprovenanced` render-gate keys are likewise parsed and unused.

### Environment Variables

```bash
# Interpreter used to launch the MCP servers (e.g. a conda env)
CRYSTALYSE_PYTHON_PATH=/path/to/python

# Visualisation
CRYSTALYSE_ENABLE_HTML_VIZ=false
CRYSTALYSE_CIF_ONLY=true
CRYSTALYSE_COLOR_SCHEME=vesta

# Diagnostics
CRYSTALYSE_DEBUG=false
CRYSTALYSE_METRICS=true
```

On zsh, put API keys and these variables in `~/.zshenv` so non-interactive shells (and
therefore the MCP subprocesses) see them; `~/.zshrc` is interactive-only.

## Tool Orchestration

### Mode-Based Server Selection

The mode chooses the chemistry server; the visualisation server always starts:

```python
# crystalyse.config.modes.MODE_MCP_SERVERS
{
    Mode.EXPLORE:  "chemistry_creative",
    Mode.VALIDATE: "chemistry_unified",
    Mode.AUTO:     "chemistry_unified",
}
```

`explore`, `validate` and `auto` are the canonical mode names. `creative`, `rigorous`
and `adaptive` still resolve, with a `DeprecationWarning`, and will be removed in v2.0.
The resolved mode is also written into the agent's instructions, which require the model
to pass `mode="<mode>"` to any tool that accepts one.

### Timeouts and Turn Budget

```python
# Per-mode timeout budgets (seconds)
mode_timeouts = {"explore": 120, "auto": 180, "validate": 300}
```

The whole discovery — every tool call included — runs inside that budget; exceeding it
returns `{"status": "failed", "error": "The operation timed out."}`. Within the budget the
model decides which tools to call, up to 1000 turns.

## Error Handling and Resilience

### Tool Failure Management

Resilience is deliberately simple, and there is no fallback chain between servers:

- A server that fails to start is logged as a warning and omitted from the run; the
  agent proceeds with whatever servers did start.
- The visualisation tools catch their own failures and return
  `{"status": "error", ...}`, so the model sees the failure as tool output and can retry
  or choose another tool.
- Exceeding the mode timeout, or any unhandled exception, returns a
  `{"status": "failed", "error": ...}` result rather than raising.
- MCP servers are started and stopped per `discover()` call, so a wedged subprocess
  cannot leak into the next run.

## Performance Optimisation

### Output Caching

The visualisation server checks for existing files before regenerating them: a CIF or a
complete `<formula>_analysis/` directory is reported as `cached: true` and reused. Model
weights are cached on disk too — Chemeleon checkpoints in
`~/.cache/crystalyse/chemeleon_checkpoints/`, MACE foundation models in `~/.cache/mace/`,
phase-diagram data in `~/.cache/crystalyse/`.

### Async Execution

```python
# Crystalyse handles async execution internally
# The agent automatically manages:
# - MCP server subprocess lifecycles
# - Streaming of tool-call events to the trace handler
# - Provenance capture and the render gate pass
# - Session persistence between calls

result = await agent.discover("Find stable perovskites for photovoltaic applications")
```

## Best Practices

### 1. Mode Selection

- Use `explore` for breadth: structure generation and energies, no SMACT gate.
- Use `validate` when a candidate needs the full validation chain.
- Use `auto` when you would rather not choose; it starts from the unified server.

### 2. Data Flow

```python
# Tools communicate through standardised formats:
# SMACT (composition) -> Chemeleon (structure) -> MACE (energy) -> visualisation (CIF + PDFs)

# Structures move as CIF strings or as {numbers, positions, cell, pbc} dicts,
# so intermediate results can be handed between servers without a shared database.
```

### 3. Resource Management

- Give long validation runs the `validate` timeout budget rather than raising `explore`'s.
- Expect the first run to download model checkpoints and phase-diagram data.
- Keep an eye on the working directory: CIFs and analysis suites accumulate there.

### 4. Security

- All three MCP servers are local stdio subprocesses. Nothing listens on a port.
- The only outbound network traffic is the model provider API and the one-off checkpoint
  and phase-diagram downloads.
- File writes through the agent's `write_file` tool ask for approval first. MCP tools
  that write CIFs and analysis PDFs write them directly, with no prompt.

## Next Steps

- Explore [Agent Integration](agents.md) with tools
- Read the [Render Gate System](render_gate_system.md) for how numeric claims are checked
- Check [API Reference](../reference/index.md) for detailed documentation
