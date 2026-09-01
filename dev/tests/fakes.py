"""Fakes and synthetic-data builders shared across the test suite.

Why fakes rather than ``MagicMock``: a mock accepts any call and invents a
return value, so a test using one can pass while the code under test calls a
method the real dependency no longer has.  A fake implements the same interface
as the real thing, so that drift shows up as an ``AttributeError`` or
``TypeError`` at test time instead of in production.

Where a ``Protocol`` exists in the package, the fake is annotated against it,
which makes the protocol the single source of truth for both sides.

Everything here builds its own data.  No test needs the network, an API key,
or a file someone uploaded.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Synthetic structures
# ---------------------------------------------------------------------------

#: Rock-salt NaCl, conventional 8-atom cell, a = 5.64 A.
#: Small enough to be fast, real enough that space-group and coordination
#: analysis return known answers (Fm-3m, #225, CN 6).
NACL_STRUCTURE: dict[str, Any] = {
    "numbers": [11, 11, 11, 11, 17, 17, 17, 17],
    "positions": [
        [0.0, 0.0, 0.0],
        [0.0, 2.82, 2.82],
        [2.82, 0.0, 2.82],
        [2.82, 2.82, 0.0],
        [2.82, 0.0, 0.0],
        [0.0, 2.82, 0.0],
        [0.0, 0.0, 2.82],
        [2.82, 2.82, 2.82],
    ],
    "cell": [[5.64, 0.0, 0.0], [0.0, 5.64, 0.0], [0.0, 0.0, 5.64]],
    "pbc": [True, True, True],
}


def make_structure(
    numbers: list[int] | None = None,
    positions: list[list[float]] | None = None,
    cell: list[list[float]] | None = None,
    pbc: list[bool] | None = None,
) -> dict[str, Any]:
    """Build a structure dict, defaulting to rock-salt NaCl.

    Pass only what the test cares about; the rest stays valid.  Use this rather
    than mutating ``NACL_STRUCTURE``, which is module-level and shared.
    """
    return {
        "numbers": list(NACL_STRUCTURE["numbers"] if numbers is None else numbers),
        "positions": [
            list(p) for p in (NACL_STRUCTURE["positions"] if positions is None else positions)
        ],
        "cell": [list(v) for v in (NACL_STRUCTURE["cell"] if cell is None else cell)],
        "pbc": list(NACL_STRUCTURE["pbc"] if pbc is None else pbc),
    }


def make_cif(formula: str = "NaCl", a: float = 5.64) -> str:
    """Generate a real CIF via pymatgen, so it parses like a real one.

    Built rather than read from disk: the test states its own inputs and cannot
    break because a fixture file changed.
    """
    from pymatgen.core import Lattice, Structure

    structure = Structure.from_spacegroup(
        "Fm-3m", Lattice.cubic(a), ["Na", "Cl"], [[0, 0, 0], [0.5, 0, 0]]
    )
    return structure.to(fmt="cif")


# ---------------------------------------------------------------------------
# Checkpoint download / extraction fakes
# ---------------------------------------------------------------------------


def checkpoint_payload(name: str) -> bytes:
    """The exact bytes ``make_checkpoint_archive`` stores for the member *name*.

    Exposed so a test can assert a checkpoint really came out of the archive,
    rather than only that some non-empty file appeared at the right path.
    """
    return f"fake checkpoint bytes for {name}".encode()


def make_checkpoint_archive(filenames: list[str], *, nest_in: str | None = "ckpts") -> bytes:
    """Build a .tar.gz containing named ``.ckpt`` files.

    ``nest_in`` reproduces the real Figshare archive's top-level ``ckpts/``
    directory, which is the whole reason the extraction code needs to flatten.
    Pass ``None`` for a flat archive.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in filenames:
            payload = checkpoint_payload(name)
            member = tarfile.TarInfo(f"{nest_in}/{name}" if nest_in else name)
            member.size = len(payload)
            tar.addfile(member, io.BytesIO(payload))
    return buf.getvalue()


class FakeDownloader:
    """Stands in for ``checkpoint_manager.Downloader``.

    Records what was requested so a test can assert the download happened
    exactly once, and writes real bytes so extraction genuinely runs.
    """

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[tuple[str, Path]] = []

    def __call__(self, url: str, filepath: Path) -> None:
        self.calls.append((url, filepath))
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(self.payload)


class FailingDownloader:
    """A downloader that always fails, for testing cleanup on error."""

    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc or RuntimeError("network unreachable")
        self.calls: list[tuple[str, Path]] = []

    def __call__(self, url: str, filepath: Path) -> None:
        self.calls.append((url, filepath))
        raise self.exc


class PartialDownloader:
    """Writes part of the archive, then fails: an interrupted transfer.

    ``FailingDownloader`` never touches the filesystem, so a test using it
    cannot tell whether the caller cleans up -- the assertion "no partial file
    remains" would hold even with the cleanup deleted.  This one leaves a
    truncated file behind for the code under test to remove.
    """

    def __init__(
        self, partial: bytes = b"\x1f\x8b truncated", exc: Exception | None = None
    ) -> None:
        self.partial = partial
        self.exc = exc or RuntimeError("connection reset mid-transfer")
        self.calls: list[tuple[str, Path]] = []

    def __call__(self, url: str, filepath: Path) -> None:
        self.calls.append((url, filepath))
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(self.partial)
        raise self.exc


def real_extractor(filepath: Path, extract_to: Path) -> None:
    """The genuine tar extraction, usable with a fake downloader.

    Keeping extraction real is deliberate: the flattening logic is what the
    checkpoint tests are about, so faking it would test nothing.
    """
    from crystalyse.tools.chemeleon.checkpoint_manager import _extract_tar_gz

    _extract_tar_gz(filepath, extract_to)


# ---------------------------------------------------------------------------
# MCP fakes
# ---------------------------------------------------------------------------


class FakeToolResult:
    """Mirrors the shape of ``mcp.types.CallToolResult`` that callers read.

    Deliberately uses mcp 2.0's snake_case ``is_error``: a fake carrying the
    old ``isError`` would hide exactly the rename that broke the servers.
    """

    def __init__(self, text: str, is_error: bool = False) -> None:
        self.content = [FakeTextContent(text)]
        self.is_error = is_error
        self.structured_content: dict[str, Any] | None = None


class FakeTextContent:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class FakeMCPServer:
    """A stand-in for one MCP server, holding a fixed tool list and responses.

    Enough to exercise agent-side routing, mode handling and error paths
    without spawning a subprocess.  A tool that was not configured raises,
    rather than returning a plausible-looking mock.
    """

    def __init__(self, name: str, tools: dict[str, Any] | None = None) -> None:
        self.name = name
        self._tools = tools or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def cleanup(self) -> None:
        self.connected = False

    async def list_tools(self) -> list[str]:
        return sorted(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> FakeToolResult:
        if not self.connected:
            raise RuntimeError(f"{self.name}: call_tool before connect")
        if name not in self._tools:
            raise KeyError(
                f"{self.name} has no tool {name!r}; configured: {sorted(self._tools)}. "
                f"A real server would return an error result -- if that is the case "
                f"under test, configure the tool to return one."
            )
        self.calls.append((name, dict(arguments)))
        value = self._tools[name]
        return value(arguments) if callable(value) else value
