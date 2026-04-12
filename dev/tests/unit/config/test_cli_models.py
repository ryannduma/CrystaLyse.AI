"""Tests for the ``crystalyse models`` CLI subcommands.

Covers acceptance criteria from spec §4.6:
- ``crystalyse models list`` prints a table without errors
- ``crystalyse models check`` with OPENAI_API_KEY set prints OK for OpenAI entries
- ``crystalyse models check`` with no API keys prints clear per-model status
- ``--model`` flag routes through resolve_model_name at the resolver level
"""

from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from crystalyse.cli import app
from crystalyse.config.models import MODEL_REGISTRY, resolve_model_name

runner = CliRunner()


# ---------------------------------------------------------------------------
# crystalyse models list
# ---------------------------------------------------------------------------


class TestModelsList:
    def test_models_list_exits_zero(self) -> None:
        """Acceptance criterion: models list prints without errors."""
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0, result.output

    def test_models_list_contains_registry_entries(self) -> None:
        result = runner.invoke(app, ["models", "list"])
        # Every registry entry name should appear in the output
        for name in MODEL_REGISTRY:
            assert name in result.output, (
                f"Registry entry {name!r} not found in models list output"
            )

    def test_models_list_shows_backend_values(self) -> None:
        result = runner.invoke(app, ["models", "list"])
        # At least one backend value should appear (headers may be truncated)
        assert "openai" in result.output.lower() or "litellm" in result.output.lower()

    def test_models_list_shows_usable_column(self) -> None:
        result = runner.invoke(app, ["models", "list"])
        # Should contain at least one check mark (OPENAI_API_KEY is set in saturn)
        assert "✓" in result.output or "✗" in result.output


# ---------------------------------------------------------------------------
# crystalyse models check
# ---------------------------------------------------------------------------


class TestModelsCheck:
    def test_models_check_with_openai_key_set(self) -> None:
        """Acceptance criterion: with OPENAI_API_KEY set, OpenAI entries show OK."""
        # OPENAI_API_KEY is set in the saturn env (verified by init.sh)
        result = runner.invoke(app, ["models", "check"])
        # OpenAI entries should show as set
        assert "openai_o4_mini" in result.output
        assert "OPENAI_API_KEY is set" in result.output

    def test_models_check_missing_keys_nonzero_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Acceptance criterion: with no API keys, prints clear per-model status."""
        # Remove all API keys
        for cfg in MODEL_REGISTRY.values():
            if cfg.api_key_env_var:
                monkeypatch.delenv(cfg.api_key_env_var, raising=False)

        result = runner.invoke(app, ["models", "check"])
        assert result.exit_code != 0
        assert "NOT set" in result.output

    def test_models_check_ollama_always_ok(self) -> None:
        """Ollama (empty api_key_env_var) should always show as usable."""
        result = runner.invoke(app, ["models", "check"])
        assert "ollama_llama3_70b_direct" in result.output
        assert "no API key required" in result.output

    def test_models_check_all_keys_set_zero_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When all env vars are set, exit code should be 0."""
        for cfg in MODEL_REGISTRY.values():
            if cfg.api_key_env_var:
                monkeypatch.setenv(cfg.api_key_env_var, "test-key")

        result = runner.invoke(app, ["models", "check"])
        assert result.exit_code == 0
        assert "All models are usable" in result.output


# ---------------------------------------------------------------------------
# --model flag resolution
# ---------------------------------------------------------------------------


class TestModelFlagResolution:
    def test_registry_name_resolves(self) -> None:
        """A registry name should resolve to the model_id string."""
        result = resolve_model_name("openai_o4_mini")
        assert result == "o4-mini"

    def test_unknown_string_passes_through(self) -> None:
        """Unknown strings are the escape hatch — pass through raw."""
        result = resolve_model_name("litellm/openrouter/anthropic/claude-opus-4.5")
        assert result == "litellm/openrouter/anthropic/claude-opus-4.5"

    def test_mode_default_fallback(self) -> None:
        """When name is None and mode is given, use MODE_DEFAULTS."""
        result = resolve_model_name(None, mode="validate")
        assert result == "o3"

    def test_none_none_raises(self) -> None:
        """Both None should raise ValueError."""
        with pytest.raises(ValueError, match="needs either a model name or a mode"):
            resolve_model_name(None)
