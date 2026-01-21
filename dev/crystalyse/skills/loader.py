"""Skill Loader - Python port of Codex's skills/loader.rs.

This module scans skill directories and loads skill metadata (frontmatter).
Full skill bodies are loaded on-demand when skills are triggered.

Skill Scopes (in priority order):
1. Project: .crystalyse/skills/ (project-specific)
2. User: ~/.crystalyse/skills/ (user-wide)
3. System: ~/.crystalyse/skills/.system/ (built-in)
4. Package: <package>/skills/ (bundled with CrystaLyse)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SkillScope(Enum):
    """Scope determines where a skill was loaded from and its priority."""
    PROJECT = "project"   # .crystalyse/skills/
    USER = "user"         # ~/.crystalyse/skills/
    SYSTEM = "system"     # ~/.crystalyse/skills/.system/
    PACKAGE = "package"   # Bundled with CrystaLyse


@dataclass
class SkillMetadata:
    """Skill metadata extracted from YAML frontmatter.

    This is all that's loaded initially - the full body is loaded on-demand.
    """
    name: str
    description: str
    path: Path
    scope: SkillScope
    # Optional fields
    version: str | None = None
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    # Raw frontmatter for extensions
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillLoadOutcome:
    """Result of loading skills from all directories."""
    skills: list[SkillMetadata]
    errors: list[str]
    warnings: list[str]

    @property
    def total_loaded(self) -> int:
        return len(self.skills)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class SkillLoader:
    """Loads skills from configured directories.

    Implements progressive disclosure:
    1. Only loads YAML frontmatter initially (name + description)
    2. Full SKILL.md body loaded on-demand via get_skill_body()
    """

    # Regex to extract YAML frontmatter from SKILL.md
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )

    def __init__(
        self,
        project_root: Path | None = None,
        user_home: Path | None = None,
        package_skills_dir: Path | None = None,
    ):
        """Initialize the skill loader.

        Args:
            project_root: Root of the current project (for .crystalyse/skills/)
            user_home: User's home directory (default: ~)
            package_skills_dir: Path to bundled skills in the CrystaLyse package
        """
        self.project_root = project_root or Path.cwd()
        self.user_home = user_home or Path.home()
        self.package_skills_dir = package_skills_dir

        # Cache for loaded skills
        self._skills_cache: dict[str, SkillMetadata] = {}
        self._body_cache: dict[str, str] = {}

    def get_skill_roots(self) -> list[tuple[SkillScope, Path]]:
        """Get all skill directories in priority order."""
        roots = []

        # Project scope: .crystalyse/skills/
        project_skills = self.project_root / ".crystalyse" / "skills"
        if project_skills.exists():
            roots.append((SkillScope.PROJECT, project_skills))

        # Also check dev/skills/ for CrystaLyse development
        dev_skills = self.project_root / "dev" / "skills"
        if dev_skills.exists():
            roots.append((SkillScope.PROJECT, dev_skills))

        # User scope: ~/.crystalyse/skills/
        user_skills = self.user_home / ".crystalyse" / "skills"
        if user_skills.exists():
            roots.append((SkillScope.USER, user_skills))

        # System scope: ~/.crystalyse/skills/.system/
        system_skills = self.user_home / ".crystalyse" / "skills" / ".system"
        if system_skills.exists():
            roots.append((SkillScope.SYSTEM, system_skills))

        # Package scope: bundled skills
        if self.package_skills_dir and self.package_skills_dir.exists():
            roots.append((SkillScope.PACKAGE, self.package_skills_dir))

        return roots

    def load_skills(self) -> SkillLoadOutcome:
        """Load skills from all configured directories.

        Returns:
            SkillLoadOutcome with loaded skills and any errors
        """
        skills = []
        errors = []
        warnings = []
        seen_names: set[str] = set()

        for scope, root in self.get_skill_roots():
            logger.debug(f"Scanning skill root: {root} (scope: {scope.value})")

            if not root.is_dir():
                continue

            for skill_dir in root.iterdir():
                if not skill_dir.is_dir():
                    continue

                # Skip hidden directories (except .system which is a root)
                if skill_dir.name.startswith("."):
                    continue

                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    warnings.append(f"Directory {skill_dir} has no SKILL.md")
                    continue

                try:
                    metadata = self._load_skill_frontmatter(skill_md, scope)

                    # Check for duplicates (first one wins by scope priority)
                    if metadata.name in seen_names:
                        warnings.append(
                            f"Duplicate skill '{metadata.name}' at {skill_md}, "
                            f"using earlier definition"
                        )
                        continue

                    skills.append(metadata)
                    seen_names.add(metadata.name)
                    self._skills_cache[metadata.name] = metadata

                except Exception as e:
                    errors.append(f"Failed to load {skill_md}: {e}")

        logger.info(f"Loaded {len(skills)} skills from {len(self.get_skill_roots())} roots")

        return SkillLoadOutcome(
            skills=skills,
            errors=errors,
            warnings=warnings,
        )

    def _load_skill_frontmatter(self, skill_md: Path, scope: SkillScope) -> SkillMetadata:
        """Load only the YAML frontmatter from a SKILL.md file.

        Args:
            skill_md: Path to SKILL.md
            scope: Which scope this skill belongs to

        Returns:
            SkillMetadata with frontmatter data
        """
        content = skill_md.read_text(encoding="utf-8")

        # Extract frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise ValueError(f"No YAML frontmatter found in {skill_md}")

        frontmatter_str = match.group(1)

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in frontmatter: {e}") from e

        if not isinstance(frontmatter, dict):
            raise ValueError("Frontmatter must be a YAML dictionary")

        # Required fields
        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not name:
            raise ValueError("Frontmatter missing required 'name' field")
        if not description:
            raise ValueError("Frontmatter missing required 'description' field")

        return SkillMetadata(
            name=name,
            description=description.strip(),
            path=skill_md,
            scope=scope,
            version=frontmatter.get("version"),
            author=frontmatter.get("author"),
            tags=frontmatter.get("tags", []),
            raw_frontmatter=frontmatter,
        )

    def get_skill_body(self, skill_name: str) -> str | None:
        """Load the full body of a SKILL.md (on-demand).

        This is called when a skill is actually triggered.

        Args:
            skill_name: Name of the skill to load

        Returns:
            Full markdown body (without frontmatter), or None if not found
        """
        # Check cache
        if skill_name in self._body_cache:
            return self._body_cache[skill_name]

        # Find skill metadata
        metadata = self._skills_cache.get(skill_name)
        if not metadata:
            # Try loading skills if not cached
            outcome = self.load_skills()
            metadata = self._skills_cache.get(skill_name)
            if not metadata:
                return None

        # Read full file
        content = metadata.path.read_text(encoding="utf-8")

        # Strip frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if match:
            body = content[match.end():]
        else:
            body = content

        # Cache and return
        self._body_cache[skill_name] = body.strip()
        return self._body_cache[skill_name]

    def get_skill(self, skill_name: str) -> SkillMetadata | None:
        """Get metadata for a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            SkillMetadata or None if not found
        """
        if skill_name not in self._skills_cache:
            self.load_skills()
        return self._skills_cache.get(skill_name)

    def list_skills(self) -> list[str]:
        """List all available skill names."""
        if not self._skills_cache:
            self.load_skills()
        return list(self._skills_cache.keys())
