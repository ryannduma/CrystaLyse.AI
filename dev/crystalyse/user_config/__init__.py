"""User configuration package for Crystalyse.

Provides TOML-based user preferences at ~/.crystalyse/config.toml.
"""

from .preferences import (
    DEFAULT_CONFIG_PATH,
    AnalysisPrefs,
    CachePrefs,
    DatabasePrefs,
    DisplayPrefs,
    SkillsPrefs,
    UserPreferences,
    get_default_config_template,
    load_preferences,
    save_preferences,
)

__all__ = [
    "UserPreferences",
    "AnalysisPrefs",
    "DisplayPrefs",
    "DatabasePrefs",
    "CachePrefs",
    "SkillsPrefs",
    "load_preferences",
    "save_preferences",
    "get_default_config_template",
    "DEFAULT_CONFIG_PATH",
]
