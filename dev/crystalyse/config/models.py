"""Model configuration and registry for Crystalyse.

This module defines the model resolution pipeline:

    User string → resolve_model_name() → str | Model → Agent(model=...)

One resolver, one pipeline.  The resolver returns either a plain string
(routed via the openai-agents SDK's MultiProvider prefix mechanism —
``"litellm/openrouter/anthropic/claude-opus-4.5"`` etc.) or a pre-built
``Model`` instance for backends that need a programmatic client
(``OpenAIChatCompletionsModel`` with a custom ``base_url``).

Every entry in ``MODEL_REGISTRY`` is a curated, documented backbone with
validated API-key gating.  Unknown strings pass through raw as an escape
hatch — power users can always type a full LiteLLM model string.

Version pins enforced by contract tests in ``dev/tests/contract/``:

- ``openai-agents>=0.22.0,<0.23``
- ``litellm==1.83.0``
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ModelBackend(StrEnum):
    """How the SDK should reach the model."""

    OPENAI = "openai"
    LITELLM = "litellm"
    OPENAI_COMPATIBLE = "openai-compat"


@dataclass(frozen=True)
class ModelConfig:
    """One backbone the user can select.

    Frozen so registry entries are immutable after module load.
    ``validate_env()`` is called at resolve time, not import time,
    so importing the registry never requires API keys to be set.
    """

    name: str
    backend: ModelBackend
    model_id: str
    api_key_env_var: str
    base_url: str | None = None
    context_window: int = 128_000
    max_tokens: int | None = None
    temperature: float | None = None
    reasoning_effort: str | None = None
    supports_tool_calling: bool = True
    supports_structured_output: bool = True
    supported_modes: frozenset[str] = field(
        default_factory=lambda: frozenset({"explore", "validate", "auto"})
    )
    notes: str = ""

    def validate_env(self) -> None:
        """Raise if the required API key env var is unset.

        Empty ``api_key_env_var`` means no key is required (local Ollama).
        """
        if self.api_key_env_var and not os.getenv(self.api_key_env_var):
            raise RuntimeError(
                f"ModelConfig {self.name!r} requires env var "
                f"{self.api_key_env_var!r}, but it is not set.  "
                f"See docs/models.md for setup."
            )

    def resolve(self) -> str | Any:
        """Return whatever ``Agent(model=...)`` should receive.

        For OPENAI and LITELLM backends this is a plain string that
        the SDK's MultiProvider can route.  For OPENAI_COMPATIBLE it
        is an ``OpenAIChatCompletionsModel`` instance with a pre-wired
        ``AsyncOpenAI`` client.
        """
        self.validate_env()

        if self.backend is ModelBackend.OPENAI:
            return self.model_id

        if self.backend is ModelBackend.LITELLM:
            return f"litellm/{self.model_id}"

        if self.backend is ModelBackend.OPENAI_COMPATIBLE:
            # Lazy import: only needed for OPENAI_COMPATIBLE entries, and
            # avoids pulling openai into the module scope on plain imports.
            from agents import OpenAIChatCompletionsModel
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=os.getenv(self.api_key_env_var) or "not-needed",
            )
            return OpenAIChatCompletionsModel(
                model=self.model_id,
                openai_client=client,
            )

        raise ValueError(f"Unknown backend: {self.backend}")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, ModelConfig] = {
    # ---- OpenAI reasoning models (current defaults) ----
    "openai_o4_mini": ModelConfig(
        name="openai_o4_mini",
        backend=ModelBackend.OPENAI,
        model_id="o4-mini",
        api_key_env_var="OPENAI_API_KEY",
        reasoning_effort="medium",
        notes="Current default.  Used by explore and auto modes.",
    ),
    "openai_o3": ModelConfig(
        name="openai_o3",
        backend=ModelBackend.OPENAI,
        model_id="o3",
        api_key_env_var="OPENAI_API_KEY",
        reasoning_effort="high",
        notes="Current validate-mode default.  Highest quality, slowest.",
    ),
    "openai_gpt4o_mini": ModelConfig(
        name="openai_gpt4o_mini",
        backend=ModelBackend.OPENAI,
        model_id="gpt-4o-mini",
        api_key_env_var="OPENAI_API_KEY",
        notes="Cheap model for plan-mode research phase or lightweight tasks.",
    ),
    # ---- Anthropic via LiteLLM ----
    "anthropic_claude_opus": ModelConfig(
        name="anthropic_claude_opus",
        backend=ModelBackend.LITELLM,
        model_id="anthropic/claude-opus-5",
        api_key_env_var="ANTHROPIC_API_KEY",
        context_window=1_000_000,
        notes="Strong reasoning, long context.  Requires direct Anthropic API key.",
    ),
    # ---- OpenRouter (any model behind one key) ----
    "openrouter_claude_opus": ModelConfig(
        name="openrouter_claude_opus",
        backend=ModelBackend.LITELLM,
        model_id="openrouter/anthropic/claude-opus-5",
        api_key_env_var="OPENROUTER_API_KEY",
        context_window=1_000_000,
        notes="Route Anthropic via OpenRouter.  One key, many models.",
    ),
    "openrouter_llama3_70b": ModelConfig(
        name="openrouter_llama3_70b",
        backend=ModelBackend.LITELLM,
        model_id="openrouter/meta-llama/llama-3.1-70b-instruct",
        api_key_env_var="OPENROUTER_API_KEY",
        context_window=131_072,
        supported_modes=frozenset({"explore", "auto"}),
        notes="Open-weights via OpenRouter.  Cannot run validate (no reasoning).",
    ),
    # ---- Mistral direct ----
    "mistral_large": ModelConfig(
        name="mistral_large",
        backend=ModelBackend.LITELLM,
        model_id="mistral/mistral-large-latest",
        api_key_env_var="MISTRAL_API_KEY",
    ),
    # ---- Local Ollama ----
    "ollama_llama3_70b_direct": ModelConfig(
        name="ollama_llama3_70b_direct",
        backend=ModelBackend.OPENAI_COMPATIBLE,
        model_id="llama3:70b",
        api_key_env_var="",
        base_url="http://localhost:11434/v1",
        context_window=8_192,
        supports_structured_output=False,
        supported_modes=frozenset({"explore"}),
        notes="Requires Ollama running locally.  Set OLLAMA_API_BASE if not localhost.",
    ),
}


# Mode → default model name (replaces the 2 hardcoded dicts in the codebase)
MODE_DEFAULTS: dict[str, str] = {
    "explore": "openai_o4_mini",
    "validate": "openai_o3",
    "auto": "openai_o4_mini",
}


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------


def resolve_model_name(
    name_or_config: str | ModelConfig | None = None,
    *,
    mode: str | None = None,
) -> str | Any:
    """Resolve a user-facing name to whatever ``Agent(model=...)`` needs.

    Resolution order:

    1. If *name_or_config* is a ``ModelConfig``, call ``.resolve()`` directly.
    2. If *name_or_config* is a string in ``MODEL_REGISTRY``, resolve via
       the registry entry.
    3. If it's an unknown string, pass it through raw — this is the escape
       hatch that lets power users type ``litellm/openrouter/...`` directly.
    4. If *name_or_config* is ``None`` and *mode* is given, fall back to
       ``MODE_DEFAULTS[mode]``.
    5. If both are ``None``, raise.

    Returns either a plain string (for MultiProvider routing) or a
    ``Model`` instance (for ``OPENAI_COMPATIBLE`` backends).
    """
    if name_or_config is None:
        if mode is None:
            raise ValueError("resolve_model_name() needs either a model name or a mode.")
        default_name = MODE_DEFAULTS.get(mode)
        if default_name is None:
            raise ValueError(f"Unknown mode {mode!r}.  Valid modes: {sorted(MODE_DEFAULTS)}")
        return resolve_model_name(default_name)

    if isinstance(name_or_config, ModelConfig):
        return name_or_config.resolve()

    # String path: look up in the registry first.
    cfg = MODEL_REGISTRY.get(name_or_config)
    if cfg is not None:
        return cfg.resolve()

    # Unknown string — pass through raw.  This lets users type full LiteLLM
    # model strings like "litellm/openrouter/anthropic/claude-opus-4.5"
    # without pre-registering them.
    return name_or_config
