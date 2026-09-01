"""End-to-end discovery flows: mode and model selection, and the chemistry stack.

Three flows live in this file, in increasing order of what they cost to run:

* **Selection** -- construct ``EnhancedCrystaLyseAgent`` in each mode and check
  that the mode picks its chemistry MCP server and its default backbone.  No
  query is run and no server is started: selection is the whole claim, and it
  costs nothing.  One test does start the ``explore`` servers for real, because
  the mapping is only worth anything if the named server exists and comes up.
* **Chemistry** -- Chemeleon -> MACE -> pymatgen, driven over MCP with no model
  in the loop.  Needs the cached checkpoints; needs no API key.
* **Agent** -- one real ``discover()`` call.  It spends money, so it is
  ``run_on("nightly")`` and skips without a key.

Things to know before adding to this file:

* ``discover()`` resolves the model *inside* itself (``resolve_model_name`` on
  ``self.model``, or ``_select_model_for_mode`` when no model was given), and
  the resolved value is never stored on the agent.  A test that must not call an
  API can therefore only assert that the constructor carries the choice and
  that the resolver the agent calls maps two names to two different backbones.
* ``discover()`` hardcodes ``max_turns=1000`` and takes no turn-limit argument,
  so the only lever on the cost of a live run is ``config.mode_timeouts`` and
  the size of the query.
* Importing the ``chemistry_unified`` server constructs ``PhaseDiagramAnalyzer``
  at module scope, which downloads a 170 MB phase-diagram pickle when the cache
  is cold.  Tests that start that server therefore also carry
  ``requires("phase_diagram")``: not because the chemistry needs the hull data,
  but so that a cold CI machine skips instead of pulling 170 MB.
* Chemeleon is a diffusion model with no seed argument, so the space group of a
  generated NaCl sample varies between runs (Fm-3m in three of four sampled
  runs, F-43m in the fourth).  The Fm-3m/225 assertion therefore lives in the
  synthetic rock-salt test, where it is deterministic, and the generated-
  structure test asserts only what a generative model can promise.
"""

from __future__ import annotations

import json
import math
from contextlib import asynccontextmanager
from typing import Any

import pytest

from crystalyse.agents.agents_bridge import EnhancedCrystaLyseAgent
from crystalyse.agents.mode_injector import GlobalModeManager
from crystalyse.config import Config
from crystalyse.config.models import MODE_DEFAULTS, resolve_model_config, resolve_model_name
from crystalyse.config.modes import MODE_MCP_SERVERS, Mode
from tests.fakes import make_structure

# For each chemistry server, one tool that only it registers.  These tell the
# two servers apart by what they can actually do, rather than by the display
# name the bridge builds for them.  Transcribed from the ``@mcp.tool``
# declarations and checked against the live surface by the tests below -- which
# is the point of keeping them here rather than in a unit test.
SIGNATURE_TOOL: dict[str, str] = {
    "chemistry_creative": "creative_discovery_pipeline",
    "chemistry_unified": "generate_crystal_csp",
}

# Every chemistry server has this one; the visualization server does not.
CHEMISTRY_MARKER_TOOL = "calculate_formation_energy"

# ``discover()`` initialises ``final_response`` to this literal and only
# overwrites it if the stream actually yields text, yet it returns
# ``status="completed"`` either way (agents_bridge.py: the result dict is built
# unconditionally on the non-exception path).  A live test that asserts only
# "status is completed and response is a non-empty string" therefore passes when
# the model produced nothing at all, so the live test below rules this value out
# explicitly.  Keep in sync with ``agents_bridge.discover``.
NO_RESPONSE_SENTINEL = "No response generated."


@pytest.fixture(autouse=True)
def restore_global_mode():
    """Constructing an agent writes the session mode into a process-wide
    singleton.  Save and restore it so these tests do not leak a mode into the
    rest of the session."""
    mode, locked = GlobalModeManager.get_mode(), GlobalModeManager.is_locked()
    yield
    GlobalModeManager._current_mode = mode
    GlobalModeManager._mode_locked = locked


@pytest.fixture
def private_home(tmp_path, monkeypatch):
    """Point ``Path.home()`` at a scratch directory.

    The constructor opens a SQLite session under ``~/.crystalyse/sessions``.
    Tests that only construct an agent have no business writing into the
    developer's real home, and no server is started that would want the caches
    that live there.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def dummy_provider_keys(monkeypatch):
    """Satisfy ``ModelConfig.validate_env()`` without a real key.

    Resolution gates on the *presence* of the provider's env var and there is no
    seam to inject that check, so the environment is the only lever.  Nothing
    here reaches a provider: the tests that use this fixture resolve a model
    name and stop.
    """
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(var, "not-a-real-key-no-request-is-made")


def make_agent(mode: str, model: str | None = None) -> EnhancedCrystaLyseAgent:
    """Construct an agent the way the CLI does, with a test-owned session name."""
    return EnhancedCrystaLyseAgent(
        config=Config.load(),
        project_name="pytest_e2e_discovery_flows",
        mode=mode,
        model=model,
    )


async def tool_names(server: Any) -> set[str]:
    return {tool.name for tool in await server.list_tools()}


def tool_payload(result: Any, tool: str) -> dict[str, Any]:
    """Decode one MCP tool result into the dict the tool returned."""
    assert not result.is_error, f"{tool} returned an MCP error: {result.content}"
    assert result.content, f"{tool} returned no content"
    payload = json.loads(result.content[0].text)
    assert payload.get("success") is True, f"{tool} failed: {payload.get('error')}"
    return payload


@asynccontextmanager
async def chemistry_server_of(agent: EnhancedCrystaLyseAgent):
    """Yield the chemistry MCP server the agent itself starts for its mode.

    ``_managed_mcp_servers`` logs and swallows a server that fails to come up,
    so a missing chemistry server is reported here rather than surfacing as a
    confusing ``StopIteration`` inside a test.
    """
    async with agent._managed_mcp_servers() as servers:
        chemistry = [s for s in servers if CHEMISTRY_MARKER_TOOL in await tool_names(s)]
        assert len(chemistry) == 1, (
            f"expected exactly one chemistry server for mode {agent.mode!r}, "
            f"got {[s.name for s in chemistry]} out of {[s.name for s in servers]}"
        )
        yield chemistry[0]


# ---------------------------------------------------------------------------
# Mode switching -- construction and selection, no query, no cost
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode, expected_server",
    [
        ("explore", "chemistry_creative"),
        ("validate", "chemistry_unified"),
        ("auto", "chemistry_unified"),
    ],
    ids=["explore", "validate", "auto"],
)
def test_mode_selects_a_launchable_chemistry_server(
    mode: str, expected_server: str, private_home
) -> None:
    """The mode an agent carries maps to a chemistry server that can be
    launched: a name ``Config`` knows, a module to run, and a cwd on disk.

    Only canonical mode names are passed here, so the deprecated-alias half of
    ``resolve_mode_name`` is deliberately not exercised -- that is already
    covered directly in ``tests/unit/config/test_modes.py``.  The "cwd on disk"
    and "python on PATH" halves of the claim are checked by
    ``get_server_config`` itself, which raises ``FileNotFoundError`` rather than
    returning a config that cannot be launched; hence no separate assertion.
    """
    agent = make_agent(mode)

    assert agent.mode == mode
    assert MODE_MCP_SERVERS[Mode(agent.mode)] == expected_server

    server_config = agent.config.get_server_config(expected_server)
    assert server_config["args"] == ["-m", f"{expected_server}.server"]


@pytest.mark.parametrize(
    "mode, expected_model",
    [
        ("explore", "openai_o4_mini"),
        ("validate", "openai_o3"),
        ("auto", "openai_o4_mini"),
    ],
    ids=["explore", "validate", "auto"],
)
def test_mode_selects_its_default_backbone(
    mode: str, expected_model: str, private_home, dummy_provider_keys
) -> None:
    """With no explicit model, the agent resolves the mode's ``MODE_DEFAULTS``
    entry -- and resolves it to that entry's provider model id."""
    agent = make_agent(mode)

    assert MODE_DEFAULTS[mode] == expected_model
    entry = resolve_model_config(None, mode=agent.mode)
    assert entry is not None and entry.name == expected_model
    assert agent._select_model_for_mode(agent.mode) == entry.model_id


def test_explore_and_validate_do_not_share_one_backbone(private_home, dummy_provider_keys) -> None:
    """The two modes must not collapse onto one model: validate exists to spend
    more reasoning than explore."""
    explore = make_agent("explore")
    validate = make_agent("validate")

    explore_model = explore._select_model_for_mode(explore.mode)
    validate_model = validate._select_model_for_mode(validate.mode)

    assert explore_model != validate_model


@pytest.mark.run_on("main")
@pytest.mark.timeout(300)
async def test_explore_mode_starts_the_creative_chemistry_server(private_home) -> None:
    """The server the bridge actually starts for ``explore`` is the creative one.

    Checked by its live tool surface: the creative server has its own discovery
    pipeline and deliberately carries no SMACT validation, which is exactly what
    distinguishes it from ``chemistry_unified``.
    """
    agent = make_agent("explore")

    async with chemistry_server_of(agent) as chemistry:
        surface = await tool_names(chemistry)

    assert SIGNATURE_TOOL["chemistry_creative"] in surface
    assert SIGNATURE_TOOL["chemistry_unified"] not in surface
    assert "validate_composition" not in surface


# ---------------------------------------------------------------------------
# Model switching -- two registry entries, two backbones, still no API call
# ---------------------------------------------------------------------------


def test_an_explicit_model_is_carried_through_construction(private_home) -> None:
    """``model=`` survives construction unchanged, for both a registry name that
    the mode default would otherwise have chosen and one from another provider."""
    openai_agent = make_agent("auto", model="openai_o4_mini")
    anthropic_agent = make_agent("auto", model="anthropic_claude_haiku")

    assert openai_agent.model == "openai_o4_mini"
    assert anthropic_agent.model == "anthropic_claude_haiku"


def test_two_explicit_models_resolve_to_different_backbones(
    private_home, dummy_provider_keys
) -> None:
    """Two agents in the same mode with different ``model=`` names resolve to
    different backbones, each routed for its own provider: a bare model id for
    the OpenAI backend, a ``litellm/``-prefixed string for Anthropic."""
    openai_agent = make_agent("auto", model="openai_o4_mini")
    anthropic_agent = make_agent("auto", model="anthropic_claude_haiku")

    openai_backbone = resolve_model_name(openai_agent.model)
    anthropic_backbone = resolve_model_name(anthropic_agent.model)

    assert openai_backbone != anthropic_backbone
    assert openai_backbone == resolve_model_config("openai_o4_mini").model_id
    assert anthropic_backbone.startswith("litellm/")
    assert anthropic_backbone.endswith(resolve_model_config("anthropic_claude_haiku").model_id)


# ---------------------------------------------------------------------------
# Chemistry pipeline -- Chemeleon -> MACE -> pymatgen over MCP, no LLM
# ---------------------------------------------------------------------------


@pytest.mark.requires("chemeleon_checkpoints", "mace_model", "phase_diagram")
@pytest.mark.run_on("main")
@pytest.mark.timeout(1200)
async def test_generated_structure_flows_from_chemeleon_through_mace_to_symmetry() -> None:
    """A structure Chemeleon generates is accepted, unmodified, by MACE and by
    the symmetry analyser -- the handoff every discovery run depends on.

    The specific space group is left to the deterministic test below: Chemeleon
    samples, so pinning 225 here would fail roughly one run in four.
    """
    agent = make_agent("validate")

    async with chemistry_server_of(agent) as chemistry:
        generated = tool_payload(
            await chemistry.call_tool(
                "generate_crystal_csp", {"formulas": ["NaCl"], "num_samples": 1}
            ),
            "generate_crystal_csp",
        )
        structure = generated["predicted_structures"][0]

        energy = tool_payload(
            await chemistry.call_tool("calculate_formation_energy", {"structure_dict": structure}),
            "calculate_formation_energy",
        )
        symmetry = tool_payload(
            await chemistry.call_tool("analyze_space_group", {"structure_input": structure}),
            "analyze_space_group",
        )

    numbers = structure["numbers"]
    assert numbers.count(11) == numbers.count(17) > 0, f"not an equimolar NaCl: {numbers}"

    formation_energy = energy["formation_energy"]
    assert math.isfinite(formation_energy)
    assert formation_energy < 0, f"NaCl should be bound, got {formation_energy} eV/atom"
    assert math.isfinite(energy["total_energy"])

    assert 1 <= symmetry["space_group_number"] <= 230
    assert symmetry["space_group_symbol"]
    assert symmetry["primitive_formula"] == "NaCl"


@pytest.mark.requires("mace_model", "phase_diagram")
@pytest.mark.run_on("main")
@pytest.mark.timeout(900)
async def test_rock_salt_is_fm3m_and_bound_over_mcp() -> None:
    """The same two tools, on a synthetic rock-salt cell with a known answer.

    This is the numerical half of the pipeline test, split out because it is the
    half that can assert a specific space group: NaCl at a = 5.64 A is Fm-3m,
    #225, and it is bound.
    """
    agent = make_agent("validate")
    rock_salt = make_structure()

    async with chemistry_server_of(agent) as chemistry:
        energy = tool_payload(
            await chemistry.call_tool("calculate_formation_energy", {"structure_dict": rock_salt}),
            "calculate_formation_energy",
        )
        symmetry = tool_payload(
            await chemistry.call_tool("analyze_space_group", {"structure_input": rock_salt}),
            "analyze_space_group",
        )

    assert symmetry["space_group_symbol"] == "Fm-3m"
    assert symmetry["space_group_number"] == 225
    assert symmetry["crystal_system"] == "cubic"

    formation_energy = energy["formation_energy"]
    assert math.isfinite(formation_energy)
    assert formation_energy < 0, f"rock-salt NaCl should be bound, got {formation_energy} eV/atom"


# ---------------------------------------------------------------------------
# One live agent run -- costs money, so nightly only
# ---------------------------------------------------------------------------


@pytest.mark.requires("openai")
@pytest.mark.run_on("nightly")
@pytest.mark.timeout(600)
async def test_a_live_discovery_run_returns_a_status_and_a_response(tmp_path) -> None:
    """One real ``discover()`` call, end to end: MCP servers up, provenance on,
    render gate on, and a result dict a caller can read.

    Kept to a single trivial turn on the cheapest registered model.  There is no
    ``max_turns`` argument on ``discover()`` (it hardcodes 1000), so the only
    guards available are the query and the mode timeout.
    """
    config = Config.load()
    config.mode_timeouts["explore"] = 150
    config.provenance["output_dir"] = tmp_path / "provenance"

    agent = EnhancedCrystaLyseAgent(
        config=config,
        project_name="pytest_e2e_live_discovery",
        mode="explore",
        model="openai_gpt4o_mini",
    )
    agent.clear_session_memory()

    result = await agent.discover(
        "Reply with the single word: ready. Do not call any tools and do not explain."
    )

    assert result["status"] == "completed", result
    assert isinstance(result["response"], str)
    assert result["response"].strip()
    # Without this the assertions above hold even when the stream yielded no
    # text at all -- see NO_RESPONSE_SENTINEL.  This is the only assertion in
    # the test that distinguishes "the model answered" from "nothing came back".
    assert result["response"].strip() != NO_RESPONSE_SENTINEL, (
        "discover() reported completed but returned its no-output placeholder"
    )
