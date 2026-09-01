"""Resolution rules for user-supplied mode strings, and the mode -> server map.

Two things are pinned here:

* ``resolve_mode_name`` -- the single entry point the CLI and the agent bridge
  use to turn whatever the user typed into a canonical ``Mode``.  Canonical
  names pass through silently, the three deprecated aliases resolve *and* warn,
  and anything else raises rather than falling back to a default.
* The cross-module invariant that ``MODE_MCP_SERVERS`` only ever names servers
  ``CrystaLyseConfig`` actually knows about.  ``config.get_server_config()``
  raises ``ValueError`` for an unknown server name, so a typo in either mapping
  would only surface when a mode is selected at runtime.

Companion to ``test_modes.py``, which covers the ``Mode`` enum, the per-mode
timeouts and old-vs-new behavioural equivalence.
"""

from __future__ import annotations

import warnings

import pytest

from crystalyse.config import CrystaLyseConfig
from crystalyse.config.modes import (
    _DEPRECATED_ALIASES,
    MODE_ALIASES,
    MODE_MCP_SERVERS,
    Mode,
    resolve_mode_name,
)

# ---------------------------------------------------------------------------
# Canonical names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        ("explore", Mode.EXPLORE),
        ("validate", Mode.VALIDATE),
        ("auto", Mode.AUTO),
    ],
    ids=["explore", "validate", "auto"],
)
def test_canonical_name_resolves_to_its_mode(name: str, expected: Mode) -> None:
    assert resolve_mode_name(name) is expected


@pytest.mark.parametrize(
    "name",
    ["explore", "validate", "auto"],
    ids=["explore", "validate", "auto"],
)
def test_canonical_name_does_not_warn(name: str) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolve_mode_name(name)
    assert [str(w.message) for w in caught] == []


@pytest.mark.parametrize(
    "typed",
    ["EXPLORE", "Explore", "  explore  ", "\texplore\n"],
    ids=["upper", "title", "padded", "tabbed"],
)
def test_case_and_surrounding_whitespace_are_normalised(typed: str) -> None:
    assert resolve_mode_name(typed) is Mode.EXPLORE


# ---------------------------------------------------------------------------
# Deprecated aliases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alias, expected",
    [
        ("creative", Mode.EXPLORE),
        ("rigorous", Mode.VALIDATE),
        ("adaptive", Mode.AUTO),
    ],
    ids=["creative-is-explore", "rigorous-is-validate", "adaptive-is-auto"],
)
def test_deprecated_alias_resolves_to_its_canonical_mode(alias: str, expected: Mode) -> None:
    with pytest.warns(DeprecationWarning):
        assert resolve_mode_name(alias) is expected


@pytest.mark.parametrize(
    "alias, expected",
    [
        ("creative", Mode.EXPLORE),
        ("rigorous", Mode.VALIDATE),
        ("adaptive", Mode.AUTO),
    ],
    ids=["creative-is-explore", "rigorous-is-validate", "adaptive-is-auto"],
)
def test_deprecation_warning_names_the_replacement(alias: str, expected: Mode) -> None:
    with pytest.warns(DeprecationWarning) as caught:
        resolve_mode_name(alias)
    message = str(caught[0].message)
    assert f"--mode {expected.value}" in message
    assert alias in message


def test_deprecated_alias_still_warns_when_typed_in_upper_case() -> None:
    """The alias check happens after normalisation, so casing must not hide it."""
    with pytest.warns(DeprecationWarning):
        assert resolve_mode_name("RIGOROUS") is Mode.VALIDATE


# ---------------------------------------------------------------------------
# The alias table itself
# ---------------------------------------------------------------------------


def test_alias_table_accepts_exactly_the_canonical_and_deprecated_names() -> None:
    assert set(MODE_ALIASES) == {m.value for m in Mode} | _DEPRECATED_ALIASES


def test_deprecated_aliases_are_not_canonical_names() -> None:
    """A name cannot be both current and deprecated: resolving one would warn."""
    assert _DEPRECATED_ALIASES.isdisjoint({m.value for m in Mode})


def test_alias_table_keys_are_already_normalised() -> None:
    """``resolve_mode_name`` lower-cases and strips before lookup, so a key that
    is not itself normalised would be unreachable."""
    assert all(key == key.strip().lower() for key in MODE_ALIASES)


def test_every_alias_resolves_to_a_real_mode_member() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolved = {alias: resolve_mode_name(alias) for alias in MODE_ALIASES}
    assert all(isinstance(mode, Mode) for mode in resolved.values())


# ---------------------------------------------------------------------------
# Unknown input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unknown",
    ["", "   ", "explor", "fast", "explore validate", "explore,validate"],
    ids=["empty", "whitespace", "typo", "invented", "two-modes", "comma-joined"],
)
def test_unknown_name_raises_value_error(unknown: str) -> None:
    with pytest.raises(ValueError, match="Unknown mode"):
        resolve_mode_name(unknown)


def test_unknown_name_error_lists_every_accepted_name() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_mode_name("fast")
    message = str(excinfo.value)
    for accepted in MODE_ALIASES:
        assert accepted in message


def test_unknown_name_error_quotes_what_the_user_typed() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_mode_name("Fast Mode")
    assert "'Fast Mode'" in str(excinfo.value)


# ---------------------------------------------------------------------------
# MODE_MCP_SERVERS must name servers CrystaLyseConfig can start
# ---------------------------------------------------------------------------


def test_every_mode_maps_to_a_server_config_knows() -> None:
    available = set(CrystaLyseConfig().mcp_servers)
    assert {MODE_MCP_SERVERS[mode] for mode in Mode} <= available


def test_no_mode_is_missing_a_server() -> None:
    assert set(MODE_MCP_SERVERS) == set(Mode)


@pytest.mark.parametrize(
    "alias",
    sorted(MODE_ALIASES),
    ids=sorted(MODE_ALIASES),
)
def test_server_for_a_resolved_alias_is_one_config_knows(alias: str) -> None:
    """Whatever the user types, the resulting server name must be one
    ``get_server_config`` accepts -- it rejects unknown names outright.
    Membership is asserted rather than calling it, because the call also stats
    the server directory and the interpreter path."""
    config = CrystaLyseConfig()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mode = resolve_mode_name(alias)
    assert MODE_MCP_SERVERS[mode] in config.mcp_servers
