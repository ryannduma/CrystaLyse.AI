"""
Contract test: no pyproject.toml in this repo may declare an uncapped torch dep.

torch 2.11.0 bumped its CUDA runtime to 13.0, which requires an NVIDIA driver
new enough to support CUDA 13 (roughly driver 555+). On any machine whose
driver tops out at CUDA 12.x — which is still the common case on HPC clusters
and shared workstations — torch 2.11 fails to initialise CUDA and both
Chemeleon and MACE silently fall back to CPU. Every structure generation and
energy calculation then takes the slow path.

Until CUDA 13 drivers are the common case in our target communities, every
torch dep declaration in this repo must be capped at ``<2.11``. This test
walks every ``pyproject.toml`` in the repo (both ``dev/`` active source and
``pypi-v2/`` release snapshot, plus their MCP-server subprojects and the
legacy repo-root wrapper) and asserts the cap is present.

If you need to raise or remove the cap, update the cap expression in all
affected pyproject.toml files *together* so this test stays green, and make
sure the target driver floor is documented in the commit message.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Project root is parent of dev/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _discover_pyproject_files() -> list[Path]:
    """Return every pyproject.toml in the repo except those under vendored dirs.

    We deliberately include ``pypi-v2/`` — that's the release snapshot and
    ships to PyPI — and every MCP-server subproject. The only exclusions are
    build caches / editable install artefacts / reference repo clones kept
    alongside CrystaLyse.AI.
    """
    excluded = {".egg-info", "__pycache__", "build", "dist", ".mypy_cache"}
    results: list[Path] = []
    for path in PROJECT_ROOT.rglob("pyproject.toml"):
        if any(part in excluded or part.endswith(".egg-info") for part in path.parts):
            continue
        # Skip virtualenvs living inside the checkout. Without this the walk
        # picks up site-packages pyproject.toml files (pandas, etc.) and
        # asserts this project's pinning policy against third-party packages,
        # which is both noisy and a latent false failure.
        if any((path.parent.parent / marker).exists() for marker in ("pyvenv.cfg",)):
            continue
        if "site-packages" in path.parts:
            continue
        results.append(path)
    return sorted(results)


# Matches a torch declaration line inside a pyproject dependency list. Captures:
#   group 1: the version spec that follows the literal "torch" dep name (may be empty).
# Explicitly excludes "mace-torch", "torch-geometric", "torch-ema", "pytorch-*",
# etc., by requiring the preceding character to be a quote rather than a dash.
_TORCH_DEP_RE = re.compile(
    r"""
    (?:^|[\s,])                  # start of line or after whitespace/comma
    ["']                         # opening quote of the dep string
    torch                        # the literal name — must NOT be preceded by '-'
    (?P<spec>[^"']*)             # everything up to the closing quote = version spec
    ["']                         # closing quote
    """,
    re.VERBOSE | re.MULTILINE,
)


def _torch_dep_specs_in(path: Path) -> list[str]:
    """Return every top-level ``torch`` dep declaration found in ``path``.

    Filters out comment lines so we don't pick up tombstone comments that
    happen to quote the dep string.
    """
    specs: list[str] = []
    for raw_line in path.read_text().splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("#"):
            continue
        for match in _TORCH_DEP_RE.finditer(raw_line):
            # Guard against mace-torch / pytorch-lightning / torch-geometric etc.
            # where the capture would still technically match if we weren't careful:
            # _TORCH_DEP_RE requires the dep name to be exactly "torch" followed by
            # a version spec or quote, so "mace-torch" can't match — the preceding
            # 'e-' isn't in the character class. Still, belt-and-suspenders:
            # reject anything whose spec starts with "-" (e.g. "torch-geometric").
            spec = match.group("spec")
            if spec.startswith("-"):
                continue
            specs.append(spec)
    return specs


def test_torch_dep_discovery_finds_something() -> None:
    """Sanity: we expect at least the dev/pyproject.toml root-level torch dep.

    If this fails, either the regex is wrong or the dev pyproject has been
    restructured in a way the rest of this test can't reason about.
    """
    dev_py = PROJECT_ROOT / "dev" / "pyproject.toml"
    assert dev_py.exists(), f"dev/pyproject.toml not found at {dev_py}"
    specs = _torch_dep_specs_in(dev_py)
    assert specs, f"no torch dep parsed out of {dev_py} — regex or layout drifted"


@pytest.mark.parametrize("pyproject_path", _discover_pyproject_files(), ids=str)
def test_no_uncapped_torch_dep(pyproject_path: Path) -> None:
    """Every torch dep in every pyproject.toml must cap at ``<2.11``.

    Rationale: torch 2.11 bumped to CUDA 13 runtime, which breaks GPU on any
    driver that tops out at CUDA 12.x (still the common HPC / workstation
    case). See the module docstring.
    """
    specs = _torch_dep_specs_in(pyproject_path)
    if not specs:
        pytest.skip(f"no torch dep in {pyproject_path.relative_to(PROJECT_ROOT)}")

    for spec in specs:
        assert "<2.11" in spec or "<2.10" in spec or "==2.10" in spec or "==2.9" in spec, (
            f"{pyproject_path.relative_to(PROJECT_ROOT)} declares an uncapped torch dep "
            f'("torch{spec}"). torch >= 2.11 requires a CUDA 13 NVIDIA driver and '
            f"silently falls back to CPU on every CUDA 12.x driver we target. "
            f'Cap to "<2.11" or update this test if the cap is being deliberately '
            f"lifted."
        )
