# CrystaLyse.AI Vision

## Mission

Transform materials design from sequential, resource-intensive workflows into adaptive, AI-accelerated research that maintains scientific rigor whilst enabling systematic exploration of chemical space.

## Scientific Context

The high-throughput paradigm transformed computational materials science by enabling systematic exploration of broad design spaces. Public materials databases now exceed hundreds of thousands of computed crystal structures, assembled through automated workflows combining enumeration, crystal structure prediction, generative sampling, and density functional theory calculations.

Despite these advances, the prevailing mode remains fundamentally linear: fixed pipelines following deterministic sequences. As design problems scale in complexity, the need grows for adaptive systems that can prioritise pathways dynamically rather than execute prescribed workflows.

## Core Principles

**Scientific Integrity**

Maintain complete traceability of all numerical results to actual computational tools. The system employs three-layer provenance enforcement:

- Prompt guidance instructing compute-or-decline behaviour
- Runtime tracking capturing all tool outputs with (value, unit, source_tool, artifact_hash, timestamp)
- Render gate blocking unprovenanced material properties from display

Every reported formation energy, hull distance, or structural parameter must originate from explicit tool invocations rather than model estimation.

**Workflow Acceleration**

Enable researchers to delegate substantial computational materials design tasks through natural language interfaces. The system decomposes queries autonomously, formulates multi-step plans, and executes tool calls with validation protocols.

Computational efficiency:
- Creative mode: ~50s per query for rapid exploration
- Rigorous mode: 2-5min per query for comprehensive validation
- Adaptive mode: Context-dependent routing balancing speed and depth

**Adaptive Intelligence**

Learn user expertise levels and adapt clarification strategies accordingly. The integrated clarification system analyses queries (terminology density, specificity, confidence cues) to tailor questions. User preference memory maintains expertise indicators with temporal decay, enabling progressive reduction in clarification depth for experienced users.

**Extensibility**

Support integration with existing research infrastructure through modular architecture. MCP servers provide standardised interfaces across computational tools (SMACT, Chemeleon, MACE, PyMatGen). The system detects available tools at runtime, enabling dynamic capability discovery and graceful degradation when components are unavailable.

## Design Philosophy

**Single-Agent Architecture**

Avoid multi-agent coordination overhead through provenance-enforced single-agent design. Multi-agent frameworks incur brittleness (high failure rates on standard benchmarks) and excessive token consumption (>10× versus single-agent approaches). Runtime tool discovery via MCP enables flexible orchestration without distributed coordination protocols.

**Database Grounding**

Mandatory external validation for composition validity and stability assessment. The system queries Materials Project phase diagrams (271,617 entries) for energy above hull calculations. Execution-time validation with hash-based provenance defends against tool hallucination whilst foundation models continue improving.

**Provenance as Architecture**

Computational honesty emerges from architectural enforcement rather than prompt engineering alone. The render gate applies rule-based semantic classification across six categories (Material Property, Derived, Literature, Contextual, Statistical, Unclassified). Unprovenanced material properties are logged in validation mode, enabling refinement of classification rules before strict filtering.

## Technical Approach

**Three-Mode Operation**

Balance exploration breadth against validation depth through computational strategy selection:

- **Creative**: Fewer candidate structures (~3 per composition), faster exploration
- **Rigorous**: Extensive polymorph sampling (30+ structures), comprehensive checks
- **Adaptive**: Dynamic routing based on query complexity and intermediate confidence

Mode selection affects structure generation parameters, stability validation protocols, and computational resource allocation.

**Hierarchical Agent Architecture**

Three-layer system enabling autonomous behaviour with scientific oversight:

- **Orchestration layer**: Strategic decision-making and computational approach selection
- **Execution layer**: MCP server communication with context-aware resource management
- **Validation layer**: Pattern-based verification ensuring complete traceability

Base timeouts scale intelligently: 60s SMACT validation, 300s Chemeleon generation, 600s MACE calculations, with dynamic adjustment based on complexity assessment.

**Memory System**

Four specialised layers enabling research continuity:

- Session memory (conversation history, tool traces, timing metrics)
- Discovery cache (computed materials, 24hr TTL)
- User preference memory (expertise level, clarification depth)
- Cross-session context (research themes, successful strategies)

SQLite persistence enables multi-day projects with cumulative knowledge retention.

## Long-Term Vision

**Extended Property Coverage**

Current limitations include electronic, optical, and magnetic properties requiring additional surrogate models. Future development targets:

- Electronic structure surrogates (tight-binding models)
- Optical property predictors (band gap, absorption spectra)
- Magnetic property calculators (exchange parameters, Curie temperatures)
- OPTIMADE database connectivity for broader materials coverage

**Experimental Integration**

Close the computational-experimental loop through direct equipment connectivity:

- Automated synthesis planning from predicted structures
- Real-time characterisation data feedback
- Iterative refinement between prediction and validation
- High-throughput experimental design optimisation

**Enhanced Safety**

Address current vulnerabilities (25% failure rate on disguised toxic requests) through architectural improvements:

- Semantic safety classifiers beyond pattern matching
- Real-time toxicity assessment for generated compositions
- Life-cycle analysis integration for sustainability evaluation
- Adversarial robustness through continuous testing

**Community Tools**

Enable broader adoption through:

- Plugin interface for custom ML models and calculators
- Jupyter kernel integration for interactive notebooks
- OpenAPI + Python SDK for laboratory automation
- Cloud deployment options for institutional use

## Design Standards

**Computational Honesty**

Zero tolerance for fabricated energies, structures, or properties. All numerical outputs undergo validation with complete audit trails. Material properties lacking provenance are flagged and blocked from display.

**Reproducibility**

Complete computational history preserved in JSONL format. Every session generates:
- events.jsonl (raw events with timestamps)
- tool_calls.jsonl (tool invocations with timing)
- materials.jsonl (discovered materials)
- performance.jsonl (computational metrics)

Session summaries include MCP tool call counts, materials discovered, and provenance statistics.

**Failure Transparency**

Clear communication of computational limitations. Tool failures reported explicitly rather than substituted with estimates. Alternative approaches suggested when primary tools unavailable. Graceful degradation maintaining partial functionality.

## Research Applications

The system targets computational materials design across:

**Energy Materials**
- Battery cathodes and anodes (Li-ion, Na-ion, solid-state)
- Solid electrolytes and fast ion conductors
- Photovoltaic semiconductors and perovskites
- Thermoelectric materials

**Electronic Materials**
- Ferroelectric and multiferroic materials
- Magnetic materials and spintronics
- Semiconductor devices
- Quantum materials

**Structural Materials**
- High-temperature ceramics
- Hard coatings and superhard materials
- Transparent conductors

## Limitations and Future Work

**Current Constraints**

- Tool coverage limited to composition validation, structure prediction, formation energy
- Database-bounded discovery scope (Materials Project, ICSD)
- Point estimates without per-calculation uncertainty quantification
- Consumer hardware computational limits
- Format sensitivity in composition validity (training corpus bias)

**Development Priorities**

Near-term (v1.1-v1.2):
- Plugin interface for custom tools
- ML-based provenance classifier (transformer model replacing regex)
- Jupyter kernel integration

Medium-term (v1.3-v2.0):
- OpenAPI + Python SDK for automation
- Literature contextualization (property extraction, database integration)
- Extended property coverage (electronic, optical, magnetic)

Long-term (v2.1+):
- Multimodal interface (web, collaborative)
- Experimental integration (synthesis equipment connectivity)
- Cloud deployment (institutional scale)

## Acknowledgements

This vision builds on foundations provided by:
- SMACT developers (composition validation)
- Chemeleon developers (structure prediction)
- MACE developers (ML force fields)
- PyMatGen developers (materials analysis)
- Materials Project and ICSD (materials data)

Supported by EPSRC project EP/X037754/1 and AIchemy hub (grants EP/Y028775/1, EP/Y028759/1).

---

**Ryan Nduma, Hyunsoo Park, and Aron Walsh**

Department of Materials, Imperial College London
