"""
Regression tests for ``crystalyse.workspace`` packaging and agent-tool surface.

These exist to prevent two specific regressions:

1. **Issue #31** — a prior release of the PyPI package shipped without the
   ``crystalyse.workspace`` subpackage, because ``pypi-v2/MANIFEST.in``
   pruned it and ``workspace/`` lacked an ``__init__.py`` (so
   ``setuptools.find_packages`` silently dropped it). Users got
   ``ModuleNotFoundError: No module named 'crystalyse.workspace'`` on
   ``crystalyse --help``.

2. **Accidental removal of the agent-facing tool surface.** The agent
   registers exactly three ``@function_tool``s from this subpackage:
   ``read_file``, ``write_file``, ``list_files``. The clarification system
   also depends on ``ClarificationRequest`` / ``Question`` / ``QueryAnalysis``
   and on the mutable ``APPROVAL_CALLBACK`` / ``CLARIFICATION_CALLBACK``
   sentinels that the CLI hot-swaps at runtime. Any of these disappearing
   silently would break the agent at module load time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# =============================================================================
# Packaging regression — catches Issue #31
# =============================================================================


class TestWorkspacePackaging:
    """Ensure ``crystalyse.workspace`` is discoverable as a real package."""

    def test_workspace_has_init_py(self) -> None:
        """Without an __init__.py, setuptools.find_packages silently drops it."""
        import crystalyse.workspace

        init_path = Path(crystalyse.workspace.__file__)
        assert init_path.name == "__init__.py", (
            f"crystalyse.workspace must be a regular package with __init__.py, "
            f"got module file {init_path}"
        )
        assert init_path.exists()

    def test_find_packages_includes_workspace(self) -> None:
        """``setuptools.find_packages`` must include ``crystalyse.workspace``.

        This is the actual failure mode for issue #31: ``find_packages`` only
        picks up directories with an ``__init__.py``, so omitting it silently
        drops the subpackage from the built sdist/wheel.
        """
        from setuptools import find_packages

        # Resolve the dev/ root from this test file: tests/unit/ → tests/ → dev/
        dev_root = Path(__file__).resolve().parents[2]
        assert (dev_root / "pyproject.toml").exists(), (
            f"sanity: expected pyproject.toml under {dev_root}"
        )

        pkgs = find_packages(where=str(dev_root), include=["crystalyse*"])
        assert "crystalyse.workspace" in pkgs, (
            f"crystalyse.workspace missing from find_packages output: {sorted(pkgs)}. "
            "Probable cause: someone removed crystalyse/workspace/__init__.py."
        )


# =============================================================================
# Tool-surface regression — catches accidental deletion of live exports
# =============================================================================


class TestWorkspaceToolsSurface:
    """The agent imports these at module load time; losing any is a hard crash."""

    @pytest.fixture(scope="class")
    def workspace_tools(self):
        from crystalyse.workspace import workspace_tools

        return workspace_tools

    @pytest.mark.parametrize(
        "attr",
        [
            "read_file",
            "write_file",
            "list_files",
        ],
    )
    def test_agent_function_tools_present(self, workspace_tools, attr: str) -> None:
        """The three ``@function_tool``s the agent registers must exist.

        These are the symbols listed in
        ``crystalyse.agents.openai_agents_bridge.EnhancedCrystaLyseAgent.discover``
        at the ``Agent(tools=[...])`` call site.
        """
        assert hasattr(workspace_tools, attr), (
            f"workspace_tools.{attr} missing — this is a registered agent tool"
        )

    @pytest.mark.parametrize(
        "attr",
        [
            "ClarificationRequest",
            "Question",
            "QueryAnalysis",
        ],
    )
    def test_clarification_models_present(self, workspace_tools, attr: str) -> None:
        """These models are part of the workspace tools public API."""
        assert hasattr(workspace_tools, attr), (
            f"workspace_tools.{attr} missing"
        )

    @pytest.mark.parametrize(
        "attr",
        [
            "APPROVAL_CALLBACK",
            "CLARIFICATION_CALLBACK",
        ],
    )
    def test_runtime_callback_sentinels_present(self, workspace_tools, attr: str) -> None:
        """The CLI hot-swaps these at runtime to wire the Rich UI.

        See ``crystalyse.cli.discover`` where
        ``workspace_tools.APPROVAL_CALLBACK = approval_callback`` is assigned.
        """
        assert hasattr(workspace_tools, attr), (
            f"workspace_tools.{attr} missing — hot-swapped by the CLI at runtime"
        )

    def test_materials_workspace_reexport(self, workspace_tools) -> None:
        """``read_file`` / ``write_file`` / ``list_files`` all delegate to this."""
        assert hasattr(workspace_tools, "MaterialsWorkspace")

    def test_dead_functions_stay_removed(self, workspace_tools) -> None:
        """Two ``@function_tool``s were deleted as dead code.

        * ``request_user_clarification`` — the comment at
          ``openai_agents_bridge.py`` explicitly says it was removed from
          agent registration because queries are pre-processed by the
          adaptive clarification system.
        * ``extract_and_save_cif_from_structures`` — never registered with
          any agent and never imported from anywhere.

        If anyone re-adds them, that's a signal they may have missed why
        they were removed in the first place. Break the test loudly.
        """
        for gone in ("request_user_clarification", "extract_and_save_cif_from_structures"):
            assert not hasattr(workspace_tools, gone), (
                f"{gone} was deleted as dead code and must not be re-added without "
                "wiring it up to an agent; see crystalyse.agents.openai_agents_bridge"
            )

    def test_agent_bridge_imports_workspace(self) -> None:
        """The agent module must successfully import its workspace dependency.

        This is the integration-level repro of issue #31: on a broken
        packaging, this import fails with ModuleNotFoundError before the
        agent can even be constructed.
        """
        import crystalyse.agents.openai_agents_bridge as bridge

        # The module-level `from ..workspace import workspace_tools` must
        # have produced a real module object, not a stub.
        assert bridge.workspace_tools.__name__ == "crystalyse.workspace.workspace_tools"
