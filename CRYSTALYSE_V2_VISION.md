# CrystaLyse V2 Vision: Skills + CLI Architecture

## The Paradigm Shift

**Current CrystaLyse (v1):** MCP servers → Tool definitions → JSON schemas → Protocol overhead

**CrystaLyse V2:** Skills + CLI → Agent reads SKILL.md → Agent runs bash/Python directly

### Why This Works

From [Simon Willison](https://simonwillison.net/):
> "Almost everything I might achieve with an MCP can be handled by a CLI tool instead. LLMs know how to call `cli-tool --help`, which means you don't have to spend many tokens describing how to use them."

From [Armin Ronacher](https://lucumr.pocoo.org/) (creator of Flask):
> "This leads me to my current conclusion: I tend to go with what is easiest, which is to ask the agent to write its own tools as a skill."

The token cost is real:
- GitHub MCP: 52,000 tokens for a single snapshot
- CLI equivalent: 1,200 tokens for targeted queries
- **That's 43x more efficient**

---

## Codex Architecture (The Blueprint)

After analyzing `/home/ryan/updatecrystalyse/CrystaLyse.AI/codex/codex-rs/core/src/skills/`:

### Skill Loading System

```rust
// From loader.rs
pub fn load_skills(config: &Config) -> SkillLoadOutcome {
    // Scans directories:
    // - .codex/skills/ (Repo scope)
    // - ~/.codex/skills/ (User scope)
    // - ~/.codex/skills/.system/ (System scope)
    // - /etc/codex/skills/ (Admin scope)

    // Only loads YAML frontmatter initially (name + description)
    // Full SKILL.md body loaded on-demand when invoked
}
```

### Progressive Disclosure (from render.rs)

```markdown
## How to use skills (progressive disclosure):
1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
2) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
3) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
4) If `assets/` or templates exist, reuse them instead of recreating from scratch.
```

### Trigger Rules

```
- Discovery: The list above is the skills available (name + description + path).
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description, you must use that skill.
- How to use: Open its `SKILL.md`, read only enough to follow the workflow.
```

---

## Replacing MCP with Skills + CLI

### Current MCP Architecture (v1)

```
CrystaLyse Agent
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  MCP Servers (running processes)                    │
│  ├── chemistry-unified-server (SMACT, Chemeleon,    │
│  │   MACE, PyMatgen)                                │
│  ├── chemistry-creative-server (Chemeleon, MACE)    │
│  └── visualization-server (3Dmol, pymatviz)         │
└─────────────────────────────────────────────────────┘
      │
      ▼
   Tool Calls (JSON-RPC over stdio)
      │
      ▼
   Results
```

**Problems:**
- Protocol overhead (JSON schemas, tool definitions)
- Token cost for tool descriptions
- Process management complexity
- Server startup latency

### New Skills + CLI Architecture (v2)

```
CrystaLyse Agent
      │
      ├── Reads: skills/index (name + description only)
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Skill Triggered                                     │
│  → Agent reads SKILL.md                             │
│  → Agent runs scripts/query.py or CLI commands      │
│  → Results returned directly                        │
└─────────────────────────────────────────────────────┘
```

**Benefits:**
- No protocol overhead
- Minimal token cost (skill summaries ~100 tokens each)
- No server processes
- Direct execution
- Agent can adapt/modify scripts on the fly

---

## Proposed Skills for CrystaLyse V2

### Core Skills (replacing MCP tools)

```
skills/
├── smact-validation/
│   ├── SKILL.md
│   └── scripts/
│       ├── validate.py          # from smact import smact_filter
│       └── oxidation_states.py
│
├── chemeleon-prediction/
│   ├── SKILL.md
│   └── scripts/
│       ├── predict_csp.py       # Crystal structure prediction
│       ├── predict_dng.py       # De novo generation
│       └── structure_to_cif.py
│
├── mace-calculation/
│   ├── SKILL.md
│   └── scripts/
│       ├── relax.py             # Structure relaxation
│       ├── formation_energy.py
│       └── forces.py
│
├── phase-diagram/
│   ├── SKILL.md
│   └── scripts/
│       ├── hull_distance.py     # Energy above hull
│       ├── competing_phases.py
│       └── query_mp.py          # Materials Project API
│
└── visualization/
    ├── SKILL.md
    └── scripts/
        ├── structure_3d.py      # 3Dmol.js HTML output
        ├── plot_dos.py
        └── write_cif.py
```

### Domain Skills (procedural knowledge)

```
skills/
├── perovskites/
│   ├── SKILL.md                 # Tolerance factor, octahedral tilting
│   └── references/
│       ├── goldschmidt.md
│       └── dopants.md
│
├── battery-cathodes/
│   ├── SKILL.md
│   └── references/
│       ├── layered-oxides.md
│       └── voltage-prediction.md
│
└── synthesis-feasibility/       # Sky agent knowledge
    ├── SKILL.md
    └── references/
        ├── precursors.md
        └── competing-phases.md
```

---

## Example: SMACT Validation Skill

### skills/smact-validation/SKILL.md

```yaml
---
name: smact-validation
description: >
  Validate chemical compositions for charge neutrality, electronegativity
  balance, and synthesizability using SMACT rules. Use when: (1) user
  provides a formula to analyze, (2) before structure prediction,
  (3) screening candidate compositions.
---

# SMACT Validation

## Quick Usage

To validate a composition:
```bash
python scripts/validate.py "LiFePO4"
```

Output: JSON with validity, oxidation states, and reasoning.

## What It Checks

1. **Charge neutrality**: Sum of oxidation states ≈ 0
2. **Electronegativity**: Anion more electronegative than cation
3. **Pauling rules**: Common oxidation states for each element

## Provenance Requirements

Always record:
- Input formula (exactly as provided)
- SMACT version used
- Any assumptions about oxidation states
```

### skills/smact-validation/scripts/validate.py

```python
#!/usr/bin/env python3
"""Validate composition using SMACT."""
import json
import sys
from smact import Element
from smact.screening import smact_filter

def validate(formula: str) -> dict:
    # Parse formula, run smact_filter, return result
    ...
    return {
        "formula": formula,
        "valid": True,
        "oxidation_states": [...],
        "reasoning": "Charge balanced, electronegativity satisfied"
    }

if __name__ == "__main__":
    result = validate(sys.argv[1])
    print(json.dumps(result, indent=2))
```

### Agent Interaction

```
User: Is LiFePO4 a valid composition?

Agent: [Reads skill description, matches "validate composition"]
       [Opens SKILL.md, sees: python scripts/validate.py "LiFePO4"]
       [Runs command]

$ python scripts/validate.py "LiFePO4"
{
  "formula": "LiFePO4",
  "valid": true,
  "oxidation_states": ["Li+1", "Fe+2", "P+5", "O-2"],
  "reasoning": "Charge balanced: 1(+1) + 1(+2) + 1(+5) + 4(-2) = 0"
}

Agent: LiFePO4 is a valid composition. The oxidation states are Li⁺, Fe²⁺, P⁵⁺, O²⁻,
       which sum to zero (charge balanced).
```

**No MCP server. No protocol. Just a script and the agent's ability to run bash.**

---

## When MCP Is Still Needed

Skills + CLI work when you have shell access. MCP is still necessary for:

| Scenario | Why MCP | Example |
|----------|---------|---------|
| No shell access | Claude Desktop, web UI | Consumer interfaces |
| Stateful sessions | Persistent connections | Browser automation, DB pools |
| OAuth/complex auth | Token refresh | Third-party APIs |
| Cross-platform distribution | "Install this MCP" | Consumer tools |

For **scientific computing on HPC with shell access**, almost none of these apply.

The only MCP that might remain useful:
- **HPC Job Scheduler**: SLURM/PBS job submission and monitoring (stateful)
- **External APIs**: If you don't want to embed credentials in scripts

---

## Implementation Roadmap

### Phase 1: Skills Infrastructure

1. Port Codex's skill loading to Python
   - `SkillLoader.load_skills()` - scan directories
   - `SkillRegistry` - index of name + description
   - `SkillInjector` - inject into agent instructions

2. Create `skills/` directory structure in CrystaLyse

3. Write skill summaries for existing tools

### Phase 2: Port MCP Tools to Skills

1. `smact-validation/` - Port SMACT validator
2. `chemeleon-prediction/` - Port Chemeleon CSP/DNG
3. `mace-calculation/` - Port MACE energy/relaxation
4. `phase-diagram/` - Port PyMatgen phase diagram tools
5. `visualization/` - Port 3Dmol and plotting

### Phase 3: Domain Knowledge Skills

1. `perovskites/` - Tolerance factor, tilting patterns
2. `battery-cathodes/` - Layered oxides, voltage prediction
3. `synthesis-feasibility/` - Sky agent knowledge

### Phase 4: Evaluation & Provenance

1. Skill-specific evaluation questions
2. Provenance requirements in SKILL.md frontmatter
3. Deterministic verification scripts

---

## The Vision

**CrystaLyse V2 = Codex for Materials Science**

- Same efficient Skills + CLI architecture
- Domain-specific procedural knowledge (perovskites, batteries, synthesis)
- Provenance enforcement built into skills
- Agent runs pymatgen/SMACT/MACE directly via Python scripts
- No MCP overhead, no token bloat from tool definitions

The agent becomes an AI scientist that:
1. Reads a skill to learn how to use a tool
2. Runs the tool directly (CLI/Python)
3. Interprets results using domain knowledge
4. Logs provenance as required by the skill

This is what Codex does for coding. CrystaLyse V2 does it for materials science.

---

## References

- [Codex CLI](https://developers.openai.com/codex/cli/) - OpenAI's coding agent
- [Agent Skills Blog](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - Anthropic's skills paradigm
- [Simon Willison on MCP vs CLI](https://simonwillison.net/) - Token efficiency analysis
- [Armin Ronacher on Skills](https://lucumr.pocoo.org/) - Practical experience
- [Best AI Coding Agents 2026](https://www.faros.ai/blog/best-ai-coding-agents-2026) - Industry trends
