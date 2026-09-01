"""Behaviour of ``crystalyse.agents.mode_injector``.

``create_mode_aware_instructions`` is appended to the system prompt on *every*
agent run, so whatever it says is what the model believes about its tools.  It
names three analysis tools and promises that a missing ``mode`` argument will be
filled in automatically.  Neither claim holds, so the tests that pin the correct
behaviour are marked ``xfail`` with the defect named in the reason:

* only ``comprehensive_materials_analysis`` is registered by any server, and
  only by ``chemistry_creative`` -- so in ``validate``/``auto`` mode, where the
  chemistry server is ``chemistry_unified``, none of the three exist;
* ``inject_mode_into_mcp_servers`` sets a global and returns its argument list
  untouched, so nothing injects anything into a tool call.

The server tool inventories below are transcribed from the ``@mcp.tool()``
declarations in ``dev/*-server/src/*/server.py``.  They are synthetic data --
the tests never import or launch a server -- so if a server gains or loses a
tool this file has to be updated by hand; that is the trade for keeping these
tests hermetic and in ``unit/``.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from crystalyse.agents.mode_injector import (
    GlobalModeManager,
    ModeInjectingToolWrapper,
    create_mode_aware_instructions,
    inject_mode_into_mcp_servers,
)
from crystalyse.config.modes import MODE_MCP_SERVERS, Mode
from tests.fakes import FakeMCPServer, FakeToolResult

# ---------------------------------------------------------------------------
# Synthetic server inventory
# ---------------------------------------------------------------------------

SERVER_TOOLS: dict[str, tuple[str, ...]] = {
    "chemistry_creative": (
        "generate_crystal_structure",
        "calculate_formation_energy",
        "creative_discovery_pipeline",
        "comprehensive_materials_analysis",
    ),
    "chemistry_unified": (
        "validate_composition",
        "analyze_stability",
        "predict_band_gap",
        "generate_crystal_csp",
        "calculate_formation_energy",
        "relax_structure",
        "analyze_space_group",
        "calculate_energy_above_hull",
        "analyze_coordination",
        "validate_oxidation_states",
        "save_cif_file",
        "create_analysis_suite",
        "smact_validate_fast",
        "generate_ml_representation",
        "filter_compositions",
        "predict_dopants",
        "calculate_stress",
        "fit_equation_of_state",
        "list_foundation_models",
        "get_server_info",
    ),
    "visualization": (
        "create_3dmol_visualization",
        "create_pymatviz_analysis_suite",
        "create_creative_visualization",
        "create_rigorous_visualization",
        "create_mode_aligned_visualization",
    ),
}


def make_server(name: str) -> FakeMCPServer:
    """One fake server carrying the tool names the real one registers."""
    return FakeMCPServer(name, {tool: FakeToolResult("{}") for tool in SERVER_TOOLS[name]})


def servers_for_mode(mode: Mode) -> list[FakeMCPServer]:
    """The server pair the agent bridge starts for *mode*: chemistry + viz."""
    return [make_server(MODE_MCP_SERVERS[mode]), make_server("visualization")]


#: Matches the ``- tool_name(mode="...", ...)`` bullets in the generated block.
_TOOL_BULLET = re.compile(r"^- ([a-z_][a-z0-9_]*)\(", re.MULTILINE)


def tools_named_in(instructions: str) -> set[str]:
    return set(_TOOL_BULLET.findall(instructions))


# ---------------------------------------------------------------------------
# create_mode_aware_instructions -- what it tells the model to call
# ---------------------------------------------------------------------------


def test_instructions_name_three_analysis_tools() -> None:
    """Pins the parse the tool-existence tests below depend on."""
    assert tools_named_in(create_mode_aware_instructions("base", "explore")) == {
        "comprehensive_materials_analysis",
        "chemistry_creative_analysis",
        "materials_discovery_pipeline",
    }


@pytest.mark.xfail(
    strict=True,
    reason=(
        "create_mode_aware_instructions advertises chemistry_creative_analysis and "
        "materials_discovery_pipeline, which no MCP server registers, and "
        "comprehensive_materials_analysis, which only chemistry_creative registers -- "
        "so in validate/auto mode none of the three tools exist"
    ),
)
@pytest.mark.parametrize(
    "mode",
    [Mode.EXPLORE, Mode.VALIDATE, Mode.AUTO],
    ids=["explore", "validate", "auto"],
)
async def test_every_tool_named_in_instructions_exists_on_a_running_server(mode: Mode) -> None:
    available: set[str] = set()
    for server in servers_for_mode(mode):
        await server.connect()
        available.update(await server.list_tools())

    named = tools_named_in(create_mode_aware_instructions("base", mode.value))
    assert named <= available, f"instructions name missing tools: {sorted(named - available)}"


@pytest.mark.parametrize(
    "mode",
    ["explore", "validate", "auto"],
    ids=["explore", "validate", "auto"],
)
def test_instructions_spell_out_the_mode_argument_for_every_named_tool(mode: str) -> None:
    instructions = create_mode_aware_instructions("base", mode)
    named = tools_named_in(instructions)
    assert named, "no tool bullets parsed -- _TOOL_BULLET no longer matches the block"
    for tool in named:
        assert f'{tool}(mode="{mode}"' in instructions


@pytest.mark.parametrize(
    "mode",
    ["explore", "validate", "auto"],
    ids=["explore", "validate", "auto"],
)
def test_instructions_state_the_session_mode_in_upper_case(mode: str) -> None:
    assert f"THE CURRENT SESSION MODE IS: {mode.upper()}" in create_mode_aware_instructions(
        "base", mode
    )


def test_base_instructions_are_kept_verbatim_at_the_front() -> None:
    base = "You are CrystaLyse.\n\nAnswer in British English.\n"
    assert create_mode_aware_instructions(base, "validate").startswith(base)


@pytest.mark.parametrize(
    "mode",
    ["explore", "validate", "auto"],
    ids=["explore", "validate", "auto"],
)
def test_no_second_mode_is_mandated_in_the_appended_block(mode: str) -> None:
    """A stale mode literal anywhere in the block would give the model two
    mandates, and it is the block that overrides all other instructions."""
    appended = create_mode_aware_instructions("base", mode).removeprefix("base")
    assert set(re.findall(r'mode="([a-z]+)"', appended)) == {mode}


# ---------------------------------------------------------------------------
# inject_mode_into_mcp_servers
# ---------------------------------------------------------------------------


def test_inject_mode_returns_the_same_server_objects_it_was_given() -> None:
    """Despite the name, the function wraps nothing: it hands back the identical
    list, so callers keep talking to the servers they passed in."""
    servers = servers_for_mode(Mode.EXPLORE)
    returned = inject_mode_into_mcp_servers(servers, "explore")
    assert returned is servers
    assert [s.name for s in returned] == ["chemistry_creative", "visualization"]


async def test_inject_mode_leaves_the_server_tool_lists_alone() -> None:
    """Whatever the injector does, the agent must still see exactly the tools
    the server registered -- none added, dropped or renamed."""
    server = make_server("chemistry_unified")
    before = await server.list_tools()
    assert before == sorted(SERVER_TOOLS["chemistry_unified"])

    (returned,) = inject_mode_into_mcp_servers([server], "validate")

    assert await returned.list_tools() == before


def test_inject_mode_accepts_an_empty_server_list() -> None:
    """The bridge appends servers only if they started, so this list can be empty."""
    assert inject_mode_into_mcp_servers([], "auto") == []


def test_inject_mode_publishes_the_mode_to_the_global_manager() -> None:
    inject_mode_into_mcp_servers(servers_for_mode(Mode.VALIDATE), "validate")
    assert GlobalModeManager.get_mode() == "validate"
    assert GlobalModeManager.is_locked() is True


@pytest.mark.xfail(
    strict=True,
    reason=(
        "inject_mode_into_mcp_servers only sets GlobalModeManager and returns its "
        "argument unchanged -- no tool is wrapped -- so the prompt's claim that the "
        "'Mode parameter will be automatically injected if missing' is false"
    ),
)
async def test_injected_servers_add_the_mode_to_a_call_that_omits_it() -> None:
    server = make_server("chemistry_creative")
    await server.connect()
    (returned,) = inject_mode_into_mcp_servers([server], "validate")

    await returned.call_tool("comprehensive_materials_analysis", {"compositions": ["NaCl"]})

    _, arguments = server.calls[-1]
    assert arguments.get("mode") == "validate"


# ---------------------------------------------------------------------------
# GlobalModeManager
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def restore_global_mode():
    """``GlobalModeManager`` keeps its state in class attributes, so anything a
    test sets leaks into the next one and into the rest of the session.  Save
    and restore around each test rather than reaching for monkeypatch."""
    mode, locked = GlobalModeManager.get_mode(), GlobalModeManager.is_locked()
    yield
    GlobalModeManager._current_mode = mode
    GlobalModeManager._mode_locked = locked


def test_default_mode_is_auto() -> None:
    assert GlobalModeManager.get_mode() == "auto"


@pytest.mark.parametrize(
    "mode",
    ["explore", "validate", "auto"],
    ids=["explore", "validate", "auto"],
)
def test_set_mode_then_get_mode_round_trips(mode: str) -> None:
    GlobalModeManager.set_mode(mode)
    assert GlobalModeManager.get_mode() == mode


def test_set_mode_locks_the_mode_by_default() -> None:
    GlobalModeManager.set_mode("explore")
    assert GlobalModeManager.is_locked() is True


def test_set_mode_can_leave_the_mode_unlocked() -> None:
    GlobalModeManager.set_mode("explore", lock_mode=False)
    assert GlobalModeManager.is_locked() is False


def test_unlock_mode_clears_the_lock_and_keeps_the_mode() -> None:
    GlobalModeManager.set_mode("explore", lock_mode=True)
    GlobalModeManager.unlock_mode()
    assert GlobalModeManager.is_locked() is False
    assert GlobalModeManager.get_mode() == "explore"


def test_every_instance_shares_one_mode() -> None:
    """The manager is used as a process-wide singleton; two instances must not
    disagree about which mode the session is in."""
    first, second = GlobalModeManager(), GlobalModeManager()
    GlobalModeManager.set_mode("explore")
    assert first.get_mode() == second.get_mode() == "explore"


def test_an_unknown_mode_leaves_the_current_mode_in_place() -> None:
    """set_mode swallows bad input rather than raising -- pinned as-is, but it
    means a typo'd mode silently runs the previous one."""
    GlobalModeManager.set_mode("validate")
    GlobalModeManager.set_mode("rigourous")
    assert GlobalModeManager.get_mode() == "validate"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "set_mode validates against MODE_ALIASES but never resolves, so get_mode() "
        "hands back the deprecated alias; AgentsBridge normalises its own self.mode "
        "with resolve_mode_name and then passes the raw string here, leaving the two "
        "disagreeing about the session mode"
    ),
)
@pytest.mark.parametrize(
    "alias, canonical",
    [("creative", "explore"), ("rigorous", "validate"), ("adaptive", "auto")],
    ids=["creative-is-explore", "rigorous-is-validate", "adaptive-is-auto"],
)
def test_a_deprecated_alias_is_stored_as_its_canonical_mode(alias: str, canonical: str) -> None:
    GlobalModeManager.set_mode(alias)
    assert GlobalModeManager.get_mode() == canonical


@pytest.mark.xfail(
    strict=True,
    reason=(
        "_mode_locked is set by set_mode but never read by it, so 'locking' the mode "
        "does not stop a later set_mode from overwriting it"
    ),
)
def test_a_locked_mode_cannot_be_changed_by_a_later_set_mode() -> None:
    GlobalModeManager.set_mode("validate", lock_mode=True)
    GlobalModeManager.set_mode("explore")
    assert GlobalModeManager.get_mode() == "validate"


# ---------------------------------------------------------------------------
# ModeInjectingToolWrapper
# ---------------------------------------------------------------------------


class RecordingTool:
    """A stand-in for one MCP tool that records the arguments it was called with."""

    def __init__(self, result: Any = "ok") -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        return self.result


async def test_wrapper_adds_the_mode_when_the_agent_omits_it() -> None:
    tool = RecordingTool()
    wrapper = ModeInjectingToolWrapper(tool, "validate", "comprehensive_materials_analysis")

    await wrapper(compositions=["NaCl"])

    assert tool.calls == [{"compositions": ["NaCl"], "mode": "validate"}]


async def test_wrapper_overrides_a_mode_the_agent_supplied() -> None:
    tool = RecordingTool()
    wrapper = ModeInjectingToolWrapper(tool, "validate", "comprehensive_materials_analysis")

    await wrapper(compositions=["NaCl"], mode="explore")

    assert tool.calls[-1]["mode"] == "validate"


async def test_wrapper_returns_the_tools_own_result() -> None:
    tool = RecordingTool(result={"structures": 3})
    wrapper = ModeInjectingToolWrapper(tool, "explore", "comprehensive_materials_analysis")

    assert await wrapper(compositions=["NaCl"]) == {"structures": 3}


async def test_wrapper_leaves_a_mode_free_tool_untouched() -> None:
    tool = RecordingTool()
    wrapper = ModeInjectingToolWrapper(tool, "validate", "save_cif_file")

    await wrapper(cif_content="data_NaCl", formula="NaCl")

    assert tool.calls == [{"cif_content": "data_NaCl", "formula": "NaCl"}]


async def test_wrapper_propagates_a_failure_from_the_tool() -> None:
    class FailingTool:
        async def __call__(self, **kwargs: Any) -> Any:
            raise RuntimeError("MACE unavailable")

    wrapper = ModeInjectingToolWrapper(FailingTool(), "validate", "analyze_stability")

    with pytest.raises(RuntimeError, match="MACE unavailable"):
        await wrapper(composition="NaCl")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "the wrapper injects mode into any tool whose name contains 'analysis', which "
        "catches create_analysis_suite and create_pymatviz_analysis_suite -- neither "
        "declares a mode parameter, so the real call raises TypeError"
    ),
)
async def test_wrapper_does_not_inject_mode_into_an_analysis_tool_that_takes_none() -> None:
    async def create_analysis_suite(*, cif_content: str, formula: str) -> str:
        return f"{formula}: {len(cif_content)} chars"

    wrapper = ModeInjectingToolWrapper(create_analysis_suite, "validate", "create_analysis_suite")

    assert await wrapper(cif_content="data_NaCl", formula="NaCl") == "NaCl: 9 chars"
