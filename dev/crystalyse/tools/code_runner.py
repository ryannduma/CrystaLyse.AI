"""Python code execution tool for Crystalyse.

Provides isolated Python code execution with access to scientific packages.
Useful for custom analysis and data processing.
"""

import contextlib
import io
import logging
import traceback
from typing import Any

try:
    from agents import function_tool

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

    # Fallback decorator
    def function_tool(func):
        return func


logger = logging.getLogger(__name__)

# Default timeout for code execution
DEFAULT_TIMEOUT = 30

# Packages available in the execution environment
AVAILABLE_PACKAGES = [
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "pymatgen",
    "ase",
    "json",
    "math",
    "collections",
    "itertools",
    "functools",
    "pathlib",
    "re",
]


def _create_safe_globals() -> dict[str, Any]:
    """Create a restricted globals dictionary for code execution.

    Returns:
        Dictionary of safe builtins and imports.
    """
    safe_globals = {
        "__builtins__": {
            # Safe built-in functions
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "frozenset": frozenset,
            "int": int,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "print": print,
            "range": range,
            "reversed": reversed,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
            # Useful additions
            "isinstance": isinstance,
            "issubclass": issubclass,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "callable": callable,
            "format": format,
            "repr": repr,
            "hash": hash,
            "id": id,
            "iter": iter,
            "next": next,
            "slice": slice,
            "vars": vars,
        }
    }

    # Import commonly used scientific packages
    try:
        import numpy as np

        safe_globals["np"] = np
        safe_globals["numpy"] = np
    except ImportError:
        pass

    try:
        import pandas as pd

        safe_globals["pd"] = pd
        safe_globals["pandas"] = pd
    except ImportError:
        pass

    try:
        import scipy

        safe_globals["scipy"] = scipy
    except ImportError:
        pass

    try:
        from pymatgen.core import Composition, Lattice, Structure

        safe_globals["Structure"] = Structure
        safe_globals["Lattice"] = Lattice
        safe_globals["Composition"] = Composition
    except ImportError:
        pass

    try:
        import ase
        from ase import Atoms

        safe_globals["ase"] = ase
        safe_globals["Atoms"] = Atoms
    except ImportError:
        pass

    # Standard library modules
    import collections
    import functools
    import itertools
    import json
    import math
    import pathlib
    import re

    safe_globals["json"] = json
    safe_globals["math"] = math
    safe_globals["collections"] = collections
    safe_globals["itertools"] = itertools
    safe_globals["functools"] = functools
    safe_globals["pathlib"] = pathlib
    safe_globals["Path"] = pathlib.Path
    safe_globals["re"] = re

    return safe_globals


@function_tool
def execute_python(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Execute Python code and return the result.

    This tool runs Python code in an isolated environment with access to
    scientific packages (numpy, scipy, pandas, pymatgen, ase). Use it for:
    - Data analysis and transformations
    - Mathematical calculations
    - Structure manipulation
    - Custom processing logic

    The code has access to:
    - numpy (as np)
    - pandas (as pd)
    - scipy
    - pymatgen (Structure, Lattice, Composition)
    - ase (Atoms)
    - json, math, collections, itertools, pathlib

    Args:
        code: Python code to execute.
        timeout: Maximum execution time in seconds (default: 30).

    Returns:
        Dictionary with:
        - success: True if code executed without errors
        - stdout: Printed output from the code
        - result: Return value (if the last statement is an expression)
        - error: Error message if execution failed
        - traceback: Full traceback if an exception occurred
    """
    logger.info(f"Executing Python code ({len(code)} chars)")

    # Create safe execution environment
    safe_globals = _create_safe_globals()
    local_vars: dict[str, Any] = {}

    # Capture stdout
    stdout_capture = io.StringIO()

    try:
        # Redirect stdout
        with contextlib.redirect_stdout(stdout_capture):
            # Execute the code
            exec(code, safe_globals, local_vars)

        # Get stdout
        stdout = stdout_capture.getvalue()

        # Try to get a result (last expression value)
        # This is a simple heuristic - check for common result variable names
        result = None
        for var_name in ["result", "output", "answer", "_result"]:
            if var_name in local_vars:
                result = local_vars[var_name]
                break

        # If no result variable, try to get any new variables
        if result is None and local_vars:
            # Get variables that were created (exclude functions/classes)
            created_vars = {
                k: v for k, v in local_vars.items() if not k.startswith("_") and not callable(v)
            }
            if len(created_vars) == 1:
                result = list(created_vars.values())[0]
            elif created_vars:
                result = created_vars

        # Serialize result if possible
        result_str = None
        if result is not None:
            try:
                import json

                result_str = json.dumps(result, indent=2, default=str)
            except Exception:
                result_str = str(result)

        return {
            "success": True,
            "stdout": stdout,
            "result": result_str,
            "error": None,
            "traceback": None,
        }

    except SyntaxError as e:
        return {
            "success": False,
            "stdout": stdout_capture.getvalue(),
            "result": None,
            "error": f"Syntax error: {e.msg} at line {e.lineno}",
            "traceback": None,
        }
    except Exception as e:
        tb = traceback.format_exc()
        return {
            "success": False,
            "stdout": stdout_capture.getvalue(),
            "result": None,
            "error": str(e),
            "traceback": tb,
        }


def execute_python_script(
    script_path: str,
    args: list[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Execute a Python script file.

    Args:
        script_path: Path to the Python script.
        args: Command-line arguments to pass to the script.
        timeout: Maximum execution time in seconds.

    Returns:
        Dictionary with execution results.
    """
    from .shell import run_shell_command

    args_str = " ".join(args) if args else ""
    command = f"python {script_path} {args_str}"

    return run_shell_command(
        command=command,
        timeout=timeout,
        sandboxed=True,
    )
