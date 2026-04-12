"""Tests for the model configuration and registry.

Feature 1.1 acceptance criteria from weekend-revision-plan.md §4.1.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from crystalyse.config.models import (
    MODE_DEFAULTS,
    MODEL_REGISTRY,
    ModelBackend,
    ModelConfig,
    resolve_model_name,
)

# ---------------------------------------------------------------------------
# Registry import and structure
# ---------------------------------------------------------------------------


def test_registry_imports():
    """AC: from crystalyse.config.models import MODEL_REGISTRY, resolve_model_name works."""
    assert isinstance(MODEL_REGISTRY, dict)
    assert callable(resolve_model_name)


def test_registry_has_expected_entries():
    """AC: all eight registry entries exist."""
    expected = {
        "openai_o4_mini",
        "openai_o3",
        "openai_gpt4o_mini",
        "anthropic_claude_opus",
        "openrouter_claude_opus",
        "openrouter_llama3_70b",
        "mistral_large",
        "ollama_llama3_70b_direct",
    }
    assert expected == set(MODEL_REGISTRY.keys())


@pytest.mark.parametrize("name", list(MODEL_REGISTRY.keys()))
def test_registry_entries_instantiate_without_raising(name):
    """AC: unit test imports every registry entry without raising."""
    cfg = MODEL_REGISTRY[name]
    assert isinstance(cfg, ModelConfig)
    assert cfg.name == name
    assert isinstance(cfg.backend, ModelBackend)


def test_mode_defaults_cover_all_modes():
    """MODE_DEFAULTS must cover explore, validate, auto."""
    assert set(MODE_DEFAULTS) == {"explore", "validate", "auto"}
    for default_name in MODE_DEFAULTS.values():
        assert default_name in MODEL_REGISTRY


# ---------------------------------------------------------------------------
# ModelConfig.validate_env()
# ---------------------------------------------------------------------------


def test_validate_env_raises_when_key_unset():
    """AC: ModelConfig(..., api_key_env_var='OPENAI_API_KEY').validate_env()
    raises RuntimeError when the env var is unset."""
    cfg = ModelConfig(
        name="test",
        backend=ModelBackend.OPENAI,
        model_id="test-model",
        api_key_env_var="CRYSTALYSE_NONEXISTENT_KEY_FOR_TEST",
    )
    with mock.patch.dict(os.environ, {}, clear=False):
        # Make sure the key doesn't exist
        os.environ.pop("CRYSTALYSE_NONEXISTENT_KEY_FOR_TEST", None)
        with pytest.raises(RuntimeError, match="CRYSTALYSE_NONEXISTENT_KEY_FOR_TEST"):
            cfg.validate_env()


def test_validate_env_noop_when_key_empty():
    """AC: ModelConfig(..., api_key_env_var='').validate_env() is a no-op."""
    cfg = ModelConfig(
        name="test",
        backend=ModelBackend.OPENAI,
        model_id="test-model",
        api_key_env_var="",
    )
    # Should not raise
    cfg.validate_env()


def test_validate_env_passes_when_key_set():
    """validate_env does not raise when the env var IS set."""
    cfg = ModelConfig(
        name="test",
        backend=ModelBackend.OPENAI,
        model_id="test-model",
        api_key_env_var="CRYSTALYSE_TEST_KEY",
    )
    with mock.patch.dict(os.environ, {"CRYSTALYSE_TEST_KEY": "sk-test"}):
        cfg.validate_env()  # should not raise


# ---------------------------------------------------------------------------
# ModelConfig.resolve()
# ---------------------------------------------------------------------------


def test_openai_backend_resolve_returns_string():
    """OPENAI backend resolve returns the bare model_id string."""
    cfg = MODEL_REGISTRY["openai_o4_mini"]
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        result = cfg.resolve()
    assert result == "o4-mini"
    assert isinstance(result, str)


def test_litellm_backend_resolve_returns_prefixed_string():
    """LITELLM backend resolve returns 'litellm/<model_id>'."""
    cfg = MODEL_REGISTRY["openrouter_claude_opus"]
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}):
        result = cfg.resolve()
    assert result.startswith("litellm/")
    assert "openrouter/anthropic/" in result
    assert isinstance(result, str)


def test_openai_compatible_resolve_returns_model_instance():
    """AC: resolve_model_name('ollama_llama3_70b_direct') returns an
    OpenAIChatCompletionsModel instance."""
    cfg = MODEL_REGISTRY["ollama_llama3_70b_direct"]
    # Ollama has empty api_key_env_var so validate_env is a no-op
    result = cfg.resolve()
    # Should be a Model instance, not a string
    assert not isinstance(result, str)
    # Check it has the expected model attribute
    assert hasattr(result, "model") or hasattr(result, "_model")


# ---------------------------------------------------------------------------
# resolve_model_name()
# ---------------------------------------------------------------------------


def test_resolve_known_registry_name():
    """AC: resolve_model_name('openai_o4_mini') returns a string."""
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        result = resolve_model_name("openai_o4_mini")
    assert isinstance(result, str)
    assert result == "o4-mini"


def test_resolve_mode_default():
    """AC: resolve_model_name(None, mode='validate') returns o3's model_id."""
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        result = resolve_model_name(None, mode="validate")
    assert result == "o3"


def test_resolve_unknown_string_passthrough():
    """AC: resolve_model_name('litellm/openrouter/unknown-model') returns
    the raw string unchanged."""
    result = resolve_model_name("litellm/openrouter/unknown-model")
    assert result == "litellm/openrouter/unknown-model"


def test_resolve_model_config_directly():
    """Passing a ModelConfig directly calls .resolve()."""
    cfg = MODEL_REGISTRY["openai_gpt4o_mini"]
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        result = resolve_model_name(cfg)
    assert result == "gpt-4o-mini"


def test_resolve_none_none_raises():
    """resolve_model_name(None) with no mode raises ValueError."""
    with pytest.raises(ValueError, match="needs either"):
        resolve_model_name(None)


def test_resolve_unknown_mode_raises():
    """resolve_model_name(None, mode='nonexistent') raises ValueError."""
    with pytest.raises(ValueError, match="Unknown mode"):
        resolve_model_name(None, mode="nonexistent")


def test_resolve_ollama_returns_model_instance():
    """AC: resolve_model_name('ollama_llama3_70b_direct') returns a Model."""
    result = resolve_model_name("ollama_llama3_70b_direct")
    assert not isinstance(result, str)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_model_config_is_frozen():
    """ModelConfig instances are immutable."""
    cfg = MODEL_REGISTRY["openai_o4_mini"]
    with pytest.raises(AttributeError):
        cfg.name = "mutated"  # type: ignore[misc]


def test_supported_modes_are_frozensets():
    """All registry entries have frozenset supported_modes."""
    for name, cfg in MODEL_REGISTRY.items():
        assert isinstance(cfg.supported_modes, frozenset), (
            f"{name}.supported_modes is {type(cfg.supported_modes)}, expected frozenset"
        )


def test_ollama_has_no_api_key_requirement():
    """Ollama entry has empty api_key_env_var."""
    cfg = MODEL_REGISTRY["ollama_llama3_70b_direct"]
    assert cfg.api_key_env_var == ""


def test_openrouter_llama_cannot_run_validate():
    """openrouter_llama3_70b should not support validate mode."""
    cfg = MODEL_REGISTRY["openrouter_llama3_70b"]
    assert "validate" not in cfg.supported_modes
    assert "explore" in cfg.supported_modes
