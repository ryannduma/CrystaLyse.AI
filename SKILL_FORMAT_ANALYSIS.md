# Skill Format Analysis: Anthropic vs Codex

## Key Insight: Progressive Disclosure & Script Execution

The user's observation is correct: **"the agent only looks at scripts when it gets it wrong"**

This is by design. From Anthropic's skill-creator SKILL.md:
> "Scripts may be executed without loading into context"
> "Scripts may still need to be read by Claude for patching or environment-specific adjustments"

### Three-Level Loading System

```
Level 1: Metadata (Always loaded, ~100 words)
         └── name + description in YAML frontmatter
         └── This is ALL the agent sees until skill triggers

Level 2: SKILL.md Body (Loaded when skill triggers, <5k words)
         └── Workflow instructions
         └── References to scripts/references/assets

Level 3: Bundled Resources (Loaded as needed, unlimited)
         └── scripts/ → Executed directly, read only if errors
         └── references/ → Read when specific info needed
         └── assets/ → Used in output, never read into context
```

---

## Anthropic Skill Format (Canonical)

### Directory Structure

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description)
│   └── Markdown body (workflow, instructions)
├── scripts/           (optional)
│   └── *.py, *.sh     (executable, run without reading)
├── references/        (optional)
│   └── *.md           (loaded into context when needed)
└── assets/            (optional)
    └── templates, images, fonts (used in output, never read)
```

### SKILL.md Format

```yaml
---
name: skill-name
description: >
  Complete explanation of what the skill does AND when to use it.
  Include specific triggers, file types, or tasks. This is the ONLY
  field the agent sees before triggering.
---

# Skill Title

## Overview
[1-2 sentences]

## Workflow / Tasks
[Instructions for using the skill]
[References to scripts, references, assets]

## [Additional sections as needed]
```

### Key Design Principles

1. **Concise is Key**: "The context window is a public good"
   - Challenge each token: "Does Claude really need this?"
   - Prefer concise examples over verbose explanations

2. **Degrees of Freedom**: Match specificity to task fragility
   - High freedom: Text instructions (multiple approaches valid)
   - Medium freedom: Pseudocode/scripts with parameters
   - Low freedom: Specific scripts (fragile operations)

3. **Progressive Disclosure**: Only load what's needed
   - Keep SKILL.md under 500 lines
   - Split large content into references/
   - Avoid deeply nested references (one level from SKILL.md)

4. **Scripts Execute First, Read Second**:
   - Run `scripts/validate.py "input"` directly
   - Only read script if: errors occur, patching needed, environment adjustment

---

## Codex Skill Format (Rust Implementation)

### Directory Scanning (from loader.rs)

```rust
// Scopes in priority order:
skill_roots() -> Vec<(SkillScope, PathBuf)> {
    vec![
        (Repo, ".codex/skills/"),      // Project-specific
        (User, "~/.codex/skills/"),    // User-wide
        (System, "~/.codex/skills/.system/"),  // Built-in
        (Admin, "/etc/codex/skills/"), // System admin
    ]
}
```

### Metadata Loading (from loader.rs)

```rust
struct SkillMetadata {
    name: String,
    description: String,
    path: PathBuf,
    scope: SkillScope,
}

// Only parses YAML frontmatter initially
// Full body loaded on-demand when skill is invoked
fn load_skill_frontmatter(path: &Path) -> Result<SkillMetadata>
```

### Skill Injection (from render.rs)

```markdown
## Skills
A skill is a set of local instructions stored in a `SKILL.md` file.

### Available skills
- skill-name: Description (file: path/to/SKILL.md)

### How to use skills
- Discovery: The list above shows available skills (name + description + path)
- Trigger rules: If user names a skill with `$SkillName` or task clearly matches
- How to use (progressive disclosure):
  1) Open SKILL.md, read only enough to follow workflow
  2) If references/ exist, load only specific files needed
  3) If scripts/ exist, prefer running them over retyping code
  4) If assets/ exist, reuse them instead of recreating
```

### Key Codex Patterns

1. **$skill-name Invocation**: Explicit skill triggering
2. **Scope Priority**: Repo > User > System > Admin
3. **Lazy Loading**: Frontmatter always, body on-demand
4. **Script Preference**: "prefer running or patching them instead of retyping"

---

## Comparison: Anthropic vs Codex

| Aspect | Anthropic | Codex |
|--------|-----------|-------|
| **Format** | SKILL.md with YAML frontmatter | Same |
| **Directories** | scripts/, references/, assets/ | Same (scripts/, references/, assets/) |
| **Invocation** | Task matching + explicit mention | `$skill-name` syntax |
| **Scopes** | Not specified | Repo, User, System, Admin |
| **Loading** | Progressive disclosure | Same (frontmatter first) |
| **Script Pattern** | Execute first, read if needed | Same |

**Verdict**: The formats are essentially identical. Codex likely adopted Anthropic's skill paradigm.

---

## Implications for CrystaLyse V2

### What We Need

1. **SkillLoader** (Python port of Codex's loader.rs)
   ```python
   class SkillLoader:
       def load_skills(self) -> list[SkillMetadata]:
           """Scan skill directories, parse frontmatter only."""

       def get_skill_body(self, skill_name: str) -> str:
           """Load full SKILL.md when skill is triggered."""
   ```

2. **SkillRegistry** (Index for matching)
   ```python
   class SkillRegistry:
       def match_query(self, query: str) -> list[str]:
           """Find skills whose description matches query."""

       def inject_into_context(self, agent_instructions: str) -> str:
           """Add skills section to agent system prompt."""
   ```

3. **Skills Directory Structure**
   ```
   skills/
   ├── smact-validation/
   │   ├── SKILL.md
   │   └── scripts/
   │       └── validate.py
   ├── chemeleon-prediction/
   │   ├── SKILL.md
   │   └── scripts/
   │       ├── predict_csp.py
   │       └── predict_dng.py
   ├── mace-calculation/
   │   ├── SKILL.md
   │   └── scripts/
   │       ├── relax.py
   │       └── formation_energy.py
   └── phase-diagram/
       ├── SKILL.md
       └── scripts/
           └── query_mp.py
   ```

### Example: SMACT Validation Skill

```yaml
---
name: smact-validation
description: >
  Validate chemical compositions for charge neutrality, electronegativity
  balance, and synthesizability using SMACT rules. Use when: (1) user
  provides a formula to analyze, (2) before structure prediction,
  (3) screening candidate compositions, (4) checking oxidation states.
---

# SMACT Validation

## Quick Usage

```bash
python scripts/validate.py "LiFePO4"
```

## What It Checks

1. **Charge neutrality**: Sum of oxidation states ≈ 0
2. **Electronegativity**: Anion more electronegative than cation
3. **Pauling rules**: Common oxidation states for each element

## Output Format

```json
{
  "formula": "LiFePO4",
  "valid": true,
  "oxidation_states": ["Li+1", "Fe+2", "P+5", "O-2"],
  "reasoning": "Charge balanced: 1(+1) + 1(+2) + 1(+5) + 4(-2) = 0"
}
```

## Provenance

Always record:
- Input formula (exactly as provided)
- SMACT version used
- Any assumptions about oxidation states
```

### Why This Replaces MCP

| MCP Approach | Skills + CLI Approach |
|--------------|----------------------|
| Start server process | No server needed |
| JSON-RPC protocol | Direct bash execution |
| Tool definitions in context (1000s tokens) | Skill summaries (~100 tokens each) |
| Fixed tool interface | Agent can modify scripts |
| Protocol overhead | Direct output capture |

**Token efficiency**: 52,000 tokens (MCP) → 1,200 tokens (CLI) = **43x more efficient**

---

## Implementation Roadmap

### Phase 1: Skills Infrastructure
- [ ] Port SkillLoader from Codex (Rust → Python)
- [ ] Create SkillRegistry with description matching
- [ ] Add skill injection to agent instructions

### Phase 2: Core Skills (Replace MCP)
- [ ] `smact-validation/` - Port from chemistry-unified-server
- [ ] `chemeleon-prediction/` - Port CSP and DNG tools
- [ ] `mace-calculation/` - Port energy and relaxation
- [ ] `phase-diagram/` - Port PyMatgen tools
- [ ] `visualization/` - Port 3Dmol and plotting

### Phase 3: Domain Skills
- [ ] `perovskites/` - Tolerance factor, tilting
- [ ] `battery-cathodes/` - Layered oxides, voltage
- [ ] `synthesis-feasibility/` - Sky agent knowledge

### Phase 4: Evaluation
- [ ] Skill-specific evaluation questions
- [ ] Provenance verification in skills
- [ ] Benchmark against MCP implementation

---

## References

- [Anthropic Agent Skills Blog](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Codex Skills Implementation](codex/codex-rs/core/src/skills/)
- [Simon Willison on MCP vs CLI](https://simonwillison.net/)
- [CrystaLyse V2 Vision](CRYSTALYSE_V2_VISION.md)
