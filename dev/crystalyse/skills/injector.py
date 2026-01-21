"""Skill Injector - Injects skill context into agent instructions.

Based on Codex's skills/render.rs, this module generates the skills
section that's added to agent system prompts.
"""

from .loader import SkillLoader, SkillMetadata
from .registry import SkillRegistry


class SkillInjector:
    """Injects skill information into agent context.

    Two modes:
    1. Summary injection: Always-on list of available skills (minimal tokens)
    2. Full injection: Load full SKILL.md when skill is triggered
    """

    # Template for the skills section (based on Codex render.rs)
    SKILLS_SECTION_TEMPLATE = """## Skills

A skill is a set of local instructions stored in a `SKILL.md` file. Below is the list of skills available. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.

### Available skills

{skill_list}

### How to use skills

- **Discovery**: The list above shows available skills (name + description + path). Skill bodies are on disk at the listed paths.
- **Trigger rules**: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description, you must use that skill. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- **Missing/blocked**: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- **How to use a skill (progressive disclosure)**:
  1. After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2. If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed; don't bulk-load everything.
  3. If `scripts/` exist, prefer running them instead of retyping code blocks.
  4. If `assets/` or templates exist, reuse them instead of recreating from scratch.
- **Coordination**: If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
- **Context hygiene**: Keep context small. Summarize long sections instead of pasting them. Only load extra files when needed.
- **Safety**: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue."""

    def __init__(
        self,
        loader: SkillLoader | None = None,
        registry: SkillRegistry | None = None,
    ):
        """Initialize the injector.

        Args:
            loader: SkillLoader instance
            registry: SkillRegistry instance
        """
        self.loader = loader or SkillLoader()
        self.registry = registry or SkillRegistry(self.loader)

    def render_skills_section(self, skills: list[SkillMetadata] | None = None) -> str:
        """Render the skills section for agent instructions.

        Args:
            skills: List of skills to include (default: all loaded skills)

        Returns:
            Formatted markdown skills section
        """
        if skills is None:
            outcome = self.loader.load_skills()
            skills = outcome.skills

        if not skills:
            return ""

        # Build skill list
        skill_lines = []
        for skill in skills:
            path_str = str(skill.path).replace("\\", "/")
            skill_lines.append(f"- {skill.name}: {skill.description} (file: {path_str})")

        skill_list = "\n".join(skill_lines)

        return self.SKILLS_SECTION_TEMPLATE.format(skill_list=skill_list)

    def inject_into_instructions(
        self,
        base_instructions: str,
        position: str = "after_tools",
    ) -> str:
        """Inject skills section into existing agent instructions.

        Args:
            base_instructions: Original agent system prompt
            position: Where to inject ("start", "end", "after_tools")

        Returns:
            Modified instructions with skills section
        """
        skills_section = self.render_skills_section()

        if not skills_section:
            return base_instructions

        if position == "start":
            return skills_section + "\n\n" + base_instructions
        elif position == "end":
            return base_instructions + "\n\n" + skills_section
        else:  # after_tools
            # Try to find a natural insertion point
            # Look for "## Tools" section and insert after it
            if "## Tools" in base_instructions:
                parts = base_instructions.split("## Tools", 1)
                # Find end of tools section (next ## or end)
                if len(parts) == 2:
                    remaining = parts[1]
                    if "\n## " in remaining:
                        tools_end_idx = remaining.index("\n## ")
                        return (
                            parts[0] +
                            "## Tools" +
                            remaining[:tools_end_idx] +
                            "\n\n" +
                            skills_section +
                            remaining[tools_end_idx:]
                        )

            # Fallback: append at end
            return base_instructions + "\n\n" + skills_section

    def get_triggered_skills(self, query: str, threshold: float = 0.5) -> list[SkillMetadata]:
        """Get skills that should be triggered for a query.

        Args:
            query: User query
            threshold: Minimum match score

        Returns:
            List of triggered skills
        """
        matches = self.registry.match_query(query, threshold=threshold)
        return [m.skill for m in matches]

    def get_skill_body_for_trigger(self, skill_name: str) -> str | None:
        """Get the full SKILL.md body when a skill is triggered.

        This is the progressive disclosure step - only load when needed.

        Args:
            skill_name: Name of the triggered skill

        Returns:
            Full skill body or None if not found
        """
        return self.loader.get_skill_body(skill_name)


def render_skills_for_agent(
    project_root: str | None = None,
    include_package_skills: bool = True,
) -> str:
    """Convenience function to render skills section for an agent.

    Args:
        project_root: Root directory to search for skills
        include_package_skills: Include bundled CrystaLyse skills

    Returns:
        Formatted skills section for agent instructions
    """
    from pathlib import Path

    # Find package skills directory
    package_skills = None
    if include_package_skills:
        # Check relative to this file
        this_dir = Path(__file__).parent
        possible_paths = [
            this_dir.parent / "skills",  # crystalyse/skills/
            this_dir.parent.parent / "skills",  # dev/skills/
        ]
        for path in possible_paths:
            if path.exists():
                package_skills = path
                break

    loader = SkillLoader(
        project_root=Path(project_root) if project_root else None,
        package_skills_dir=package_skills,
    )

    injector = SkillInjector(loader=loader)
    return injector.render_skills_section()
