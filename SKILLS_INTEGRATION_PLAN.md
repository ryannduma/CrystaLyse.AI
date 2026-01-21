# CrystaLyse Skills Integration Plan

## Executive Summary

Agent Skills represent a paradigm shift from "building custom agents" to "teaching general agents procedural knowledge." For CrystaLyse, this means packaging computational materials science expertise—currently scattered across documentation, group wikis, and practitioner experience—into composable, token-efficient modules that AI scientists can load dynamically.

**Core Insight**: atomate2 provides the "what" (workflow definitions). Skills provide the "why" and "when to deviate"—the tacit knowledge that distinguishes an expert from a novice.

---

## Part 1: The Conceptual Fit

### 1.1 What Skills Solve for CrystaLyse

| Problem | Skill Solution |
|---------|---------------|
| Experts know when default parameters fail | `references/troubleshooting.md` loaded on error |
| Different material classes need different approaches | Domain-specific reference files (perovskites.md, batteries.md) |
| Workflow decisions depend on context | Decision trees in SKILL.md body |
| Same code rewritten repeatedly | `scripts/` with deterministic Python |
| LLM hallucinates parameters | Provenance requirements in frontmatter |

### 1.2 Progressive Disclosure for Materials Science

```
Level 0: Frontmatter (~100 tokens)
├── name: "dft-relaxation"
├── description: "Guide for DFT geometry optimizations..."
│
Level 1: SKILL.md Body (~2000 tokens)
├── Core workflow steps
├── Parameter selection heuristics
├── When to load reference files
│
Level 2: Reference Files (loaded as needed)
├── references/vasp-errors.md      # Only if VASP errors
├── references/convergence.md      # Only if convergence issues
├── references/spin-polarized.md   # Only for magnetic systems
│
Level 3: Scripts (executed, not loaded)
└── scripts/check_forces.py        # Deterministic validation
```

This is radically more token-efficient than stuffing everything into system prompts.

---

## Part 2: Proposed Skills Architecture for CrystaLyse

### 2.1 Directory Structure

```
crystalyse/
└── skills/
    ├── SKILLS_INDEX.md              # Metadata registry for all skills
    │
    ├── core/                        # Essential computational workflows
    │   ├── composition-validation/
    │   │   ├── SKILL.md
    │   │   ├── references/
    │   │   │   ├── smact-rules.md
    │   │   │   └── oxidation-states.md
    │   │   └── scripts/
    │   │       └── validate_charge_balance.py
    │   │
    │   ├── structure-prediction/
    │   │   ├── SKILL.md
    │   │   ├── references/
    │   │   │   ├── chemeleon-guide.md
    │   │   │   ├── crystal-systems.md
    │   │   │   └── confidence-interpretation.md
    │   │   └── scripts/
    │   │       └── structure_to_cif.py
    │   │
    │   ├── energy-calculation/
    │   │   ├── SKILL.md
    │   │   ├── references/
    │   │   │   ├── mace-parameters.md
    │   │   │   ├── relaxation-strategies.md
    │   │   │   └── energy-interpretation.md
    │   │   └── scripts/
    │   │       └── calculate_ehull.py
    │   │
    │   └── phase-diagram/
    │       ├── SKILL.md
    │       └── references/
    │           └── competing-phases.md
    │
    ├── domain/                      # Material-class specific knowledge
    │   ├── perovskites/
    │   │   ├── SKILL.md
    │   │   └── references/
    │   │       ├── tolerance-factor.md
    │   │       ├── octahedral-tilting.md
    │   │       └── common-dopants.md
    │   │
    │   ├── battery-cathodes/
    │   │   ├── SKILL.md
    │   │   └── references/
    │   │       ├── layered-oxides.md
    │   │       ├── spinel-structures.md
    │   │       └── voltage-prediction.md
    │   │
    │   └── thermoelectrics/
    │       ├── SKILL.md
    │       └── references/
    │           ├── band-engineering.md
    │           └── thermal-conductivity.md
    │
    ├── synthesis/                   # Synthesis route knowledge (Sky integration)
    │   ├── feasibility/
    │   │   ├── SKILL.md
    │   │   └── references/
    │   │       ├── precursor-selection.md
    │   │       ├── reaction-conditions.md
    │   │       └── competing-phases.md
    │   │
    │   └── solid-state/
    │       ├── SKILL.md
    │       └── references/
    │           ├── calcination-temps.md
    │           └── grinding-mixing.md
    │
    ├── workflows/                   # Multi-step workflow orchestration
    │   ├── materials-discovery/
    │   │   ├── SKILL.md             # Full discovery pipeline
    │   │   └── references/
    │   │       └── screening-strategies.md
    │   │
    │   └── property-optimization/
    │       ├── SKILL.md
    │       └── references/
    │           └── substitution-strategies.md
    │
    └── meta/                        # Skills about skills
        ├── mcp-builder/             # Bring your own tools
        │   ├── SKILL.md
        │   └── references/
        │       ├── fastmcp-guide.md
        │       └── tool-design.md
        │
        └── skill-creator/           # Create new skills
            ├── SKILL.md
            └── references/
                └── materials-patterns.md
```

### 2.2 Skill Dependency Graph

```
composition-validation
        │
        ▼
structure-prediction ──────────────────┐
        │                              │
        ▼                              │
energy-calculation                     │
        │                              │
        ▼                              ▼
phase-diagram ◄─────────────── synthesis/feasibility
        │
        ▼
  domain/*  (loaded based on material class)
```

---

## Part 3: Example Skills

### 3.1 Core Skill: `composition-validation`

```yaml
# skills/core/composition-validation/SKILL.md
---
name: composition-validation
description: >
  Validate chemical compositions for charge neutrality, electronegativity
  balance, and synthesizability using SMACT rules. Use when: (1) user provides
  a chemical formula to analyze, (2) before structure prediction, (3) screening
  candidate compositions, (4) checking if a material is chemically plausible.
---

# Composition Validation

## Quick Validation Workflow

1. Parse formula → Extract elements and stoichiometry
2. Check element validity → All elements in periodic table?
3. Check oxidation states → Common states for each element?
4. Check charge balance → Sum of charges ≈ 0?
5. Check electronegativity → Reasonable anion/cation distribution?

## When to Use References

- **Ambiguous oxidation states**: See [oxidation-states.md](references/oxidation-states.md)
- **Understanding SMACT rules**: See [smact-rules.md](references/smact-rules.md)

## Deterministic Validation

Run `scripts/validate_charge_balance.py <formula>` for exact charge balance.

## Provenance Requirements

Always record:
- Input formula (exactly as provided)
- Validation method (SMACT version)
- Any assumptions about oxidation states
```

### 3.2 Domain Skill: `perovskites`

```yaml
# skills/domain/perovskites/SKILL.md
---
name: perovskites
description: >
  Domain expertise for perovskite materials (ABX3, A2BB'X6, layered variants).
  Use when: (1) user mentions perovskite explicitly, (2) formula matches ABX3
  pattern, (3) discussing solar cells, ferroelectrics, or ionic conductors,
  (4) tolerance factor or octahedral tilting is relevant.
---

# Perovskite Materials Guide

## Quick Assessment

For ABX3 perovskites:
1. Calculate Goldschmidt tolerance factor: t = (rA + rX) / √2(rB + rX)
2. Assess stability: 0.8 < t < 1.0 suggests cubic perovskite is stable

## Decision Tree

- **t > 1.0**: A-site too large → hexagonal polytypes likely
- **0.9 < t < 1.0**: Cubic perovskite stable
- **0.8 < t < 0.9**: Orthorhombic/tetragonal distortions
- **t < 0.8**: B-site too large → different structure types

## When to Load References

- **Tilting patterns**: See [octahedral-tilting.md](references/octahedral-tilting.md)
- **Doping strategies**: See [common-dopants.md](references/common-dopants.md)
- **Detailed tolerance factor analysis**: See [tolerance-factor.md](references/tolerance-factor.md)
```

### 3.3 Meta Skill: `mcp-builder` (Bring Your Own Tools)

```yaml
# skills/meta/mcp-builder/SKILL.md
---
name: mcp-builder
description: >
  Guide for creating custom MCP servers to integrate external tools with
  CrystaLyse. Use when: (1) user wants to add new computational tools,
  (2) integrating with external APIs (Materials Project, AFLOW, NOMAD),
  (3) wrapping local simulation codes, (4) extending CrystaLyse capabilities.
---

# MCP Server Builder for CrystaLyse

## Overview

CrystaLyse uses MCP (Model Context Protocol) servers to interface with
computational tools. This skill guides you through creating new MCP servers
to extend CrystaLyse's capabilities.

## Workflow

### Phase 1: Define Tool Interface
1. What inputs does the tool need?
2. What outputs does it produce?
3. What provenance should be tracked?

### Phase 2: Implementation
See [fastmcp-guide.md](references/fastmcp-guide.md) for Python implementation.

### Phase 3: Integration
Register with CrystaLyse via config:
```python
# crystalyse/config.py
MCP_SERVERS = {
    "your-server": {
        "command": ["python", "-m", "your_server"],
        "tools": ["tool1", "tool2"]
    }
}
```

### Phase 4: Evaluation
Create evaluation questions per [tool-design.md](references/tool-design.md).

## Provenance Requirements

All custom tools MUST:
- Return structured output with `source` field
- Include tool version in metadata
- Log all input parameters
```

---

## Part 4: Evaluation Framework

### 4.1 Connecting to CrystaLyse Provenance

The render gate and provenance system already enforce computational honesty. Skills should extend this:

```yaml
# In SKILL.md frontmatter (proposed extension)
evaluation:
  deterministic_checks:
    - "structure_has_valid_cell"
    - "energy_is_negative"
    - "forces_below_threshold"

  provenance_requirements:
    must_record:
      - calculator_version
      - input_parameters
      - convergence_criteria
    must_justify_if_changed:
      - default_cutoff
      - k_point_density

  llm_judge_dimensions:
    - "parameter_appropriateness"
    - "result_interpretation"
```

### 4.2 Skill-Specific Evaluation Questions

For each skill, create evaluation questions that test:

1. **Tool Usage**: Can the agent use the tools correctly?
2. **Decision Making**: Does it follow the skill's decision trees?
3. **Error Recovery**: When things fail, does it follow troubleshooting guides?
4. **Provenance Compliance**: Does it record what it should?

Example evaluation for `structure-prediction`:

```xml
<evaluation>
  <qa_pair>
    <question>Predict the crystal structure for SrTiO3 using Chemeleon.
    What space group does the most confident prediction have?</question>
    <answer>Pm-3m</answer>
  </qa_pair>
  <qa_pair>
    <question>Given the formula Ba0.5Sr0.5TiO3, what is the Goldschmidt
    tolerance factor? Round to 2 decimal places.</question>
    <answer>1.01</answer>
  </qa_pair>
</evaluation>
```

### 4.3 Provenance as Evaluation Substrate

```python
# Proposed: crystalyse/skills/evaluation.py

def evaluate_skill_execution(skill_name: str, transcript: dict) -> EvalResult:
    """
    Evaluate skill execution using provenance logs.

    1. Deterministic checks on outputs
    2. Provenance completeness verification
    3. LLM-as-judge on reasoning quality
    """
    skill = load_skill(skill_name)

    # Check deterministic requirements
    for check in skill.evaluation.deterministic_checks:
        if not run_check(check, transcript):
            return EvalResult(passed=False, reason=f"Failed: {check}")

    # Check provenance completeness
    provenance = extract_provenance(transcript)
    for field in skill.evaluation.provenance_requirements.must_record:
        if field not in provenance:
            return EvalResult(passed=False, reason=f"Missing provenance: {field}")

    # LLM-as-judge for subjective dimensions
    judge_scores = []
    for dimension in skill.evaluation.llm_judge_dimensions:
        score = llm_judge(transcript, dimension, skill.rubric[dimension])
        judge_scores.append(score)

    return EvalResult(
        passed=all(s >= 3 for s in judge_scores),
        scores=judge_scores
    )
```

---

## Part 5: Integration with Existing CrystaLyse Architecture

### 5.1 Skill Loading in EnhancedCrystaLyseAgent

```python
# Proposed modification to crystalyse/agents/openai_agents_bridge.py

class EnhancedCrystaLyseAgent:
    def __init__(self, ...):
        self.skill_registry = SkillRegistry()
        self.skill_registry.load_all_skills()  # Load frontmatter only

    async def query(self, prompt: str, ...):
        # Determine which skills might be relevant
        relevant_skills = self.skill_registry.match_skills(prompt)

        # Load full SKILL.md for relevant skills
        skill_context = ""
        for skill in relevant_skills[:3]:  # Max 3 skills
            skill_context += self.skill_registry.load_skill_body(skill)

        # Inject into agent instructions
        instructions = self.base_instructions + skill_context

        # Continue with normal agent execution...
```

### 5.2 Skill-Aware Mode Injection

```python
# Proposed extension to crystalyse/agents/mode_injector.py

class GlobalModeManager:
    def get_mode_context(self, mode: str, active_skills: list[str]) -> str:
        base_context = self._get_base_mode_context(mode)

        # Add skill-specific mode adaptations
        for skill in active_skills:
            skill_mode_hints = self.skill_registry.get_mode_hints(skill, mode)
            if skill_mode_hints:
                base_context += f"\n\n## {skill} ({mode} mode)\n{skill_mode_hints}"

        return base_context
```

### 5.3 Memory Integration

Skills could inform the memory system about what to cache:

```python
# Proposed extension to crystalyse/memory/crystalyse_memory.py

class CrystaLyseMemory:
    def cache_skill_discovery(self, skill: str, discovery: dict):
        """Cache discoveries made while using a skill."""
        # Skills can define what's worth caching
        skill_config = self.skill_registry.get_skill(skill)
        cache_fields = skill_config.get("cache_fields", [])

        filtered = {k: v for k, v in discovery.items() if k in cache_fields}
        self.discovery_cache.add(skill, filtered)
```

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

1. **Create skill loading infrastructure**
   - `SkillRegistry` class for managing skills
   - Frontmatter parser for YAML metadata
   - Skill matching algorithm based on description

2. **Port existing knowledge to skills**
   - `composition-validation` (wrap existing SMACT tools)
   - `structure-prediction` (wrap Chemeleon)
   - `energy-calculation` (wrap MACE)

3. **Basic evaluation framework**
   - Deterministic checks only
   - Integration with existing provenance system

### Phase 2: Domain Skills (Week 3-4)

1. **Create domain-specific skills**
   - `perovskites` (leveraging existing knowledge)
   - `battery-cathodes` (common use case)
   - `thermoelectrics` (aligns with existing tests)

2. **Synthesis integration**
   - Port Sky agent knowledge to `synthesis/feasibility`
   - Link synthesis skills to structure prediction

3. **Evaluation expansion**
   - Add LLM-as-judge for subjective dimensions
   - Create evaluation question sets for each skill

### Phase 3: Meta Skills & Community (Week 5-6)

1. **MCP Builder skill**
   - Enable users to bring their own tools
   - Template for new MCP servers
   - Integration documentation

2. **Skill Creator skill**
   - Guide for creating new CrystaLyse skills
   - Materials-science-specific patterns

3. **Community infrastructure**
   - Skill contribution guidelines
   - Version control for skills
   - Skill sharing mechanism

---

## Part 7: Generalizing Beyond atomate2

### 7.1 The Opportunity

atomate2 codifies workflow *definitions*. Skills codify workflow *wisdom*:

| atomate2 | Skills |
|----------|--------|
| "Run VASP with these INCAR settings" | "When to deviate from default INCAR" |
| "Calculate phonons with phonopy" | "What imaginary modes mean and how to fix them" |
| "Submit to queue manager" | "How to debug queue failures" |

### 7.2 Broader Computational Materials Science Skills

Beyond CrystaLyse's current scope, skills could teach agents about:

- **AiiDA workflows** - How to navigate provenance graphs
- **FireWorks** - Queue management and job recovery
- **Materials Project API** - Efficient data retrieval patterns
- **AFLOW** - Database query optimization
- **ASE calculators** - When to use which calculator

### 7.3 Cross-Platform Skill Portability

Skills are platform-agnostic by design. A `perovskites` skill could work with:
- CrystaLyse (OpenAI Agents + MCP)
- Claude.ai (native skill support)
- FutureHouse agents
- Custom LangChain/LangGraph implementations

This aligns with Anthropic's vision of skills as an "open standard for cross-platform portability."

---

## Part 8: Connection to Broader AI-for-Science Trends

Recent developments validate this direction:

- **[El Agente](https://acceleration.utoronto.ca/news/meet-el-agente-an-autonomous-ai-for-performing-computational-chemistry)** (U Toronto): Multi-agent system for quantum chemistry with 87% first-attempt success rate
- **[FutureHouse Platform](https://www.futurehouse.org/research-announcements/launching-futurehouse-platform-ai-agents)**: AI agents for scientific discovery emphasizing reproducibility
- **[Matlantis Agentic AI](https://cen.acs.org/physical-chemistry/computational-chemistry/Chemical-industry-bet-agentic-AI/104/web/2026/01)**: Industry adoption of agents for materials simulation
- **[SciToolAgent](https://arxiv.org/html/2503.08979v1)**: Knowledge-graph-powered tool orchestration

The common thread: packaging domain expertise for AI consumption. Skills are the natural format for this.

---

## Summary

Skills offer CrystaLyse a path from "AI tool that runs calculations" to "AI scientist with domain expertise." The key insight is that procedural knowledge—when to deviate, how to troubleshoot, what matters for each material class—is the bottleneck for AI agents in computational materials science.

By adopting the Agent Skills paradigm:
1. **Token efficiency**: Load expertise only when needed
2. **Composability**: Mix and match domain knowledge
3. **Community leverage**: Package and share expert knowledge
4. **Evaluation**: Systematic validation tied to provenance
5. **Portability**: Skills work across agent frameworks

The MCP Builder skill enables extensibility—users bring their tools, CrystaLyse teaches them how to use them scientifically.

---

## Next Steps

1. Review this plan and prioritize skills to implement first
2. Prototype `composition-validation` skill as proof of concept
3. Design skill registry integration with existing agent architecture
4. Create evaluation framework connected to provenance system
