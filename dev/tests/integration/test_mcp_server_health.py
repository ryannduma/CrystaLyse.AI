"""Health of the three MCP servers, spoken to over a real stdio pipe.

These tests spawn the servers exactly as ``CrystaLyseConfig`` tells the agent
bridge to spawn them -- a subprocess, a pipe, and the JSON-RPC handshake -- so
they catch the failures that only appear once the process is real: an import
that raises, a tool that never gets registered, or a library that scribbles on
stdout and corrupts the protocol stream.

No API key is involved; nothing here talks to a model.  What they do need is
the chemistry stack importable in the interpreter that ``get_server_config``
picks, which is why they live in ``integration/`` rather than ``unit/``.

They are slow by nature.  ``chemistry_unified`` imports torch, MACE and a
270k-entry phase diagram before it will answer ``initialize``, which takes tens
of seconds on a warm cache and longer on a cold one -- hence the generous
:data:`STARTUP_TIMEOUT_S`.  Chemeleon and MACE *tools* are deliberately not
called here; those belong in ``e2e/`` and ``scientific_validation/``.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from crystalyse.config import CrystaLyseConfig

#: Long enough for a cold first import of torch + MACE + the phase diagram.
STARTUP_TIMEOUT_S = 300.0

#: Once ``initialize`` has been answered the imports are done, so anything that
#: is not doing physics should come back quickly.  This is also the guard that
#: turns "the server hung" into a failure instead of a wedged test run.
CALL_TIMEOUT_S = 60.0


def _spawn_env(cfg: dict[str, Any]) -> dict[str, str]:
    """The environment a server subprocess is spawned with.

    The servers are launched with ``python -m <pkg>.server`` from their own
    ``src/`` tree, so that tree has to be on ``PYTHONPATH`` for the module to
    be importable even when the package is not installed.  It is *prepended*
    rather than assigned: an inherited ``PYTHONPATH`` may be the only reason
    ``crystalyse`` itself is importable in the child, and clobbering it would
    fail the server for a reason that has nothing to do with what is under
    test.
    """
    env = dict(cfg["env"])
    inherited = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{cfg['cwd']}{os.pathsep}{inherited}" if inherited else cfg["cwd"]
    return env


def _server_params(server_name: str) -> StdioServerParameters:
    """Stdio parameters for *server_name*, straight from the shipped config.

    ``get_server_config`` hands back the command, argv and cwd the agent bridge
    uses.
    """
    cfg = CrystaLyseConfig().get_server_config(server_name)
    return StdioServerParameters(
        command=cfg["command"],
        args=list(cfg["args"]),
        cwd=cfg["cwd"],
        env=_spawn_env(cfg),
    )


@asynccontextmanager
async def _connected(server_name: str) -> AsyncIterator[ClientSession]:
    """Spawn *server_name* and yield an initialised MCP client session."""
    async with stdio_client(_server_params(server_name)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=STARTUP_TIMEOUT_S) as session:
            await session.initialize()
            yield session


# ---------------------------------------------------------------------------
# Every server starts and exposes the tool surface the agent prompts assume
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("server_name", "expected_tool_count", "expected_tool_names"),
    [
        (
            "chemistry_unified",
            20,
            ("validate_composition", "calculate_formation_energy", "generate_crystal_csp"),
        ),
        (
            "chemistry_creative",
            4,
            ("generate_crystal_structure", "creative_discovery_pipeline"),
        ),
        (
            "visualization",
            5,
            ("create_3dmol_visualization", "create_mode_aligned_visualization"),
        ),
    ],
    ids=["chemistry_unified", "chemistry_creative", "visualization"],
)
async def test_server_starts_and_lists_its_expected_tools(
    server_name: str,
    expected_tool_count: int,
    expected_tool_names: tuple[str, ...],
) -> None:
    """The server comes up over stdio and advertises the tools it is meant to.

    The count is deliberately exact: a tool silently dropped (a decorator lost
    in a refactor, a registration line deleted) is invisible to every test that
    only checks the tools it happens to name.
    """
    async with _connected(server_name) as session:
        listed = await session.list_tools()

    names = {tool.name for tool in listed.tools}
    assert len(listed.tools) == expected_tool_count, f"tools on {server_name}: {sorted(names)}"
    assert set(expected_tool_names) <= names


# ---------------------------------------------------------------------------
# stdout is the protocol channel and nothing else
# ---------------------------------------------------------------------------


def _send(proc: subprocess.Popen[str], frame: dict[str, object]) -> None:
    """Write one JSON-RPC frame, unless the server has already died."""
    if proc.poll() is not None:
        return
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(frame) + "\n")
    proc.stdin.flush()


def _wait_until(predicate: Callable[[], bool], proc: subprocess.Popen[str], timeout: float) -> None:
    """Poll until *predicate* holds, the server exits, or *timeout* elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate() or proc.poll() is not None:
            return
        time.sleep(0.1)


def _raw_handshake_stdout(server_name: str) -> list[str]:
    """Drive *server_name* with plain pipes and return every stdout line.

    Deliberately not using the MCP client: the client parses stdout for us and
    would swallow exactly the garbage this test exists to find.  stderr is
    discarded because logging belongs there -- only stdout is under test.
    """
    cfg = CrystaLyseConfig().get_server_config(server_name)
    proc = subprocess.Popen(
        [cfg["command"], *cfg["args"]],
        cwd=cfg["cwd"],
        env=_spawn_env(cfg),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    lines: list[str] = []

    def drain() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": types.LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "crystalyse-health-check", "version": "0"},
                },
            },
        )
        _wait_until(lambda: len(lines) >= 1, proc, STARTUP_TIMEOUT_S)
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        _wait_until(lambda: len(lines) >= 2, proc, CALL_TIMEOUT_S)
        if proc.stdin is not None and not proc.stdin.closed:
            proc.stdin.close()  # EOF: a well-behaved stdio server shuts down
        with suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=CALL_TIMEOUT_S)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=CALL_TIMEOUT_S)
        reader.join(timeout=CALL_TIMEOUT_S)
    return lines


def test_unified_server_writes_only_json_rpc_to_stdout() -> None:
    """Nothing but protocol frames reach stdout during a handshake.

    This is a real regression guard, not a formality: MACE prints a banner at
    import time, and when that landed on stdout it sat in front of the
    ``initialize`` response and made the server unusable.  Anything a
    dependency prints has to go to stderr.
    """
    lines = _raw_handshake_stdout("chemistry_unified")

    payloads = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            payloads.append(json.loads(text))
        except json.JSONDecodeError as exc:
            pytest.fail(f"non-JSON line on chemistry_unified stdout: {text!r} ({exc})")

    # Without this the check above passes vacuously on a server that said
    # nothing at all, which is a different failure entirely.
    assert {1, 2} <= {payload.get("id") for payload in payloads}, (
        f"handshake did not complete; stdout was {lines!r}"
    )
    assert all(payload.get("jsonrpc") == "2.0" for payload in payloads)


# ---------------------------------------------------------------------------
# Tool calls round-trip, including the ones that should fail
# ---------------------------------------------------------------------------


async def test_validate_composition_round_trips_over_stdio() -> None:
    """A cheap tool call reaches SMACT and its answer comes back intact."""
    async with _connected("chemistry_unified") as session:
        result = await session.call_tool(
            "validate_composition",
            {"composition": "NaCl"},
            read_timeout_seconds=CALL_TIMEOUT_S,
        )

    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload["valid"] is True
    assert payload["formula"] == "NaCl"


async def test_unknown_tool_returns_an_error_result_instead_of_hanging() -> None:
    """An unregistered tool name is answered, not ignored.

    ``read_timeout_seconds`` is the point of the test: a server that never
    replies fails here with a timeout rather than wedging the run.
    """
    async with _connected("chemistry_unified") as session:
        result = await session.call_tool(
            "no_such_tool",
            {},
            read_timeout_seconds=CALL_TIMEOUT_S,
        )

    assert result.is_error is True
    assert "no_such_tool" in result.content[0].text
