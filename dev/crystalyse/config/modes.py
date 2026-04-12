"""
Mode configuration for CrystaLyse.

Defines the three operating modes (explore, validate, auto), a resolver that
accepts deprecated aliases (creative, rigorous, adaptive) with a
DeprecationWarning, and per-mode defaults for MCP server selection and
timeouts.
"""

from __future__ import annotations

import warnings
from enum import StrEnum


class Mode(StrEnum):
    """Canonical operating modes for CrystaLyse."""

    EXPLORE = "explore"
    VALIDATE = "validate"
    AUTO = "auto"


# Maps every accepted mode string (canonical + deprecated) to its Mode value.
MODE_ALIASES: dict[str, Mode] = {
    "explore": Mode.EXPLORE,
    "creative": Mode.EXPLORE,
    "validate": Mode.VALIDATE,
    "rigorous": Mode.VALIDATE,
    "auto": Mode.AUTO,
    "adaptive": Mode.AUTO,
}

# The subset of alias keys that are deprecated.
_DEPRECATED_ALIASES: set[str] = {"creative", "rigorous", "adaptive"}

# Which MCP chemistry server each mode prefers.
MODE_MCP_SERVERS: dict[Mode, str] = {
    Mode.EXPLORE: "chemistry_creative",
    Mode.VALIDATE: "chemistry_unified",
    Mode.AUTO: "chemistry_unified",
}

# Per-mode timeout defaults (seconds).
MODE_TIMEOUTS: dict[Mode, int] = {
    Mode.EXPLORE: 120,  # 2 minutes for fast exploration
    Mode.VALIDATE: 300,  # 5 minutes for comprehensive validation
    Mode.AUTO: 180,  # 3 minutes for balanced approach
}


def resolve_mode_name(user_input: str) -> Mode:
    """Normalise a user-supplied mode string to its canonical ``Mode`` value.

    Accepts both canonical names (``explore``, ``validate``, ``auto``) and
    deprecated aliases (``creative``, ``rigorous``, ``adaptive``).  Deprecated
    aliases emit a ``DeprecationWarning`` suggesting the canonical name.

    Raises ``ValueError`` for unknown mode strings with a list of valid modes.
    """
    key = user_input.strip().lower()
    mode = MODE_ALIASES.get(key)

    if mode is None:
        valid = sorted(MODE_ALIASES.keys())
        raise ValueError(f"Unknown mode {user_input!r}. Valid modes: {', '.join(valid)}")

    if key in _DEPRECATED_ALIASES:
        warnings.warn(
            f"--mode {key} is deprecated; use --mode {mode.value}. "
            "This alias will be removed in v2.0.",
            DeprecationWarning,
            stacklevel=2,
        )

    return mode
