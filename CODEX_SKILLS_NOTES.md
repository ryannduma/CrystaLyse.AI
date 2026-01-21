# Codex, Skills, and MCP Server Notes

## Overview

These notes capture how OpenAI's Codex agent handles skills and how it can integrate with other agents via MCP.

---

## Codex Architecture

**Codex CLI** is OpenAI's local coding agent:
- Built in Rust (`codex-rs/`) for speed
- Runs locally with a full-screen TUI
- Open source: https://github.com/openai/codex
- Powered by GPT-5-Codex (optimized for agentic coding)

---

## Skill Support in Codex

### Directory Structure

Codex reads skills from `.codex/skills/` directories:

```
.codex/
└── skills/
    ├── code-change-verification/
    │   └── SKILL.md
    ├── pr-draft-summary/
    │   └── SKILL.md
    ├── examples-auto-run/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── run.sh
    └── test-coverage-improver/
        └── SKILL.md
```

### `$skill-name` Invocation Syntax

In Codex, skills are invoked by typing `$skill-name` in the chat:

```
$code-change-verification
```

This triggers Codex to:
1. Find `.codex/skills/code-change-verification/SKILL.md`
2. Load the instructions into context
3. Execute the skill's workflow

### Example from OpenAI Agents SDK Repo

From their `AGENTS.md`:
```markdown
## Mandatory Skill Usage

### `$code-change-verification`

Run `$code-change-verification` before marking work complete when changes
affect runtime code, tests, or build/test behavior.

Run it when you change:
- `src/agents/` (library code) or shared utilities
- `tests/` or add or modify snapshot tests
- `examples/`
- Build or test configuration
```

### SKILL.md Format

Same format as Anthropic's Agent Skills:

```yaml
---
name: examples-auto-run
description: Run python examples in auto mode with logging, rerun helpers, and background control.
---

# examples-auto-run

## What it does
- Runs `uv run examples/run_examples.py` with auto-input/auto-approve
- Per-example logs under `.tmp/examples-start-logs/`
...
```

---

## Codex as MCP Server

Codex can run as an MCP server, allowing other agents to call it as a tool.

### Starting Codex as MCP Server

```bash
codex --mcp
```

### Tools Exposed

When running as MCP server, Codex exposes two tools:

| Tool | Description |
|------|-------------|
| `codex` | Run a Codex session. Accepts configuration parameters. |
| `codex-reply` | Continue a conversation using a thread ID. |

### Architecture: Agents Calling Agents

```
┌─────────────────────┐
│  Orchestrator Agent │
│  (e.g., CrystaLyse) │
│                     │
│  "Implement feature"│
└─────────┬───────────┘
          │ MCP call
          ▼
┌─────────────────────┐
│  Codex MCP Server   │
│                     │
│  - codex tool       │  ← "Run a Codex session"
│  - codex-reply tool │  ← "Continue conversation"
└─────────────────────┘
          │
          ▼
    [Codex writes code, runs tests]
          │
          ▼
    [Result returned to orchestrator]
```

### Use Case Example

A CrystaLyse workflow where:
1. CrystaLyse discovers a material needs a custom analysis script
2. CrystaLyse calls Codex via MCP: "Write a Python script to calculate band structure"
3. Codex writes the code, runs tests, validates
4. CrystaLyse receives the script and continues its materials workflow

This enables **separation of concerns**:
- CrystaLyse: Materials science expertise
- Codex: Code implementation expertise

---

## OpenAI Agents SDK vs Codex

| Component | What it is | Skill Support |
|-----------|------------|---------------|
| **Codex CLI** | Local coding agent (Rust) | Native (`.codex/skills/`) |
| **OpenAI Agents SDK** | Python SDK for building agents | Not built-in |
| **CrystaLyse** | Built on Agents SDK | Must implement own |

**Key insight**: The OpenAI Agents SDK is lower-level infrastructure. It provides tools, handoffs, and tracing, but skill loading must be implemented by the application.

---

## Implications for CrystaLyse

### Option 1: Implement Custom Skill Loading

Build a `SkillRegistry` similar to what Codex does internally:

```python
class SkillRegistry:
    def load_frontmatter(self, skill_dir: Path) -> dict:
        """Load just name + description for context efficiency"""

    def match_skills(self, query: str) -> list[str]:
        """Match relevant skills based on description"""

    def inject_skill_context(self, agent: Agent, skills: list[str]):
        """Add skill body to agent instructions"""
```

### Option 2: Use Codex as MCP Server

Delegate coding tasks to Codex while CrystaLyse handles materials science:

```python
# In CrystaLyse MCP config
mcp_servers = {
    "codex": {
        "command": ["codex", "--mcp"],
        "tools": ["codex", "codex-reply"]
    }
}
```

### Option 3: Hybrid Approach

- CrystaLyse skills for materials science workflows
- Codex MCP for code generation tasks
- Best of both worlds

---

## References

- [Codex CLI Documentation](https://developers.openai.com/codex/cli/)
- [Codex CLI Features](https://developers.openai.com/codex/cli/features/)
- [Use Codex with Agents SDK](https://developers.openai.com/codex/guides/agents-sdk/)
- [Custom Instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Codex GitHub Repository](https://github.com/openai/codex)
- [Anthropic Agent Skills](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
