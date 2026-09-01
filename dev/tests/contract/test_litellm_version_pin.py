"""
Contract test: every pyproject.toml that declares a ``[litellm]`` optional-
dependency extra must pin ``litellm==1.83.0`` exactly.

Why this pin exists
-------------------

It is a transitive-dependency squeeze on the ``openai`` package, not a
provider-translation problem.

``openai-agents`` 0.21+ requires ``openai>=3.0.0``.  Meanwhile:

* litellm 1.84.0 and later cap ``openai<3.0.0``;
* litellm 1.83.1 through 1.83.14 pin ``openai`` to an exact 2.x version
  (``openai==2.30.0`` or ``==2.24.0``).

That leaves ``litellm==1.83.0`` as the only release whose ``openai``
requirement (``>=2.8.0``, no upper bound) can be satisfied alongside the
agents SDK.  The pin is exact because both neighbours are unsatisfiable, so
there is no range to express.

An earlier revision of this file claimed litellm above 1.82.6 breaks the SDK's
Anthropic message ordering.  That was not reproducible on 1.83.0: a live
Anthropic call through ``LitellmModel`` (Claude Opus 5) round-trips correctly.
The real constraint is the ``openai`` major version above.

Pyproject files that do NOT declare a ``[litellm]`` extra are skipped — not
every subproject needs LiteLLM (the MCP servers, for example, only need the
core ``crystalyse`` package).

How to update
-------------

1. Verify the new LiteLLM version still works with the SDK's ``LitellmModel``
   by running the smoke test at ``dev/tests/unit/config/test_models.py``.
2. Update the pin in every pyproject.toml that declares ``[litellm]``.
3. Update ``EXPECTED_PIN`` in this test.
4. Run ``python -m pytest dev/tests/contract/ -v`` to confirm green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Project root is parent of dev/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# The exact bounds every litellm dep MUST contain.
EXPECTED_PIN = "==1.83.0"


def _discover_pyproject_files() -> list[Path]:
    """Return every pyproject.toml in the repo, excluding build artefacts."""
    excluded = {".egg-info", "__pycache__", "build", "dist", ".mypy_cache"}
    results: list[Path] = []
    for path in PROJECT_ROOT.rglob("pyproject.toml"):
        if any(part in excluded or part.endswith(".egg-info") for part in path.parts):
            continue
        results.append(path)
    return sorted(results)


def _has_litellm_extra(text: str) -> bool:
    """Return True if the pyproject text declares a ``[litellm]`` extras group.

    Matches both ``[project.optional-dependencies]`` style and inline table
    forms.  The pattern looks for a line like ``litellm = [`` which is the
    standard way to declare an extras group in pyproject.toml.
    """
    return bool(re.search(r"^\s*litellm\s*=\s*\[", text, re.MULTILINE))


# Matches a litellm dependency declaration inside a quoted string.
_LITELLM_DEP_RE = re.compile(
    r"""
    ^\s*                         # leading whitespace (inside a TOML array)
    ["']                         # opening quote
    litellm                      # the literal package name
    (?P<spec>[^"']*)             # version specifier (may be empty)
    ["']                         # closing quote
    """,
    re.VERBOSE | re.MULTILINE,
)


def _litellm_dep_specs_in(path: Path) -> list[str]:
    """Return every litellm dep specifier found in ``path``.

    Only looks inside a ``litellm = [`` extras block to avoid matching
    comments or unrelated mentions of the word "litellm".
    """
    text = path.read_text()
    specs: list[str] = []

    in_litellm_extra = False

    for raw_line in text.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("#"):
            # Still track bracket depth in comments? No — skip entirely.
            if in_litellm_extra:
                continue
            continue

        # Detect entry into the litellm extras block
        if re.match(r"^\s*litellm\s*=\s*\[", raw_line):
            in_litellm_extra = True
            # The opening bracket is on this line; check for deps on same line
            for match in _LITELLM_DEP_RE.finditer(raw_line):
                specs.append(match.group("spec"))
            # Check if the array closes on the same line
            if "]" in raw_line.split("[", 1)[1]:
                in_litellm_extra = False
            continue

        if in_litellm_extra:
            for match in _LITELLM_DEP_RE.finditer(raw_line):
                specs.append(match.group("spec"))
            if "]" in raw_line:
                in_litellm_extra = False

    return specs


def test_litellm_dep_discovery_finds_something() -> None:
    """Sanity: dev/pyproject.toml must declare a [litellm] extra with a pin.

    If this fails, either the regex is wrong or the extras structure has
    been reorganised.
    """
    dev_py = PROJECT_ROOT / "dev" / "pyproject.toml"
    assert dev_py.exists(), f"dev/pyproject.toml not found at {dev_py}"
    specs = _litellm_dep_specs_in(dev_py)
    assert specs, (
        f"no litellm dep parsed from the [litellm] extra in {dev_py} — regex or layout drifted"
    )


@pytest.mark.parametrize("pyproject_path", _discover_pyproject_files(), ids=str)
def test_litellm_version_pin(pyproject_path: Path) -> None:
    """Every [litellm] extra must pin litellm to ``==1.83.0``.

    Rationale: it is the only litellm release whose ``openai`` requirement is
    satisfiable alongside openai-agents' ``openai>=3.0.0``.  See the module
    docstring.

    Pyprojects without a [litellm] extra are skipped — not every subproject
    needs LiteLLM.
    """
    text = pyproject_path.read_text()
    if not _has_litellm_extra(text):
        pytest.skip(f"no [litellm] extra in {pyproject_path.relative_to(PROJECT_ROOT)}")

    specs = _litellm_dep_specs_in(pyproject_path)
    assert specs, (
        f"{pyproject_path.relative_to(PROJECT_ROOT)} declares a [litellm] "
        f"extra but no litellm dependency was found inside it — "
        f"the extras block may be empty or the regex needs updating"
    )

    for spec in specs:
        assert EXPECTED_PIN in spec, (
            f"{pyproject_path.relative_to(PROJECT_ROOT)} declares "
            f'"litellm{spec}" but this project requires the exact pin '
            f'"litellm{EXPECTED_PIN}". litellm 1.84.0+ caps openai<3.0.0 and '
            f"1.83.1-1.83.14 pin openai==2.x exactly, both of which conflict "
            f"with openai-agents' openai>=3.0.0 requirement. "
            f"See the module docstring."
        )
