"""Test categorisation: what kind of test, when it runs, what it needs.

Three independent dimensions, so that neither the category nor the schedule has
to be restated on every test:

1. **Category** -- applied automatically from the directory a test lives in.
   ``tests/unit/`` is a unit test, ``tests/integration/`` an integration test,
   and so on.  Nothing to remember.

2. **Schedule** -- ``@pytest.mark.run_on("<stage>")``.  Stages nest:
   ``release > nightly > main > pr > local``.  Selecting a stage runs that
   stage *and everything below it*, so ``--ci-stage main`` runs the unit tests
   too.  Categories carry sensible defaults, so the marker is only needed to
   override one.

3. **Requirements** -- ``@pytest.mark.requires("openrouter")``.  A test that
   needs something not present is **skipped with a reason**, never failed.  A
   missing API key is not a regression.

The split that matters is by *dependency*, not by topic: a test belongs in
``integration/`` because it needs something outside this repository to be
alive, not because it is about a big subject.  A test that builds all its own
data belongs in ``unit/`` even if it lives next to slow ones.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Stages, cheapest first.  Index position *is* the ordering.
STAGES: tuple[str, ...] = ("local", "pr", "main", "nightly", "release")

#: Category -> the stage at which tests of that category first run.
#: Unit tests gate every PR; anything needing external systems waits for main;
#: numerical checks are slow enough to defer to the nightly run.
CATEGORY_DEFAULT_STAGE: dict[str, str] = {
    "unit": "pr",
    "contract": "pr",
    "integration": "main",
    "mcp_servers": "main",
    "e2e": "main",
    "regression": "main",
    "scientific_validation": "nightly",
}

#: Directory name -> category marker applied automatically.
DIRECTORY_CATEGORIES: dict[str, str] = {
    "unit": "unit",
    "contract": "contract",
    "integration": "integration",
    "mcp_servers": "mcp_servers",
    "e2e": "e2e",
    "scientific_validation": "scientific_validation",
    "regression": "regression",
}


def stage_includes(selected: str, required: str) -> bool:
    """Does running at *selected* also run something scheduled for *required*?"""
    return STAGES.index(selected) >= STAGES.index(required)


# ---------------------------------------------------------------------------
# Requirement probes
# ---------------------------------------------------------------------------
#
# Each returns (available, reason_if_not).  Probes must be cheap and must not
# make network calls -- checking for a key is fine, spending money to prove it
# works is not.


def _env_key(var: str, label: str):
    def probe() -> tuple[bool, str]:
        return bool(os.getenv(var)), f"{label} requires {var} to be set"

    return probe


def _chemeleon_checkpoints() -> tuple[bool, str]:
    from crystalyse.tools.chemeleon.checkpoint_manager import (
        CHECKPOINT_FILENAMES,
        DEFAULT_CACHE_DIR,
    )

    missing = [n for n in CHECKPOINT_FILENAMES.values() if not (DEFAULT_CACHE_DIR / n).is_file()]
    return not missing, f"Chemeleon checkpoints not cached in {DEFAULT_CACHE_DIR} ({missing})"


def _mace_model() -> tuple[bool, str]:
    cache = Path.home() / ".cache" / "mace"
    has = cache.is_dir() and any(cache.iterdir())
    return has, f"no MACE foundation model cached in {cache}"


def _phase_diagram() -> tuple[bool, str]:
    cache = Path.home() / ".cache" / "crystalyse"
    has = cache.is_dir() and any(cache.glob("ppd-*.pkl.gz"))
    return has, f"no phase-diagram data cached in {cache}"


def _gpu() -> tuple[bool, str]:
    try:
        import torch
    except ImportError:
        return False, "torch not installed"
    if torch.cuda.is_available():
        return True, ""
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return True, ""
    return False, "no CUDA or MPS device available"


def _ollama() -> tuple[bool, str]:
    import socket

    with socket.socket() as s:
        s.settimeout(0.25)
        try:
            s.connect(("127.0.0.1", 11434))
            return True, ""
        except OSError:
            return False, "no Ollama server listening on 127.0.0.1:11434"


def _git_lfs() -> tuple[bool, str]:
    return shutil.which("git-lfs") is not None, "git-lfs not installed"


REQUIREMENT_PROBES = {
    "openai": _env_key("OPENAI_API_KEY", "OpenAI"),
    "anthropic": _env_key("ANTHROPIC_API_KEY", "Anthropic"),
    "openrouter": _env_key("OPENROUTER_API_KEY", "OpenRouter"),
    "mistral": _env_key("MISTRAL_API_KEY", "Mistral"),
    "chemeleon_checkpoints": _chemeleon_checkpoints,
    "mace_model": _mace_model,
    "phase_diagram": _phase_diagram,
    "gpu": _gpu,
    "ollama": _ollama,
    "git_lfs": _git_lfs,
}


def missing_requirements(names) -> list[str]:
    """Return a reason string for each named requirement that is unavailable."""
    reasons = []
    for name in names:
        probe = REQUIREMENT_PROBES.get(name)
        if probe is None:
            reasons.append(f"unknown requirement {name!r}; valid: {sorted(REQUIREMENT_PROBES)}")
            continue
        try:
            ok, why = probe()
        except Exception as e:  # a broken probe must skip, never error the run
            ok, why = False, f"requirement probe {name!r} failed: {e}"
        if not ok:
            reasons.append(why)
    return reasons
