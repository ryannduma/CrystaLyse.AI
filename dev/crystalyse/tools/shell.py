"""Shell execution tool for Crystalyse.

Provides safe bash command execution with sandboxing capabilities.
Based on OpenAI SDK's LocalShellTool pattern but with materials science context.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
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

# Default timeout for shell commands
DEFAULT_TIMEOUT = 60

# Allowed commands for sandboxed mode
ALLOWED_COMMANDS = {
    # General utilities
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "sort",
    "uniq",
    "echo",
    "pwd",
    "date",
    "env",
    # Python tools
    "python",
    "python3",
    "pip",
    "pip3",
    "conda",
    # Materials science tools
    "ase",
    "cif2cell",
    "phonopy",
    # File operations (safe subset)
    "cp",
    "mv",
    "mkdir",
    "rm",
    "touch",
    # Git operations
    "git",
}

# Blocked commands
BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777",
    "chmod -R 777",
    "curl | bash",
    "wget | bash",
    "dd if=",
    "mkfs.",
}


def _is_command_safe(command: str, sandboxed: bool = True) -> tuple[bool, str]:
    """Check if a command is safe to execute.

    Args:
        command: The command to check.
        sandboxed: If True, only allow explicitly allowed commands.

    Returns:
        Tuple of (is_safe, reason).
    """
    # Check for obviously dangerous patterns
    for blocked in BLOCKED_COMMANDS:
        if blocked in command:
            return False, f"Command contains blocked pattern: {blocked}"

    if sandboxed:
        # Extract base command (first word)
        base_cmd = command.strip().split()[0] if command.strip() else ""
        # Handle sudo
        if base_cmd == "sudo":
            return False, "sudo is not allowed in sandboxed mode"

        # Check if base command is allowed
        if base_cmd not in ALLOWED_COMMANDS:
            return False, f"Command '{base_cmd}' is not in the allowed list for sandboxed mode"

    return True, ""


@function_tool
def run_shell_command(
    command: str,
    working_directory: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    sandboxed: bool = True,
) -> dict:
    """Execute a shell command and return the result.

    This tool runs bash commands with safety restrictions. Use it for:
    - Running Python scripts
    - File system operations (ls, cat, cp, etc.)
    - Git operations
    - Package installation (pip, conda)
    - Materials science CLI tools (ase, phonopy, etc.)

    Args:
        command: The bash command to execute.
        working_directory: Directory to run the command in (default: current).
        timeout: Maximum execution time in seconds (default: 60).
        sandboxed: If True, only allow safe commands (default: True).

    Returns:
        Dictionary with:
        - success: True if command completed successfully
        - stdout: Standard output from the command
        - stderr: Standard error from the command
        - return_code: Exit code of the command
        - error: Error message if something went wrong
    """
    # Validate command safety
    is_safe, reason = _is_command_safe(command, sandboxed)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": f"Command blocked: {reason}",
        }

    # Resolve working directory (handle empty string from SDK)
    cwd = Path(working_directory) if working_directory and working_directory.strip() else Path.cwd()
    if not cwd.exists():
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": f"Working directory does not exist: {cwd}",
        }

    try:
        logger.info(f"Executing shell command: {command[:100]}...")

        # Run the command
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )

        stdout = result.stdout
        stderr = result.stderr

        # Truncate very long outputs
        max_output = 50000
        if len(stdout) > max_output:
            stdout = stdout[:max_output] + f"\n... [truncated, {len(result.stdout)} total chars]"
        if len(stderr) > max_output:
            stderr = stderr[:max_output] + f"\n... [truncated, {len(result.stderr)} total chars]"

        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": result.returncode,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": f"Command timed out after {timeout} seconds",
        }
    except Exception as e:
        logger.error(f"Shell command failed: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": str(e),
        }


async def run_shell_command_async(
    command: str,
    working_directory: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    sandboxed: bool = True,
) -> dict[str, Any]:
    """Async version of run_shell_command.

    Uses asyncio subprocess for non-blocking execution.
    """
    # Validate command safety
    is_safe, reason = _is_command_safe(command, sandboxed)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": f"Command blocked: {reason}",
        }

    # Resolve working directory
    cwd = Path(working_directory) if working_directory else Path.cwd()
    if not cwd.exists():
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": f"Working directory does not exist: {cwd}",
        }

    try:
        logger.info(f"Executing async shell command: {command[:100]}...")

        # Create subprocess
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )

        # Wait for completion with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "error": f"Command timed out after {timeout} seconds",
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Truncate very long outputs
        max_output = 50000
        if len(stdout) > max_output:
            stdout = stdout[:max_output] + f"\n... [truncated, {len(stdout_bytes)} total chars]"
        if len(stderr) > max_output:
            stderr = stderr[:max_output] + f"\n... [truncated, {len(stderr_bytes)} total chars]"

        return {
            "success": proc.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": proc.returncode,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Async shell command failed: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": str(e),
        }
