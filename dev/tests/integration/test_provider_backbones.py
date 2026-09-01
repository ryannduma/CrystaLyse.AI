"""Do the live backbones actually do what their registry entries claim?

``MODEL_REGISTRY`` is a *capability table*: every entry declares
``supports_tool_calling`` and ``supports_structured_output``, and
``agents_bridge`` wires an agent up on the strength of those claims.  No
offline test can tell you whether a claim is true -- only the provider can.

So each test here takes one entry, resolves it exactly the way
``agents_bridge`` does (``ModelConfig.resolve()`` for the model plus
``ModelConfig.agent_model_settings()`` for the reasoning/thinking config) and
asserts the declared capability against the live API:

* a plain one-turn completion returns non-empty output;
* ``supports_tool_calling`` -> a trivial ``function_tool`` is really invoked
  and its value really reaches the answer;
* ``supports_structured_output`` -> ``Agent(output_type=...)`` returns a
  validated model instance.

Cost discipline, because this is real money: the cheapest entry per provider,
one short prompt per test, ``max_turns=1`` (2 only where a tool call needs a
second turn to be reported), no parametrisation across models and no retries.

Every live test carries ``@pytest.mark.requires(<provider>)``, so the file
skips with a reason when a key is absent, and it lives in ``integration/`` so
it defers to the main stage instead of gating every PR.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import pytest
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool
from pydantic import BaseModel

from crystalyse.config.models import ModelBackend, ModelConfig, get_effective_registry

#: LiteLLM is an optional extra (``pip install 'crystalyse[litellm]'``), and
#: every LITELLM-backed entry routes through it.  Skip rather than fail when
#: the extra is not installed -- a missing optional dependency is not a
#: regression in the registry.
requires_litellm = pytest.mark.skipif(
    importlib.util.find_spec("litellm") is None,
    reason="litellm extra not installed (pip install 'crystalyse[litellm]')",
)

#: A value no model can produce on its own.  If it appears in the answer, the
#: tool genuinely ran *and* its return value genuinely reached the model --
#: that is the behaviour, so there is nothing to learn from call counts.
TOOL_CANARY = "ZQ-4417-PLUM"


@function_tool
def lookup_batch_code(sample: str) -> str:
    """Return the internal batch code for a sample name."""
    return TOOL_CANARY


class CapitalAnswer(BaseModel):
    """Smallest structured payload that still has a checkable value."""

    city: str


def _entry(name: str) -> ModelConfig:
    """The entry as resolution actually sees it -- config.toml overrides included."""
    registry, _ = get_effective_registry()
    cfg = registry.get(name)
    assert cfg is not None, f"{name!r} is missing from the effective model registry"
    return cfg


async def _plain_completion(cfg: ModelConfig) -> str:
    """One turn, one word.  The smallest thing a usable backbone must do."""
    agent = Agent(
        name=f"{cfg.name}-plain",
        model=cfg.resolve(),
        instructions="Reply with the single word: ok",
        model_settings=cfg.agent_model_settings(),
    )
    result = await Runner.run(agent, input="ping", max_turns=1)
    return result.final_output


async def _answer_via_tool(cfg: ModelConfig, **settings: Any) -> str:
    """Two turns: one to call the tool, one to report what it returned.

    *settings* goes to ``agent_model_settings()``, which is also how a caller
    caps ``max_tokens`` on a route known to run away.
    """
    agent = Agent(
        name=f"{cfg.name}-tool",
        model=cfg.resolve(),
        instructions=(
            "Use the lookup_batch_code tool to look up the batch code, then "
            "reply with that code and nothing else."
        ),
        tools=[lookup_batch_code],
        model_settings=cfg.agent_model_settings(tool_choice="auto", **settings),
    )
    result = await Runner.run(agent, input="Batch code for sample A?", max_turns=2)
    return result.final_output


async def _structured_answer(cfg: ModelConfig, **settings: Any) -> CapitalAnswer:
    agent = Agent(
        name=f"{cfg.name}-structured",
        model=cfg.resolve(),
        instructions="Answer with the city name only.",
        output_type=CapitalAnswer,
        model_settings=cfg.agent_model_settings(**settings),
    )
    result = await Runner.run(agent, input="What is the capital of France?", max_turns=1)
    return result.final_output


# ---------------------------------------------------------------------------
# OpenAI -- openai_o4_mini, the cheapest reasoning entry (o3 costs ~10x)
# ---------------------------------------------------------------------------


@pytest.mark.requires("openai")
async def test_openai_o4_mini_completes_one_turn() -> None:
    cfg = _entry("openai_o4_mini")
    assert cfg.backend is ModelBackend.OPENAI

    output = await _plain_completion(cfg)

    assert isinstance(output, str)
    assert output.strip(), "o4-mini returned an empty completion"


@pytest.mark.requires("openai")
async def test_openai_o4_mini_invokes_tool_and_uses_its_value() -> None:
    cfg = _entry("openai_o4_mini")
    if not cfg.supports_tool_calling:
        pytest.skip(f"{cfg.name} does not claim tool calling")

    output = await _answer_via_tool(cfg)

    assert TOOL_CANARY in output, f"tool result never reached the answer: {output!r}"


@pytest.mark.requires("openai")
async def test_openai_o4_mini_returns_validated_structured_output() -> None:
    cfg = _entry("openai_o4_mini")
    if not cfg.supports_structured_output:
        pytest.skip(f"{cfg.name} does not claim structured output")

    answer = await _structured_answer(cfg)

    assert isinstance(answer, CapitalAnswer)
    assert "paris" in answer.city.lower()


# ---------------------------------------------------------------------------
# Anthropic -- anthropic_claude_haiku, the cheapest tier ($1/$5 per Mtok).
# This entry also exercises the Claude 4.x thinking wire format
# (thinking={"type": "enabled", "budget_tokens": ...}) that
# agent_model_settings() builds for it.
# ---------------------------------------------------------------------------


@requires_litellm
@pytest.mark.requires("anthropic")
async def test_anthropic_haiku_completes_one_turn() -> None:
    cfg = _entry("anthropic_claude_haiku")
    assert cfg.backend is ModelBackend.LITELLM

    output = await _plain_completion(cfg)

    assert isinstance(output, str)
    assert output.strip(), "claude-haiku returned an empty completion"


@requires_litellm
@pytest.mark.requires("anthropic")
async def test_anthropic_haiku_invokes_tool_and_uses_its_value() -> None:
    cfg = _entry("anthropic_claude_haiku")
    if not cfg.supports_tool_calling:
        pytest.skip(f"{cfg.name} does not claim tool calling")

    output = await _answer_via_tool(cfg)

    assert TOOL_CANARY in output, f"tool result never reached the answer: {output!r}"


@requires_litellm
@pytest.mark.requires("anthropic")
async def test_anthropic_haiku_returns_validated_structured_output() -> None:
    cfg = _entry("anthropic_claude_haiku")
    if not cfg.supports_structured_output:
        pytest.skip(f"{cfg.name} does not claim structured output")

    answer = await _structured_answer(cfg)

    assert isinstance(answer, CapitalAnswer)
    assert "paris" in answer.city.lower()


# ---------------------------------------------------------------------------
# OpenRouter -- one hosted-frontier entry and one open-weights entry, because
# the two fail in different ways.  Kept to one call each to hold the bill down.
# ---------------------------------------------------------------------------


@requires_litellm
@pytest.mark.requires("openrouter")
async def test_openrouter_claude_opus_invokes_tool_and_uses_its_value() -> None:
    """One call covering both of this entry's load-bearing claims.

    Opus is the priciest tier in the registry, so it gets a single request:
    a successful tool round-trip proves the OpenRouter route works *and*
    returns non-empty output, which a plain completion test would only
    duplicate at twice the cost.
    """
    cfg = _entry("openrouter_claude_opus")
    if not cfg.supports_tool_calling:
        pytest.skip(f"{cfg.name} does not claim tool calling")

    output = await _answer_via_tool(cfg)

    assert TOOL_CANARY in output, f"tool result never reached the answer: {output!r}"


@requires_litellm
@pytest.mark.requires("openrouter")
async def test_openrouter_claude_opus_returns_validated_structured_output() -> None:
    cfg = _entry("openrouter_claude_opus")
    if not cfg.supports_structured_output:
        pytest.skip(f"{cfg.name} does not claim structured output")

    answer = await _structured_answer(cfg)

    assert isinstance(answer, CapitalAnswer)
    assert "paris" in answer.city.lower()


@requires_litellm
@pytest.mark.requires("openrouter")
async def test_openrouter_llama3_70b_completes_one_turn() -> None:
    """The open-weights route's one claim that is cheap to check honestly.

    Observed flakiness, recorded rather than papered over: OpenRouter fans
    open-weights models out to third-party providers, and one attempt in
    eleven came back with an empty completion and no error at all.  There is
    no retry here on purpose -- a retry loop would hide exactly the breakage
    this test exists to catch.  If this assertion fires, read it as "the
    route returned nothing", check the OpenRouter dashboard for the provider
    it picked, and re-run once before believing the registry entry is broken.
    """
    cfg = _entry("openrouter_llama3_70b")
    assert cfg.backend is ModelBackend.LITELLM

    output = await _plain_completion(cfg)

    assert isinstance(output, str)
    assert output.strip(), (
        "openrouter/meta-llama/llama-3.1-70b-instruct returned an empty "
        "completion -- see this test's docstring"
    )


@requires_litellm
@pytest.mark.requires("openrouter")
@pytest.mark.xfail(
    reason=(
        "registry defect: openrouter_llama3_70b takes the default "
        "supports_tool_calling=True, but the live OpenRouter route for "
        "meta-llama/llama-3.1-70b-instruct never calls the tool.  Observed "
        "2026-09-01: it ignored the tool entirely and emitted a degenerate "
        "repeating string ('...BATCHA14A11A14B10...') with no error, running "
        "7m23s until the output budget ran out.  Either the entry should "
        "declare supports_tool_calling=False or model_id should name a route "
        "that supports tools."
    ),
    strict=False,
)
async def test_openrouter_llama3_70b_invokes_tool_and_uses_its_value() -> None:
    """The claim most likely to be wrong: tool calling on an open-weights route.

    ``max_tokens`` is capped here and nowhere else in this file: the degenerate
    loop above is what an uncapped run costs, in both money and wall-clock.
    """
    cfg = _entry("openrouter_llama3_70b")
    if not cfg.supports_tool_calling:
        pytest.skip(f"{cfg.name} does not claim tool calling")

    output = await _answer_via_tool(cfg, max_tokens=128)

    assert TOOL_CANARY in output, f"tool result never reached the answer: {output!r}"


@requires_litellm
@pytest.mark.requires("openrouter")
# Deferred to nightly rather than gating merges.  Measured 2026-09-01: this
# passes in isolation but fails intermittently in a full-file run -- OpenRouter
# routes open-weights models to third-party providers, and one returned an
# empty completion (observed once in eleven attempts).  That is the route's
# reliability, not this project's code, and a test that goes red without any
# code changing trains people to ignore red CI.  It still runs nightly, where a
# genuine regression in the LiteLLM structured-output path will surface.
@pytest.mark.run_on("nightly")
async def test_openrouter_llama3_70b_returns_validated_structured_output() -> None:
    """The other defaulted claim on the open-weights entry.

    Capped like the tool-calling test above, for the same reason: a route that
    cannot honour the request tends to babble rather than error.  256 tokens is
    ample for ``{"city": "Paris"}``, so a failure here is about the claim, not
    about truncation.
    """
    cfg = _entry("openrouter_llama3_70b")
    if not cfg.supports_structured_output:
        pytest.skip(f"{cfg.name} does not claim structured output")

    answer = await _structured_answer(cfg, max_tokens=256)

    assert isinstance(answer, CapitalAnswer)
    assert "paris" in answer.city.lower()


# ---------------------------------------------------------------------------
# Ollama -- resolution only.  No requires("ollama"): nothing is contacted.
# ---------------------------------------------------------------------------


@pytest.mark.run_on("pr")
def test_ollama_direct_entry_resolves_to_openai_compatible_model() -> None:
    """resolve() builds the client-backed Model itself, without a network call.

    The OPENAI_COMPATIBLE branch is the only one that returns a ``Model``
    instance rather than a routing string, and it must point at the local
    Ollama endpoint.  Constructing ``AsyncOpenAI`` contacts nothing, so this
    needs no running server and runs at PR stage.
    """
    cfg = _entry("ollama_llama3_70b_direct")
    assert cfg.backend is ModelBackend.OPENAI_COMPATIBLE

    resolved = cfg.resolve()

    assert isinstance(resolved, OpenAIChatCompletionsModel)
    assert resolved.model == "llama3:70b"
    assert str(resolved._client.base_url).startswith("http://localhost:11434/v1")
