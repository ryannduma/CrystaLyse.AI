"""Default-on plan mode heuristic (Feature 2.6).

Decides whether to auto-enter plan mode based on query complexity
signals.  The heuristic is OR-combined: any single signal firing
is sufficient to enter plan mode.

Override precedence (highest → lowest):
  1. ``--plan`` / ``--no-plan`` CLI flag
  2. ``/plan`` slash command
  3. ``settings.plan_mode`` (``"on"`` / ``"off"`` / ``"auto"``)
  4. Heuristic result from this module
"""

from __future__ import annotations

import re

from crystalyse.config.settings import CrystalyseSettings

# ---------------------------------------------------------------------------
# Signal patterns
# ---------------------------------------------------------------------------

#: Multi-candidate phrases that suggest a broad discovery task.
_MULTI_CANDIDATE_PATTERNS: list[str] = [
    "multiple",
    "several",
    "five",
    "list",
    "candidates",
    "set of",
    "family of",
]

#: Rigour / publication keywords.
_RIGOUR_KEYWORDS: list[str] = [
    "stability",
    "validate",
    "verify",
    "rigorous",
    "publication",
]

#: Threshold-like patterns (performance targets).
_THRESHOLD_RE = re.compile(
    r"""
    [><]                  # comparison operators
    | meV/atom            # energy per atom
    | GPa                 # pressure
    | \beV\b              # electronvolts (word boundary)
    | mAh/g               # battery capacity
    """,
    re.VERBOSE | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def should_auto_enter_plan_mode(
    query: str,
    settings: CrystalyseSettings | None = None,
    *,
    cli_plan_flag: bool | None = None,
) -> bool:
    """Decide whether the query should auto-enter plan mode.

    Parameters
    ----------
    query:
        The user's query string.
    settings:
        Loaded settings (provides ``plan_mode``).  If ``None``, defaults
        are used (``plan_mode="auto"``).
    cli_plan_flag:
        Explicit CLI override.  ``True`` = ``--plan``, ``False`` =
        ``--no-plan``, ``None`` = no override (defer to settings/heuristic).

    Returns
    -------
    bool
        ``True`` if the query should enter plan mode.
    """
    # --- Override layer 1: CLI flag ---
    if cli_plan_flag is True:
        return True
    if cli_plan_flag is False:
        return False

    # --- Override layer 3: settings ---
    if settings is None:
        settings = CrystalyseSettings()

    if settings.plan_mode == "on":
        return True
    if settings.plan_mode == "off":
        return False

    # --- Layer 4: heuristic (settings.plan_mode == "auto") ---
    return _run_heuristic(query)


def _run_heuristic(query: str) -> bool:
    """OR-combined heuristic signals.  Any one firing → plan mode on."""
    q_lower = query.lower()

    # Signal 1: query length > 20 words
    if len(query.split()) > 20:
        return True

    # Signal 2: multi-candidate phrases
    for pattern in _MULTI_CANDIDATE_PATTERNS:
        if pattern in q_lower:
            return True

    # Signal 3: rigour / publication keywords
    for keyword in _RIGOUR_KEYWORDS:
        if keyword in q_lower:
            return True

    # Signal 4: threshold patterns
    if _THRESHOLD_RE.search(query):
        return True

    return False
