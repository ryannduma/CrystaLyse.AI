"""Reasoning/thinking configuration reaching ``ModelSettings``.

``ModelConfig.reasoning_effort`` and ``ModelConfig.thinking_budget_tokens``
are declarative fields that nothing consumed until
``ModelConfig.agent_model_settings()`` existed.  The wire format differs by
provider *and* by model generation, so these tests pin the shape of the
``ModelSettings`` object each registry entry produces.

Everything here is offline: no API keys, no network, no ``validate_env()``.
"""

from __future__ import annotations

from typing import Any

import pytest
from agents.model_settings import ModelSettings
from openai.types.shared import Reasoning

from crystalyse.config.models import (
    MODE_DEFAULTS,
    MODEL_REGISTRY,
    ModelBackend,
    ModelConfig,
    get_effective_registry,
    resolve_model_config,
)


def _entry(**overrides: Any) -> ModelConfig:
    """A synthetic registry entry.  No key required, so nothing hits a provider."""
    fields: dict[str, Any] = {
        "name": "synthetic",
        "backend": ModelBackend.LITELLM,
        "model_id": "anthropic/claude-synthetic",
        "api_key_env_var": "",
    }
    fields.update(overrides)
    return ModelConfig(**fields)


# ---------------------------------------------------------------------------
# OPENAI backend: reasoning=Reasoning(effort=...)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "effort"),
    [("openai_o3", "high"), ("openai_o4_mini", "medium")],
    ids=["o3-high", "o4-mini-medium"],
)
def test_openai_reasoning_effort_becomes_a_reasoning_object(name: str, effort: str) -> None:
    settings = MODEL_REGISTRY[name].agent_model_settings()
    assert isinstance(settings.reasoning, Reasoning)
    assert settings.reasoning.effort == effort


def test_openai_backend_never_uses_extra_args_for_reasoning() -> None:
    """The Responses API takes ``reasoning``; ``extra_args`` is a LiteLLM channel."""
    settings = MODEL_REGISTRY["openai_o3"].agent_model_settings()
    assert settings.extra_args is None


def test_openai_entry_without_reasoning_effort_leaves_reasoning_unset() -> None:
    """gpt-4o-mini is not a reasoning model; sending ``reasoning`` would be rejected."""
    cfg = MODEL_REGISTRY["openai_gpt4o_mini"]
    assert cfg.reasoning_effort is None
    settings = cfg.agent_model_settings()
    assert settings.reasoning is None
    assert settings.extra_args is None


def test_openai_backend_drops_a_declared_thinking_budget() -> None:
    """``thinking_budget_tokens`` is Anthropic-only: on an OPENAI entry it reaches nothing.

    Characterisation, not endorsement.  ``thinking_budget_tokens`` is in
    ``OVERRIDABLE_FIELDS``, so config.toml accepts it on ``openai_o3`` and it
    then does nothing -- the silent no-op ``model_overrides.py`` calls worse
    than a crash.  Pinned so a future fix has to update this test.
    """
    settings = _entry(
        backend=ModelBackend.OPENAI,
        model_id="o3",
        thinking_budget_tokens=2048,
    ).agent_model_settings()
    assert settings.reasoning is None
    assert settings.extra_args is None


def test_explicit_reasoning_override_wins_over_the_declared_effort() -> None:
    settings = MODEL_REGISTRY["openai_o3"].agent_model_settings(reasoning=Reasoning(effort="low"))
    assert settings.reasoning is not None
    assert settings.reasoning.effort == "low"


# ---------------------------------------------------------------------------
# LITELLM backend: thinking travels in extra_args
# ---------------------------------------------------------------------------


def test_thinking_budget_uses_the_claude_4x_enabled_shape() -> None:
    """Claude 4.x wants ``thinking={"type": "enabled", "budget_tokens": N}``."""
    cfg = MODEL_REGISTRY["anthropic_claude_haiku"]
    budget = cfg.thinking_budget_tokens
    assert budget is not None, "registry entry no longer declares a thinking budget"

    settings = cfg.agent_model_settings()
    assert settings.extra_args == {"thinking": {"type": "enabled", "budget_tokens": budget}}


def test_litellm_reasoning_effort_uses_the_claude_5_adaptive_shape() -> None:
    """Claude 5 rejects ``type="enabled"``; it wants adaptive thinking + effort."""
    cfg = MODEL_REGISTRY["anthropic_claude_sonnet"]
    effort = cfg.reasoning_effort
    assert effort is not None, "registry entry no longer declares a reasoning effort"
    assert cfg.thinking_budget_tokens is None

    settings = cfg.agent_model_settings()
    assert settings.extra_args == {
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort},
    }


def test_litellm_backend_does_not_build_a_reasoning_object() -> None:
    """``reasoning`` is an OpenAI Responses field; litellm would ignore it."""
    settings = MODEL_REGISTRY["anthropic_claude_sonnet"].agent_model_settings()
    assert settings.reasoning is None


def test_thinking_budget_takes_precedence_when_both_are_declared() -> None:
    """budget_tokens and adaptive+effort are mutually exclusive on the wire."""
    settings = _entry(thinking_budget_tokens=4096, reasoning_effort="high").agent_model_settings()
    assert settings.extra_args == {"thinking": {"type": "enabled", "budget_tokens": 4096}}


def test_litellm_entry_with_no_thinking_config_sends_no_extra_args() -> None:
    cfg = MODEL_REGISTRY["mistral_large"]
    assert cfg.reasoning_effort is None and cfg.thinking_budget_tokens is None
    assert cfg.agent_model_settings().extra_args is None


def test_max_tokens_stays_out_of_extra_args() -> None:
    """The SDK passes max_tokens separately; a duplicate makes litellm raise."""
    settings = _entry(max_tokens=1024, thinking_budget_tokens=512).agent_model_settings()
    assert settings.max_tokens == 1024
    assert settings.extra_args == {"thinking": {"type": "enabled", "budget_tokens": 512}}


def test_caller_extra_args_are_merged_with_the_thinking_block() -> None:
    settings = _entry(thinking_budget_tokens=512).agent_model_settings(
        extra_args={"api_base": "http://localhost:4000"}
    )
    assert settings.extra_args == {
        "api_base": "http://localhost:4000",
        "thinking": {"type": "enabled", "budget_tokens": 512},
    }


def test_caller_extra_args_dict_is_not_mutated() -> None:
    caller_args: dict[str, Any] = {"api_base": "http://localhost:4000"}
    _entry(thinking_budget_tokens=512).agent_model_settings(extra_args=caller_args)
    assert caller_args == {"api_base": "http://localhost:4000"}


def test_openai_compatible_backend_carries_no_thinking_payload() -> None:
    """Local chat-completions endpoints get neither shape, even if effort is declared."""
    settings = _entry(
        backend=ModelBackend.OPENAI_COMPATIBLE,
        model_id="qwen3:32b",
        reasoning_effort="high",
    ).agent_model_settings()
    assert settings.reasoning is None
    assert settings.extra_args is None


# ---------------------------------------------------------------------------
# Plain sampling fields and pass-through overrides
# ---------------------------------------------------------------------------


def test_declared_temperature_and_max_tokens_reach_the_settings() -> None:
    settings = _entry(
        backend=ModelBackend.OPENAI,
        model_id="gpt-4o-mini",
        temperature=0.2,
        max_tokens=4096,
    ).agent_model_settings()
    assert settings.temperature == 0.2
    assert settings.max_tokens == 4096


def test_overrides_pass_through_alongside_the_thinking_block() -> None:
    settings = _entry(thinking_budget_tokens=512).agent_model_settings(tool_choice="auto")
    assert settings.tool_choice == "auto"
    assert settings.extra_args == {"thinking": {"type": "enabled", "budget_tokens": 512}}


def test_override_wins_over_the_declared_temperature() -> None:
    settings = _entry(temperature=0.1).agent_model_settings(temperature=0.9)
    assert settings.temperature == 0.9


# ---------------------------------------------------------------------------
# Whole-registry invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(MODEL_REGISTRY), ids=sorted(MODEL_REGISTRY))
def test_every_registry_entry_builds_settings_without_raising(name: str) -> None:
    settings = MODEL_REGISTRY[name].agent_model_settings()
    assert isinstance(settings, ModelSettings)
    assert "max_tokens" not in (settings.extra_args or {})


_DECLARES_REASONING = sorted(
    name
    for name, cfg in MODEL_REGISTRY.items()
    if cfg.reasoning_effort or cfg.thinking_budget_tokens is not None
)


@pytest.mark.parametrize("name", _DECLARES_REASONING, ids=_DECLARES_REASONING)
def test_declared_reasoning_config_is_never_silently_dropped(name: str) -> None:
    """The bug this method fixed: a declared effort that reaches nothing."""
    settings = MODEL_REGISTRY[name].agent_model_settings()
    carried = settings.reasoning is not None or "thinking" in (settings.extra_args or {})
    assert carried, f"{name} declares reasoning config that agent_model_settings() drops"


def test_the_registry_still_declares_reasoning_config_somewhere() -> None:
    """Without this, emptying ``_DECLARES_REASONING`` would silently retire the check above."""
    assert _DECLARES_REASONING


# ---------------------------------------------------------------------------
# resolve_model_config()
# ---------------------------------------------------------------------------


def test_registry_name_resolves_to_the_registry_entry() -> None:
    effective, _ = get_effective_registry()
    assert resolve_model_config("openai_o3") is effective["openai_o3"]


def test_a_model_config_resolves_to_itself() -> None:
    cfg = _entry()
    assert resolve_model_config(cfg) is cfg


def test_unregistered_pass_through_string_resolves_to_none() -> None:
    """A raw LiteLLM string has no registry entry, hence no declared reasoning."""
    assert resolve_model_config("litellm/openrouter/anthropic/claude-opus-4.5") is None


@pytest.mark.parametrize("mode", sorted(MODE_DEFAULTS), ids=sorted(MODE_DEFAULTS))
def test_mode_without_a_name_resolves_to_the_mode_default(mode: str) -> None:
    effective, _ = get_effective_registry()
    assert resolve_model_config(mode=mode) is effective[MODE_DEFAULTS[mode]]


def test_no_name_and_no_mode_resolves_to_none() -> None:
    assert resolve_model_config() is None


def test_unknown_mode_resolves_to_none() -> None:
    """Unlike resolve_model_name(), the config resolver reports absence instead of raising."""
    assert resolve_model_config(mode="turbo") is None


def test_mode_default_reasoning_effort_survives_into_the_settings() -> None:
    """End to end: the reason agent_model_settings() and this resolver both exist."""
    cfg = resolve_model_config(mode="validate")
    assert cfg is not None
    assert cfg.reasoning_effort is not None
    settings = cfg.agent_model_settings()
    assert settings.reasoning is not None
    assert settings.reasoning.effort == cfg.reasoning_effort
