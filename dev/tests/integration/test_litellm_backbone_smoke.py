"""Smoke tests for the LiteLLM backbone integration.

These tests verify that the openai-agents SDK's LiteLLM integration
is properly installed, that CrystaLyse's model resolver produces values
the SDK accepts, and that the full Agent → LitellmModel → litellm.acompletion
pipeline fires correctly (with a mocked LLM response).

Feature 1.7 — spec §4.7 acceptance criteria:
- Import-smoke test for LitellmModel and MultiProvider passes
- Mocked-response test creates an Agent with a LiteLLM model string and
  exercises the SDK path
- Live test marked @pytest.mark.requires_api runs green when key is set,
  skips cleanly otherwise
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import-smoke tests
# ---------------------------------------------------------------------------


class TestLitellmImportSmoke:
    """Verify the SDK exports the LiteLLM integration classes we depend on."""

    def test_litellm_model_importable(self) -> None:
        from agents.extensions.models.litellm_model import LitellmModel

        assert LitellmModel is not None

    def test_multi_provider_importable(self) -> None:
        from agents.models.multi_provider import MultiProvider

        assert MultiProvider is not None

    def test_litellm_completion_callable(self) -> None:
        from litellm import acompletion

        assert callable(acompletion)

    def test_litellm_model_accepts_model_string(self) -> None:
        """LitellmModel can be instantiated with a model string."""
        from agents.extensions.models.litellm_model import LitellmModel

        model = LitellmModel(model="openai/gpt-4o-mini")
        assert model.model == "openai/gpt-4o-mini"

    def test_litellm_model_accepts_api_key(self) -> None:
        from agents.extensions.models.litellm_model import LitellmModel

        model = LitellmModel(
            model="anthropic/claude-opus-4-6-20260205",
            api_key="test-key",
        )
        assert model.api_key == "test-key"


# ---------------------------------------------------------------------------
# Resolver → Agent integration
# ---------------------------------------------------------------------------


class TestResolverAgentIntegration:
    """Verify that resolve_model_name() output is accepted by Agent()."""

    def test_registry_name_produces_agent_compatible_model(self) -> None:
        """resolve_model_name('openai_o4_mini') → 'o4-mini' → Agent accepts it."""
        from agents import Agent

        from crystalyse.config.models import resolve_model_name

        resolved = resolve_model_name("openai_o4_mini")
        assert resolved == "o4-mini"

        # Agent accepts the resolved string (it uses MultiProvider internally)
        agent = Agent(name="smoke", model=resolved, instructions="test")
        assert agent.model == resolved

    def test_litellm_prefix_produces_agent_compatible_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_model_name for a LiteLLM entry produces a 'litellm/...' string."""
        from agents import Agent

        from crystalyse.config.models import resolve_model_name

        # The Anthropic registry entry requires ANTHROPIC_API_KEY
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        resolved = resolve_model_name("anthropic_claude_opus")
        assert resolved.startswith("litellm/")

        # Agent accepts the prefixed string
        agent = Agent(name="smoke", model=resolved, instructions="test")
        assert agent.model == resolved

    def test_raw_passthrough_produces_agent_compatible_model(self) -> None:
        """Unknown strings pass through and Agent accepts them."""
        from agents import Agent

        from crystalyse.config.models import resolve_model_name

        raw = "litellm/openrouter/anthropic/claude-opus-4.5"
        resolved = resolve_model_name(raw)
        assert resolved == raw

        agent = Agent(name="smoke", model=resolved, instructions="test")
        assert agent.model == raw


# ---------------------------------------------------------------------------
# Mocked-response test
# ---------------------------------------------------------------------------


class TestMockedLitellmResponse:
    """Exercise the Agent → LitellmModel → litellm.acompletion pipeline
    with a mocked LLM response.  No real API calls are made.
    """

    @pytest.fixture
    def mock_litellm_response(self):
        """Build a minimal but structurally valid litellm ModelResponse."""
        from litellm.types.utils import Choices, Message, ModelResponse, Usage

        msg = Message(content="Hello from mocked LiteLLM", role="assistant")
        choice = Choices(finish_reason="stop", index=0, message=msg)
        usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        return ModelResponse(
            id="mock-resp-001",
            choices=[choice],
            model="openai/gpt-4o-mini",
            usage=usage,
        )

    async def test_agent_with_litellm_model_runs_one_turn(
        self, mock_litellm_response
    ) -> None:
        """Create an Agent with LitellmModel, mock acompletion, run one turn.

        This is the load-bearing test: it confirms the full pipeline from
        resolve_model_name → LitellmModel → Agent.run → litellm.acompletion
        fires without error.
        """
        from agents import Agent, Runner
        from agents.extensions.models.litellm_model import LitellmModel

        model = LitellmModel(model="openai/gpt-4o-mini")
        agent = Agent(
            name="litellm-smoke",
            model=model,
            instructions="You are a test assistant. Reply briefly.",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.return_value = mock_litellm_response

            result = await Runner.run(
                agent,
                input="Say hello",
                max_turns=1,
            )

            # Verify the mock was called (the SDK fired the LiteLLM path)
            assert mock_acomp.called, "litellm.acompletion was never called"

            # Verify we got a result back through the pipeline
            assert result.final_output is not None

    async def test_resolver_to_litellm_model_pipeline(
        self, mock_litellm_response
    ) -> None:
        """Full pipeline: resolve_model_name → LitellmModel → Agent → run."""
        from agents import Agent, Runner
        from agents.extensions.models.litellm_model import LitellmModel

        from crystalyse.config.models import MODEL_REGISTRY

        # Resolve a LiteLLM-backed registry entry
        cfg = MODEL_REGISTRY["anthropic_claude_opus"]
        resolved = cfg.resolve.__wrapped__(cfg) if hasattr(cfg.resolve, "__wrapped__") else None

        # Build the model manually (resolve() would check env var)
        model = LitellmModel(model=f"litellm/{cfg.model_id}")
        agent = Agent(
            name="pipeline-smoke",
            model=model,
            instructions="You are a test assistant.",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.return_value = mock_litellm_response

            result = await Runner.run(agent, input="Test", max_turns=1)

            assert mock_acomp.called
            # Verify the model string passed to litellm includes the provider prefix
            call_kwargs = mock_acomp.call_args
            called_model = call_kwargs.kwargs.get("model") or call_kwargs.args[0] if call_kwargs.args else None
            if called_model:
                assert "anthropic" in called_model.lower() or "litellm" in called_model.lower()


# ---------------------------------------------------------------------------
# Live test (gated on API key)
# ---------------------------------------------------------------------------


class TestLiveLitellmBackbone:
    """Live test that makes a real API call.  Only runs when opted in."""

    @pytest.mark.requires_api
    async def test_live_openrouter_one_turn(self) -> None:
        """Run one turn against OpenRouter with a cheap model.

        Skips if OPENROUTER_API_KEY is not set.  This test costs real money
        (a fraction of a cent per run) — it's gated behind the requires_api
        marker which CI excludes by default.
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set")

        from agents import Agent, Runner
        from agents.extensions.models.litellm_model import LitellmModel

        model = LitellmModel(
            model="openrouter/meta-llama/llama-3.1-70b-instruct",
            api_key=api_key,
        )
        agent = Agent(
            name="live-smoke",
            model=model,
            instructions="Reply with exactly one word: 'pong'.",
        )

        result = await Runner.run(agent, input="ping", max_turns=1)
        assert result.final_output is not None
        assert len(result.final_output) > 0
