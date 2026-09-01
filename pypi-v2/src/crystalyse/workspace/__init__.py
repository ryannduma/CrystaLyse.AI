"""Per-project filesystem tools registered with the Crystalyse agent.

The agent registers ``read_file``, ``write_file`` and ``list_files`` from
``workspace_tools`` as OpenAI Agents SDK function tools (see
``crystalyse.agents.agents_bridge``). These are backed by
``MaterialsWorkspace``, a sandboxed per-project directory helper with a
path-traversal guard.

This file exists primarily so ``setuptools.find_packages`` picks this
directory up. Without an ``__init__.py`` the subpackage silently disappears
from the built sdist and wheel — that is the root cause of issue #31
("ModuleNotFoundError: No module named 'crystalyse.workspace'" on
``pip install crystalyse``).
"""
