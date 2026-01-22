"""Skill Script Executor for Crystalyse.

This module provides execution of skill scripts via subprocess.
Skills can have a `scripts/` directory with Python scripts that perform
specific tasks (validation, prediction, analysis, etc.).
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from agents import function_tool

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

    def function_tool(func):
        return func


logger = logging.getLogger(__name__)

# Default timeout for skill scripts
DEFAULT_SCRIPT_TIMEOUT = 300  # 5 minutes


def _find_skills_directory() -> Path | None:
    """Find the skills directory."""
    possible_paths = [
        Path(__file__).parent.parent.parent / "skills",  # dev/skills/
        Path(__file__).parent.parent / "skills",  # crystalyse/skills/
        Path.cwd() / "skills",
        Path.cwd() / "dev" / "skills",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def _find_skill_script(skill_name: str, script_name: str) -> Path | None:
    """Find a specific script within a skill.

    Args:
        skill_name: Name of the skill directory
        script_name: Name of the script file (with or without .py)

    Returns:
        Path to the script or None if not found
    """
    skills_dir = _find_skills_directory()
    if not skills_dir:
        return None

    skill_dir = skills_dir / skill_name
    if not skill_dir.exists():
        return None

    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return None

    # Add .py extension if not present
    if not script_name.endswith(".py"):
        script_name = f"{script_name}.py"

    script_path = scripts_dir / script_name
    if script_path.exists():
        return script_path

    return None


def list_skill_scripts(skill_name: str) -> list[str]:
    """List all available scripts for a skill.

    Args:
        skill_name: Name of the skill

    Returns:
        List of script names (without .py extension)
    """
    skills_dir = _find_skills_directory()
    if not skills_dir:
        return []

    skill_dir = skills_dir / skill_name
    scripts_dir = skill_dir / "scripts"

    if not scripts_dir.exists():
        return []

    return [p.stem for p in scripts_dir.glob("*.py") if not p.name.startswith("_")]


def get_available_skills() -> dict[str, list[str]]:
    """Get all available skills and their scripts.

    Returns:
        Dictionary mapping skill names to their scripts.
    """
    skills_dir = _find_skills_directory()
    if not skills_dir:
        return {}

    result = {}
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("."):
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue

        scripts = list_skill_scripts(skill_dir.name)
        if scripts:
            result[skill_dir.name] = scripts

    return result


@function_tool
def execute_skill_script(
    skill_name: str,
    script_name: str,
    args: str = "{}",
    timeout: int = DEFAULT_SCRIPT_TIMEOUT,
) -> dict:
    """Execute a skill's script and return the result.

    Skills are organized in the `skills/` directory, each containing:
    - SKILL.md: Instructions and documentation
    - scripts/: Executable Python scripts

    This tool runs a script from a skill's scripts directory, passing
    arguments as JSON via stdin.

    Available skills and scripts can be found in:
    - smact-validation: validate.py, validate_batch.py
    - chemeleon-prediction: predict_csp.py, predict_dng.py
    - mace-calculation: formation_energy.py, relax.py
    - pymatgen-analysis: analyze_structure.py, hull_distance.py

    Args:
        skill_name: Name of the skill (directory name).
        script_name: Name of the script to run (without .py).
        args: Arguments to pass to the script as JSON.
        timeout: Maximum execution time in seconds (default: 300).

    Returns:
        Dictionary with:
        - success: True if script executed successfully
        - result: Parsed JSON output from the script
        - stdout: Raw stdout if not JSON
        - stderr: Standard error output
        - error: Error message if execution failed

    Example:
        execute_skill_script(
            skill_name="smact-validation",
            script_name="validate",
            args='{"formula": "LiFePO4"}'
        )
    """
    # Parse args from JSON string
    try:
        args_dict = json.loads(args) if args else {}
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "result": None,
            "stdout": "",
            "stderr": "",
            "error": f"Invalid args JSON: {e}",
        }

    # Find the script
    script_path = _find_skill_script(skill_name, script_name)

    if script_path is None:
        # Provide helpful error message
        skills_dir = _find_skills_directory()
        available = get_available_skills()

        error_msg = f"Script '{script_name}' not found in skill '{skill_name}'."
        if skill_name in available:
            error_msg += f" Available scripts: {available[skill_name]}"
        elif available:
            error_msg += f" Available skills: {list(available.keys())}"
        else:
            error_msg += f" Skills directory: {skills_dir}"

        return {
            "success": False,
            "result": None,
            "stdout": "",
            "stderr": "",
            "error": error_msg,
        }

    # Prepare input
    input_json = json.dumps(args_dict)

    try:
        logger.info(f"Executing skill script: {skill_name}/{script_name}")

        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
            cwd=str(script_path.parent),
        )

        stdout = result.stdout
        stderr = result.stderr

        # Try to parse stdout as JSON
        parsed_result = None
        try:
            if stdout.strip():
                parsed_result = json.loads(stdout)
        except json.JSONDecodeError:
            # Not JSON, keep as raw stdout
            pass

        success = result.returncode == 0

        return {
            "success": success,
            "result": parsed_result,
            "stdout": stdout if parsed_result is None else "",
            "stderr": stderr,
            "return_code": result.returncode,
            "error": None if success else f"Script exited with code {result.returncode}",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "result": None,
            "stdout": "",
            "stderr": "",
            "error": f"Script timed out after {timeout} seconds",
        }
    except Exception as e:
        logger.error(f"Skill script execution failed: {e}")
        return {
            "success": False,
            "result": None,
            "stdout": "",
            "stderr": "",
            "error": str(e),
        }


async def execute_skill_script_async(
    skill_name: str,
    script_name: str,
    args: dict[str, Any] | None = None,
    timeout: int = DEFAULT_SCRIPT_TIMEOUT,
) -> dict[str, Any]:
    """Async version of execute_skill_script.

    Uses asyncio subprocess for non-blocking execution.
    """
    import asyncio

    # Find the script
    script_path = _find_skill_script(skill_name, script_name)

    if script_path is None:
        available = get_available_skills()
        error_msg = f"Script '{script_name}' not found in skill '{skill_name}'."
        if skill_name in available:
            error_msg += f" Available scripts: {available[skill_name]}"

        return {
            "success": False,
            "result": None,
            "stdout": "",
            "stderr": "",
            "error": error_msg,
        }

    # Prepare input
    input_json = json.dumps(args or {})

    try:
        logger.info(f"Executing skill script (async): {skill_name}/{script_name}")

        # Create subprocess
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent),
            env=os.environ.copy(),
        )

        # Wait for completion with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=input_json.encode()),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "success": False,
                "result": None,
                "stdout": "",
                "stderr": "",
                "error": f"Script timed out after {timeout} seconds",
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Try to parse stdout as JSON
        parsed_result = None
        try:
            if stdout.strip():
                parsed_result = json.loads(stdout)
        except json.JSONDecodeError:
            pass

        success = proc.returncode == 0

        return {
            "success": success,
            "result": parsed_result,
            "stdout": stdout if parsed_result is None else "",
            "stderr": stderr,
            "return_code": proc.returncode,
            "error": None if success else f"Script exited with code {proc.returncode}",
        }

    except Exception as e:
        logger.error(f"Async skill script execution failed: {e}")
        return {
            "success": False,
            "result": None,
            "stdout": "",
            "stderr": "",
            "error": str(e),
        }
