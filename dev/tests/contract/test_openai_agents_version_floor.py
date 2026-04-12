"""
Contract test: every pyproject.toml that declares ``openai-agents`` as a
dependency must pin it to ``>=0.13.6,<0.14``.

Why this pin exists
-------------------

openai-agents 0.13.6 is the first release that ships ``LitellmModel``,
``MultiProvider`` prefix routing, and ``Agent(output_type=...)``.  These three
APIs are load-bearing for CrystaLyse's multi-provider model resolver and
structured output pipeline.  Versions before 0.13.6 lack these APIs entirely
and will crash at import time.

The ``<0.14`` ceiling keeps us within the tested API surface.  The SDK has made
breaking changes between minor versions before (e.g. the ``AnyLLMModel``
rename between 0.12 and 0.13).  If 0.14 ships and we validate it, update the
pin expression in **all** affected pyproject.toml files together and update
this test to match.

How to update
-------------

1. Verify the new version still exports ``LitellmModel``, ``MultiProvider``,
   and ``Agent.__init__(output_type=...)``.
2. Update the pin in every pyproject.toml (dev/, pypi-v2/, repo root).
3. Update ``EXPECTED_SPEC`` in this test.
4. Run ``python -m pytest dev/tests/contract/ -v`` to confirm green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Project root is parent of dev/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# The exact version specifier every openai-agents dep MUST contain.
# Both the floor and the ceiling must be present.
EXPECTED_FLOOR = ">=0.13.6"
EXPECTED_CEILING = "<0.14"


def _discover_pyproject_files() -> list[Path]:
    """Return every pyproject.toml in the repo, excluding build artefacts."""
    excluded = {".egg-info", "__pycache__", "build", "dist", ".mypy_cache"}
    results: list[Path] = []
    for path in PROJECT_ROOT.rglob("pyproject.toml"):
        if any(part in excluded or part.endswith(".egg-info") for part in path.parts):
            continue
        results.append(path)
    return sorted(results)


# Matches an openai-agents dependency declaration inside a quoted string in a
# TOML dependency list.  Captures the version specifier that follows the name.
# Excludes lines that are clearly in a [project.keywords] or similar non-dep
# context by requiring the line to start with optional whitespace then a quote
# (dependency lists are indented string arrays, keywords don't have version
# specs anyway).
_OPENAI_AGENTS_DEP_RE = re.compile(
    r"""
    ^\s*                         # leading whitespace (inside a TOML array)
    ["']                         # opening quote
    openai-agents                # the literal package name
    (?P<spec>[^"']*)             # version specifier (may be empty)
    ["']                         # closing quote
    """,
    re.VERBOSE | re.MULTILINE,
)


def _openai_agents_dep_specs_in(path: Path) -> list[str]:
    """Return every openai-agents dep specifier found in ``path``.

    Skips comment lines and keyword-only mentions (bare name without version
    spec inside a ``keywords`` array).
    """
    text = path.read_text()
    specs: list[str] = []

    # Track whether we're inside a keywords section to skip those
    in_keywords = False
    for raw_line in text.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("#"):
            continue
        # Detect TOML section/key transitions
        if re.match(r"^keywords\s*=", stripped):
            in_keywords = True
            continue
        # A new key assignment or section header exits keywords context
        if in_keywords and (re.match(r"^\w", stripped) or stripped.startswith("[")):
            in_keywords = False
        if in_keywords:
            continue

        for match in _OPENAI_AGENTS_DEP_RE.finditer(raw_line):
            spec = match.group("spec")
            specs.append(spec)
    return specs


def test_openai_agents_dep_discovery_finds_something() -> None:
    """Sanity: we expect at least dev/pyproject.toml to declare openai-agents.

    If this fails, either the regex is wrong or the pyproject has been
    restructured in a way this test can't reason about.
    """
    dev_py = PROJECT_ROOT / "dev" / "pyproject.toml"
    assert dev_py.exists(), f"dev/pyproject.toml not found at {dev_py}"
    specs = _openai_agents_dep_specs_in(dev_py)
    assert specs, f"no openai-agents dep parsed from {dev_py} — regex or layout drifted"


@pytest.mark.parametrize("pyproject_path", _discover_pyproject_files(), ids=str)
def test_openai_agents_version_pin(pyproject_path: Path) -> None:
    """Every openai-agents dep must be pinned to ``>=0.13.6,<0.14``.

    Rationale: versions before 0.13.6 lack LitellmModel, MultiProvider, and
    Agent(output_type=...) which are required for the multi-provider model
    resolver.  The <0.14 ceiling guards against breaking API changes between
    minor versions.  See the module docstring for full context.
    """
    specs = _openai_agents_dep_specs_in(pyproject_path)
    if not specs:
        pytest.skip(f"no openai-agents dep in {pyproject_path.relative_to(PROJECT_ROOT)}")

    for spec in specs:
        assert EXPECTED_FLOOR in spec, (
            f"{pyproject_path.relative_to(PROJECT_ROOT)} declares "
            f'"openai-agents{spec}" which is missing the floor pin '
            f'"{EXPECTED_FLOOR}". openai-agents < 0.13.6 lacks LitellmModel, '
            f"MultiProvider, and Agent(output_type=...). "
            f'Pin to "{EXPECTED_FLOOR},{EXPECTED_CEILING}".'
        )
        assert EXPECTED_CEILING in spec, (
            f"{pyproject_path.relative_to(PROJECT_ROOT)} declares "
            f'"openai-agents{spec}" which is missing the ceiling pin '
            f'"{EXPECTED_CEILING}". The SDK has made breaking changes between '
            f"minor versions before. "
            f'Pin to "{EXPECTED_FLOOR},{EXPECTED_CEILING}".'
        )
