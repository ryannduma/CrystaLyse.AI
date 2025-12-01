# CrystaLyse.AI Status & Roadmap

**Current Status**: Version 1.0.0
**PyPI Release**: v1.0.1 (stable)
**Development**: v1.0.0-dev (this repository)
**Date**: 2025-12-01

## Project Status

Crystalyse is a provenance-enforced scientific agent for computational materials design. Version 1.0 represents a stable release suitable for research applications, with active development continuing in this repository.

The system has been validated through:
- Component integration testing (SMACT, Chemeleon, MACE, PyMatGen)
- Materials design task demonstrations (quaternary oxides, battery cathodes, photovoltaics)
- Adversarial testing suite (86% pass rate across safety, robustness, sustainability)
- Shadow validation confirming zero material-property hallucinations

## Core Capabilities (v1.0.0)

### Computational Tools

**SMACT Integration**
- Compositional screening via charge balance and electronegativity
- Oxidation state assignment
- Chemical validity checks (<10ms per composition on CPU)

**Chemeleon Integration**
- Crystal structure generation from composition
- Multiple candidate structures (mode-dependent: 3-30 structures)
- Denoising diffusion model with pre-loaded checkpoints
- Auto-download on first run (~600 MB, cached)

**MACE Integration**
- Formation energy calculation via ML force field
- Structure relaxation and optimisation
- MACE-MP0 foundation model pre-trained on Materials Project
- Computational cost: 1-2s single-point, ~1h molecular dynamics (GPU)

**PyMatGen Integration**
- Energy above hull calculations (271,617 Materials Project entries)
- Phase diagram construction
- Space group analysis and symmetry operations
- Crystallographic analysis (coordination, bond valence)
- Auto-download phase diagrams (~170 MB, one-time)

### Operational Modes

| Mode | Duration | Candidate Structures | Validation Depth |
|------|----------|---------------------|------------------|
| Creative | ~50s | 3 per composition | Fast exploration |
| Rigorous | 2-5min | 30+ per composition | Comprehensive |
| Adaptive | Variable | Context-dependent | Dynamic routing |

Mode selection adapts computational strategy to query demands, balancing speed against validation thoroughness.

### Provenance System

Three-layer enforcement:
1. **Prompt guidance** - Instructs compute-or-decline behaviour
2. **Runtime tracking** - Tuple-based provenance (value, unit, source_tool, artifact_hash, timestamp)
3. **Render gate** - Blocks unprovenanced material properties

All numerical outputs undergo regex validation. Material properties must trace to explicit tool invocations. JSONL audit trails enable complete reproducibility.

### Memory Architecture

Four specialised layers:
- **Session memory** - Conversation history, tool traces, timing metrics
- **Discovery cache** - Computed materials, formation energies (24hr TTL)
- **User preference memory** - Expertise level, clarification depth, vocabulary patterns
- **Cross-session context** - Research themes, recurring systems, strategy patterns

SQLite persistence enables multi-day research continuity.

### Safety Filtering

Three-tier classification:
- **Tier 1** (Automatic refusal) - Explosive materials, toxic heavy metals, chemical weapons
- **Tier 2** (Context review) - Ambiguous requests requiring clarification
- **Tier 3** (Safe execution) - Legitimate safety applications (fire-resistant ceramics, biocompatible implants)

Current vulnerabilities: 25% failure rate on disguised toxic requests and high-energy material ambiguity.

### Interface

**CLI** (Typer + Rich):
- Non-interactive: `crystalyse analyse` for scripted single-shot analyses
- Interactive: `crystalyse chat` for multi-turn sessions
- Adaptive clarification based on expertise detection
- Dynamic mode switching with context preservation

**Session Management**:
- Persistent sessions across computational runs
- User preference tracking with temporal decay
- Cross-session pattern recognition

## Performance Benchmarks

**Hardware**: Intel i7, 16GB RAM, no GPU

| Operation | Creative Mode | Rigorous Mode |
|-----------|---------------|---------------|
| Simple query (single material) | ~50s | 2-3min |
| Complex analysis (multiple candidates) | 1-2min | 3-5min |
| Batch screening (10 materials) | 5-10min | 15-30min |

**Resource Requirements**:
- Python 3.11+
- RAM: 8GB minimum, 16GB recommended
- Storage: ~2GB (installation + cache)
- Network: Required for first-run downloads
- GPU: Optional (MACE acceleration)

## Development Roadmap

### Near-Term (v1.1-v1.2)

**Workspace Management Integration**
- Complete integration of file operation system (`crystalyse/workspace/`)
- Enhanced approval workflows with preview capabilities
- Improved clarification system integration
- Context-aware file suggestions

**Enhanced Memory System**
- Production-ready cross-session context (`crystalyse/memory/`)
- Refined user preference learning algorithms
- Temporal decay models for preference weighting
- Multi-user collaboration support

**Plugin Interface for Custom Tools**
- MCP-compatible plugin architecture
- Standardised tool interfaces
- Custom ML model integration
- Experimental data connectors

**Enhanced Provenance Classifier**
- ML-based semantic classification
- Replace rule-based system with transformer model (BERT/RoBERTa)
- Training on shadow-mode logs
- Improved precision for paraphrasing and novel phrasings

**Jupyter Kernel Integration**
- Native Jupyter protocol support
- Rich display capabilities
- Interactive notebook workflows

### Medium-Term (v1.3-v2.0)

**OpenAPI + Python Client SDK**
- FastAPI-based REST service
- Async task handling
- Laboratory automation integration
- Pipeline orchestration

**Literature Contextualization**
- Materials database integration (Materials Project, PubChem)
- Property extraction from literature
- NLP processing for context enhancement

**Extended Property Coverage**
- Electronic structure surrogates
- Optical property predictors
- Magnetic property calculators
- OPTIMADE database connectivity

### Long-Term (v2.1+)

**Multimodal Interface**
- VScode extension interface with enhanced visual feedback
- Visual workflow management
- Educational environments

**Experimental Integration**
- Direct synthesis agent integration (Sky) and perhaps equipment connectivity
- Multimodal data feedback via file upload/reading


**Advanced Safety**
- Semantic safety classifiers
- Real-time toxicity assessment
- Life-cycle analysis integration

## Known Limitations

**Tool Coverage**
- Electronic, optical, magnetic properties require additional surrogates
- Limited to inorganic crystals (organic/hybrid systems not supported)
- Database-bounded discovery scope


**Safety Vulnerabilities**
- 25% failure rate on disguised toxic requests
- High-energy material ambiguity (battery vs explosive)
- Semantic framing bypasses

**Model Capabilities**
- Point estimates only (per-calculation uncertainty not exposed)
- Format sensitivity in composition validity (training corpus bias)
- Tool hallucination risks without runtime validation

**Computational Constraints**
- Consumer hardware limits throughput
- ML force fields provide approximate energies
- No direct DFT validation

**Experimental Features**
- Workspace management (`crystalyse/workspace/`) is scaffolded with basic file operations and clarification callbacks; full integration pending
- Enhanced memory features (`crystalyse/memory/`) provide four-layer architecture but cross-session context and user preference learning are experimental; improved integration planned for near-term releases

## Architecture Principles

**Single-Agent Design**
- Avoids multi-agent coordination overhead
- Reduced brittleness and failure modes
- Lower token consumption versus multi-agent frameworks
- Runtime tool discovery via MCP

**Database Grounding**
- Mandatory for composition validity
- Materials Project phase diagrams (271,617 entries)
- Execution-time validation with hash-based provenance

**Modular Extensibility**
- MCP servers as thin wrappers
- Tool implementations in `crystalyse.tools.*`
- Clean Python packaging (no PYTHONPATH manipulation)

## Contributing

The project welcomes contributions in several areas:

**Tool Integration**
- Additional calculators (tight-binding, property-specific)
- Database connectors (OPTIMADE, COD, ICSD)
- Experimental data sources

**Safety & Validation**
- Adversarial test cases
- Semantic classifiers
- Toxicity databases

**Performance Optimisation**
- Batch processing improvements
- GPU utilisation
- Caching strategies

**Documentation**
- Use case tutorials
- Educational materials
- API documentation

See [CLAUDE.md](CLAUDE.md) for development setup.

## Citation

If you use Crystalyse in your research, please cite:

```bibtex
@article{nduma2025crystalyse,
  title={Crystalyse: a multi-tool agent for materials design},
  author={Nduma, Ryan and Park, Hyunsoo and Walsh, Aron},
  journal={In preparation},
  year={2025}
}
```

And the underlying tools:
- SMACT: Davies et al., JOSS 4, 1361 (2019)
- Chemeleon: Park et al., Nat. Commun. (2025)
- MACE: Batatia et al., NeurIPS (2022)
- PyMatgen: Ong et al. (2013)

## Acknowledgements

This work was supported by:
- EPSRC project EP/X037754/1
- AIchemy hub (grants EP/Y028775/1, EP/Y028759/1)

We thank the developers of SMACT, Chemeleon, MACE, PyMatGen, Pymatviz, and the OpenAI Agents SDK, as well as the Materials Project and ICSD for providing materials data.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Ryan Nduma, Hyunsoo Park, and Aron Walsh**
Department of Materials, Imperial College London
