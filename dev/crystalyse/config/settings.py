"""CrystaLyse project settings loaded from ``.crystalyse/config.toml``.

Settings are loaded with three-layer precedence (highest → lowest):

1. **Project-level**: ``.crystalyse/config.toml`` in the project root.
2. **User-level**: ``~/.crystalyse/config.toml`` in the user's home.
3. **Built-in defaults**: the ``CrystalyseSettings`` dataclass defaults.

Use ``load_settings()`` as the single entry point — it handles discovery,
merging, and fallback to defaults when no config file exists.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal

from .workspace import find_crystalyse_root

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrystalyseSettings:
    """Runtime settings resolved from ``config.toml`` files.

    All fields have sensible defaults so the system works out of the box
    without any configuration.
    """

    #: Registry key for the default model (resolved by ``resolve_model_name``).
    default_model: str = "openai_o4_mini"

    #: Default operating mode (canonical name).
    default_mode: str = "explore"

    #: Whether plan mode is active: ``"on"`` | ``"off"`` | ``"auto"``.
    #: ``"auto"`` enables the default-on heuristic from PR 2 Feature 2.6.
    plan_mode: Literal["on", "off", "auto"] = "auto"

    #: Override for the plans directory.  ``None`` means
    #: ``<project_root>/.crystalyse/plans/``.
    plans_directory: str | None = None

    #: Number of days before plan files are eligible for cleanup.
    plans_cleanup_days: int = 30


def _load_toml(path: Path) -> dict:
    """Read a TOML file and return its contents as a dict.

    Returns an empty dict if the file doesn't exist or can't be parsed.
    """
    if not path.is_file():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.warning("Failed to parse %s: %s", path, e)
        return {}


def _merge_into_settings(base: dict, override: dict) -> dict:
    """Merge *override* into *base* (shallow, override wins)."""
    merged = {**base, **override}
    return merged


def load_settings(
    *,
    project_root: Path | None = None,
    user_home: Path | None = None,
) -> CrystalyseSettings:
    """Load settings with three-layer precedence.

    Parameters
    ----------
    project_root:
        Explicit project root.  If ``None``, calls
        ``find_crystalyse_root()`` to discover it.
    user_home:
        Override for the user home directory (useful for testing).
        Defaults to ``Path.home()``.

    Returns
    -------
    CrystalyseSettings
        Merged settings.  If no config files exist, returns defaults.
    """
    # Layer 3: built-in defaults (from the dataclass).
    settings_fields = {f.name for f in fields(CrystalyseSettings)}
    merged: dict = {}

    # Layer 2: user-level config.
    home = user_home or Path.home()
    user_config_path = home / ".crystalyse" / "config.toml"
    user_raw = _load_toml(user_config_path)
    # Only keep keys that are valid settings fields.
    user_filtered = {k: v for k, v in user_raw.items() if k in settings_fields}
    merged = _merge_into_settings(merged, user_filtered)

    # Layer 1: project-level config (highest precedence).
    root = project_root or find_crystalyse_root()
    if root is not None:
        project_config_path = root / ".crystalyse" / "config.toml"
        project_raw = _load_toml(project_config_path)
        project_filtered = {k: v for k, v in project_raw.items() if k in settings_fields}
        merged = _merge_into_settings(merged, project_filtered)

    # Construct the dataclass with merged values (unrecognised keys dropped).
    return CrystalyseSettings(**merged)
