"""TOML-based user preferences for Crystalyse.

Supports configuration at ~/.crystalyse/config.toml with sections:
- [analysis]: default_mode, parallel_batch_size, max_candidates
- [display]: verbosity, enable_html_viz
- [databases]: preferred_providers, max_results_per_query
- [cache]: max_discoveries, auto_cleanup_days
- [skills]: script_timeout_secs, enable_sandboxing
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".crystalyse" / "config.toml"


@dataclass
class AnalysisPrefs:
    """Analysis preferences."""

    default_mode: str = "creative"  # "creative" or "rigorous"
    parallel_batch_size: int = 10
    max_candidates: int = 100


@dataclass
class DisplayPrefs:
    """Display and output preferences."""

    verbosity: str = "normal"  # "quiet", "normal", "verbose"
    enable_html_viz: bool = False


@dataclass
class DatabasePrefs:
    """Database query preferences."""

    preferred_providers: list[str] = field(default_factory=lambda: ["mp", "aflow", "oqmd"])
    max_results_per_query: int = 50


@dataclass
class CachePrefs:
    """Discovery cache preferences."""

    max_discoveries: int = 10000
    auto_cleanup_days: int = 90


@dataclass
class SkillsPrefs:
    """Skills execution preferences."""

    script_timeout_secs: int = 300
    enable_sandboxing: bool = True


@dataclass
class UserPreferences:
    """Complete user preferences configuration."""

    analysis: AnalysisPrefs = field(default_factory=AnalysisPrefs)
    display: DisplayPrefs = field(default_factory=DisplayPrefs)
    databases: DatabasePrefs = field(default_factory=DatabasePrefs)
    cache: CachePrefs = field(default_factory=CachePrefs)
    skills: SkillsPrefs = field(default_factory=SkillsPrefs)


def _merge_dict(dataclass_instance: Any, data: dict[str, Any]) -> Any:
    """Merge dictionary into dataclass instance, handling nested structures."""
    for key, value in data.items():
        if hasattr(dataclass_instance, key):
            setattr(dataclass_instance, key, value)
    return dataclass_instance


def load_preferences(config_path: Path = DEFAULT_CONFIG_PATH) -> UserPreferences:
    """Load user preferences from TOML file.

    Args:
        config_path: Path to config.toml file

    Returns:
        UserPreferences with loaded values (defaults if file doesn't exist)
    """
    if not config_path.exists():
        return UserPreferences()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to parse {config_path}: {e}")
        return UserPreferences()

    prefs = UserPreferences()

    # Merge each section
    if "analysis" in data:
        prefs.analysis = _merge_dict(AnalysisPrefs(), data["analysis"])
    if "display" in data:
        prefs.display = _merge_dict(DisplayPrefs(), data["display"])
    if "databases" in data:
        prefs.databases = _merge_dict(DatabasePrefs(), data["databases"])
    if "cache" in data:
        prefs.cache = _merge_dict(CachePrefs(), data["cache"])
    if "skills" in data:
        prefs.skills = _merge_dict(SkillsPrefs(), data["skills"])

    return prefs


def save_preferences(prefs: UserPreferences, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Save user preferences to TOML file.

    Args:
        prefs: UserPreferences to save
        config_path: Path to config.toml file
    """

    config_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Crystalyse User Preferences",
        "# https://github.com/your-repo/crystalyse",
        "",
        "[analysis]",
        f'default_mode = "{prefs.analysis.default_mode}"  # "creative" or "rigorous"',
        f"parallel_batch_size = {prefs.analysis.parallel_batch_size}",
        f"max_candidates = {prefs.analysis.max_candidates}",
        "",
        "[display]",
        f'verbosity = "{prefs.display.verbosity}"  # "quiet", "normal", "verbose"',
        f"enable_html_viz = {str(prefs.display.enable_html_viz).lower()}",
        "",
        "[databases]",
        f"preferred_providers = {prefs.databases.preferred_providers}".replace("'", '"'),
        f"max_results_per_query = {prefs.databases.max_results_per_query}",
        "",
        "[cache]",
        f"max_discoveries = {prefs.cache.max_discoveries}",
        f"auto_cleanup_days = {prefs.cache.auto_cleanup_days}",
        "",
        "[skills]",
        f"script_timeout_secs = {prefs.skills.script_timeout_secs}",
        f"enable_sandboxing = {str(prefs.skills.enable_sandboxing).lower()}",
    ]

    config_path.write_text("\n".join(lines) + "\n")


def get_default_config_template() -> str:
    """Get a default config.toml template as a string."""
    return """# Crystalyse User Preferences
# https://github.com/your-repo/crystalyse

[analysis]
default_mode = "creative"  # "creative" or "rigorous"
parallel_batch_size = 10
max_candidates = 100

[display]
verbosity = "normal"  # "quiet", "normal", "verbose"
enable_html_viz = false

[databases]
preferred_providers = ["mp", "aflow", "oqmd"]
max_results_per_query = 50

[cache]
max_discoveries = 10000
auto_cleanup_days = 90

[skills]
script_timeout_secs = 300
enable_sandboxing = true
"""
