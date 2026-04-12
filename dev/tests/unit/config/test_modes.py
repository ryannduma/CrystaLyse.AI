"""Tests for the mode configuration and resolve_mode_name() pipeline.

Covers:
- Canonical mode resolution (explore, validate, auto)
- Deprecated alias resolution with DeprecationWarning (creative, rigorous, adaptive)
- ValueError on unknown modes
- Behavioural equivalence: old mode name produces the same bridge config as its
  canonical equivalent
"""

from __future__ import annotations

import warnings

import pytest

from crystalyse.config.modes import (
    _DEPRECATED_ALIASES,
    MODE_ALIASES,
    MODE_MCP_SERVERS,
    MODE_TIMEOUTS,
    Mode,
    resolve_mode_name,
)

# ---------------------------------------------------------------------------
# Mode enum basics
# ---------------------------------------------------------------------------


class TestModeEnum:
    def test_mode_has_three_members(self) -> None:
        assert len(Mode) == 3

    def test_mode_values_are_canonical(self) -> None:
        assert Mode.EXPLORE.value == "explore"
        assert Mode.VALIDATE.value == "validate"
        assert Mode.AUTO.value == "auto"

    def test_mode_is_str_enum(self) -> None:
        assert isinstance(Mode.EXPLORE, str)
        assert Mode.EXPLORE == "explore"


# ---------------------------------------------------------------------------
# resolve_mode_name — canonical names
# ---------------------------------------------------------------------------


class TestResolveModeNameCanonical:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("explore", Mode.EXPLORE),
            ("validate", Mode.VALIDATE),
            ("auto", Mode.AUTO),
        ],
    )
    def test_canonical_names_resolve(self, name: str, expected: Mode) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_mode_name(name)
            assert result is expected
            # No deprecation warning for canonical names
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) == 0

    def test_canonical_names_are_case_insensitive(self) -> None:
        assert resolve_mode_name("EXPLORE") is Mode.EXPLORE
        assert resolve_mode_name("Validate") is Mode.VALIDATE
        assert resolve_mode_name("  auto  ") is Mode.AUTO


# ---------------------------------------------------------------------------
# resolve_mode_name — deprecated aliases
# ---------------------------------------------------------------------------


class TestResolveModeNameDeprecated:
    @pytest.mark.parametrize(
        "alias, expected",
        [
            ("creative", Mode.EXPLORE),
            ("rigorous", Mode.VALIDATE),
            ("adaptive", Mode.AUTO),
        ],
    )
    def test_deprecated_aliases_resolve_correctly(self, alias: str, expected: Mode) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_mode_name(alias)
            assert result is expected
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) == 1

    def test_deprecation_warning_message(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            resolve_mode_name("creative")
            msg = str(w[0].message)
            assert "deprecated" in msg.lower()
            assert "explore" in msg
            assert "v2.0" in msg

    def test_deprecated_aliases_set_is_complete(self) -> None:
        assert _DEPRECATED_ALIASES == {"creative", "rigorous", "adaptive"}


# ---------------------------------------------------------------------------
# resolve_mode_name — error handling
# ---------------------------------------------------------------------------


class TestResolveModeNameErrors:
    def test_unknown_mode_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown mode"):
            resolve_mode_name("xyz")

    def test_error_message_lists_valid_modes(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            resolve_mode_name("nonsense")
        msg = str(exc_info.value)
        for valid in MODE_ALIASES:
            assert valid in msg

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError):
            resolve_mode_name("")


# ---------------------------------------------------------------------------
# MODE_ALIASES completeness
# ---------------------------------------------------------------------------


class TestModeAliases:
    def test_all_canonical_names_present(self) -> None:
        for mode in Mode:
            assert mode.value in MODE_ALIASES
            assert MODE_ALIASES[mode.value] is mode

    def test_all_deprecated_aliases_present(self) -> None:
        for alias in _DEPRECATED_ALIASES:
            assert alias in MODE_ALIASES

    def test_alias_count(self) -> None:
        # 3 canonical + 3 deprecated = 6
        assert len(MODE_ALIASES) == 6


# ---------------------------------------------------------------------------
# Per-mode defaults (MCP servers, timeouts)
# ---------------------------------------------------------------------------


class TestModeDefaults:
    def test_every_mode_has_mcp_server(self) -> None:
        for mode in Mode:
            assert mode in MODE_MCP_SERVERS

    def test_every_mode_has_timeout(self) -> None:
        for mode in Mode:
            assert mode in MODE_TIMEOUTS
            assert isinstance(MODE_TIMEOUTS[mode], int)
            assert MODE_TIMEOUTS[mode] > 0

    def test_explore_uses_creative_server(self) -> None:
        assert MODE_MCP_SERVERS[Mode.EXPLORE] == "chemistry_creative"

    def test_validate_uses_unified_server(self) -> None:
        assert MODE_MCP_SERVERS[Mode.VALIDATE] == "chemistry_unified"


# ---------------------------------------------------------------------------
# Behavioural equivalence: old name vs canonical name
# ---------------------------------------------------------------------------


class TestBehaviouralEquivalence:
    """Every deprecated alias must produce the exact same resolved state as its
    canonical equivalent.  This is the §2.10 acceptance criterion: parametrized
    test asserting byte-identical bridge config for old and new mode names.
    """

    @pytest.mark.parametrize(
        "old_name, new_name",
        [
            ("creative", "explore"),
            ("rigorous", "validate"),
            ("adaptive", "auto"),
        ],
    )
    def test_old_and_new_resolve_to_same_mode(self, old_name: str, new_name: str) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            old_mode = resolve_mode_name(old_name)
            new_mode = resolve_mode_name(new_name)
        assert old_mode is new_mode

    @pytest.mark.parametrize(
        "old_name, new_name",
        [
            ("creative", "explore"),
            ("rigorous", "validate"),
            ("adaptive", "auto"),
        ],
    )
    def test_old_and_new_get_same_mcp_server(self, old_name: str, new_name: str) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            old_mode = resolve_mode_name(old_name)
            new_mode = resolve_mode_name(new_name)
        assert MODE_MCP_SERVERS[old_mode] == MODE_MCP_SERVERS[new_mode]

    @pytest.mark.parametrize(
        "old_name, new_name",
        [
            ("creative", "explore"),
            ("rigorous", "validate"),
            ("adaptive", "auto"),
        ],
    )
    def test_old_and_new_get_same_timeout(self, old_name: str, new_name: str) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            old_mode = resolve_mode_name(old_name)
            new_mode = resolve_mode_name(new_name)
        assert MODE_TIMEOUTS[old_mode] == MODE_TIMEOUTS[new_mode]

    @pytest.mark.parametrize(
        "old_name, new_name",
        [
            ("creative", "explore"),
            ("rigorous", "validate"),
            ("adaptive", "auto"),
        ],
    )
    def test_old_and_new_get_same_model_default(self, old_name: str, new_name: str) -> None:
        """Both old and new mode names resolve to the same default model."""
        from crystalyse.config.models import resolve_model_name

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            old_mode = resolve_mode_name(old_name)
            new_mode = resolve_mode_name(new_name)
        old_model = resolve_model_name(None, mode=old_mode.value)
        new_model = resolve_model_name(None, mode=new_mode.value)
        assert old_model == new_model
