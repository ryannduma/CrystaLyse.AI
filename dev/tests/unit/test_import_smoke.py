"""
Smoke tests: top-level modules must be importable.

These are not coverage theatre — they exist because issue #31
(``ModuleNotFoundError: No module named 'crystalyse.workspace'``) manifested
as ``crystalyse --help`` failing to import the CLI module at startup, and the
test suite had no unit test that actually imported ``crystalyse.cli``. The
bug therefore survived CI and made it into a PyPI release.

Importing a module executes its top-level statements (imports, class
definitions, module-level constants), which is enough to catch:

- Missing subpackages dropped by setuptools packaging (the #31 failure mode).
- Broken absolute imports after a file move.
- Syntax errors introduced by auto-formatters or merge conflicts.
- Missing runtime dependencies declared in wrong extras group.

Each module gets its own test so a failure names the guilty party precisely.
"""

from __future__ import annotations

import importlib

import pytest

# Modules that are on the startup path for ``crystalyse <command>``. If any of
# these fail to import, the CLI is broken from the user's point of view.
TOP_LEVEL_STARTUP_MODULES = [
    # Entrypoint module registered in pyproject.toml [project.scripts].
    "crystalyse.cli",
    # Built and wired into the CLI's non-interactive discover flow.
    "crystalyse.agents.openai_agents_bridge",
    # Registered as the agent's read_file/write_file/list_files tools.
    "crystalyse.workspace.workspace_tools",
]


@pytest.mark.parametrize("module_name", TOP_LEVEL_STARTUP_MODULES)
def test_top_level_module_imports(module_name: str) -> None:
    """Importing must not raise — covers the entire CLI startup path."""
    importlib.import_module(module_name)


def test_cli_exposes_typer_app() -> None:
    """The Typer app registered as the ``crystalyse`` console script must
    actually be a ``typer.Typer`` instance. Guards against someone renaming
    or accidentally removing the CLI entrypoint referenced in pyproject.toml
    ``[project.scripts] crystalyse = "crystalyse.cli:main"``.
    """
    import typer

    from crystalyse import cli

    assert isinstance(cli.app, typer.Typer)
    assert callable(cli.main)


def test_mode_strenum_values() -> None:
    """``Mode`` is a StrEnum whose members behave as strings.

    Regression guard: StrEnum members render as their value, not as
    ``"Mode.EXPLORE"``. The mode rename (creative->explore, rigorous->validate,
    adaptive->auto) preserved this property.
    """
    from crystalyse.config.modes import Mode

    assert Mode.EXPLORE == "explore"
    assert Mode.VALIDATE == "validate"
    assert Mode.AUTO == "auto"
    # StrEnum members render as their value, not as "Mode.<name>".
    assert f"{Mode.EXPLORE}" == "explore"
    assert str(Mode.VALIDATE) == "validate"


def test_deleted_clarification_module_not_importable() -> None:
    """The clarification system was deleted in PR 1 Feature 1.4.

    This test verifies it stays deleted — if someone re-adds it without
    going through the proper planning process, this test will catch it.
    """
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("crystalyse.ui.enhanced_clarification")
