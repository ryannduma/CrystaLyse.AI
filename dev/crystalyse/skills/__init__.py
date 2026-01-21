"""CrystaLyse Skills System - Skills + CLI architecture for materials science.

This module provides skill loading, registry, and injection capabilities
based on the Codex/Anthropic skills paradigm.

Skills are modular packages that extend CrystaLyse's capabilities with:
- Specialized workflows (multi-step procedures)
- Tool integrations (CLI scripts, Python modules)
- Domain expertise (perovskites, batteries, synthesis)
- Bundled resources (references, assets)
"""

from .injector import SkillInjector
from .loader import SkillLoader, SkillMetadata, SkillScope
from .registry import SkillRegistry

__all__ = [
    "SkillLoader",
    "SkillMetadata",
    "SkillScope",
    "SkillRegistry",
    "SkillInjector",
]
