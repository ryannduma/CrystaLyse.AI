"""CrystaLyse Skills System V2 - Skills + CLI architecture for materials science.

This module provides skill loading, registry, injection, and execution capabilities.

Skills are modular packages that extend CrystaLyse's capabilities with:
- Specialized workflows (multi-step procedures)
- Executable scripts for specific tasks
- Domain expertise (perovskites, batteries, synthesis)
- Bundled resources (references, assets)
"""

from .executor import execute_skill_script, get_available_skills, list_skill_scripts
from .injector import SkillInjector
from .loader import SkillLoader, SkillMetadata, SkillScope
from .registry import SkillRegistry

__all__ = [
    # Core classes
    "SkillLoader",
    "SkillMetadata",
    "SkillScope",
    "SkillRegistry",
    "SkillInjector",
    # Executor functions
    "execute_skill_script",
    "get_available_skills",
    "list_skill_scripts",
]
