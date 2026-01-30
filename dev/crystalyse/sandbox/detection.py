"""Sandbox denial detection heuristics.

Detects when command failures are likely caused by sandbox restrictions.
Based on Codex's denial detection patterns.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Exit code base for signals (128 + signal number on Unix)
EXIT_CODE_SIGNAL_BASE = 128

# SIGSYS is raised when seccomp blocks a syscall
SIGSYS_CODE = getattr(signal, "SIGSYS", 31)  # Default to 31 on Linux

# Keywords indicating sandbox denial
SANDBOX_DENIED_KEYWORDS: tuple[str, ...] = (
    "operation not permitted",
    "permission denied",
    "read-only file system",
    "seccomp",
    "sandbox",
    "landlock",
    "failed to write file",
    "cannot create",
    "access denied",
    "not allowed",
)


@dataclass
class CommandOutput:
    """Output from a command execution.

    Attributes:
        stdout: Standard output text.
        stderr: Standard error text.
        exit_code: Process exit code.
    """

    stdout: str
    stderr: str
    exit_code: int


def is_sandbox_denied(
    sandbox_type: str,
    output: CommandOutput,
) -> bool:
    """Check if a command failure was likely caused by sandbox restrictions.

    Uses heuristics including:
    - Exit code analysis (SIGSYS for seccomp violations)
    - Keyword detection in stdout/stderr

    Args:
        sandbox_type: Type of sandbox ("none", "macos-seatbelt", "linux-landlock").
        output: The command output to analyse.

    Returns:
        True if the failure appears to be sandbox-related.
    """
    # Success or no sandbox - not a denial
    if sandbox_type == "none" or output.exit_code == 0:
        return False

    # Check for sandbox-specific keywords in output
    combined = (output.stdout + " " + output.stderr).lower()
    has_keyword = any(keyword in combined for keyword in SANDBOX_DENIED_KEYWORDS)

    if has_keyword:
        return True

    # Check for SIGSYS on Linux (seccomp violation)
    if sandbox_type == "linux-landlock":
        sigsys_exit = EXIT_CODE_SIGNAL_BASE + SIGSYS_CODE
        if output.exit_code == sigsys_exit:
            return True

    return False


def get_denial_reason(output: CommandOutput) -> str | None:
    """Extract a human-readable denial reason from command output.

    Args:
        output: The command output to analyse.

    Returns:
        A description of why access was denied, or None if unclear.
    """
    combined = (output.stdout + " " + output.stderr).lower()

    # Check each keyword and return a relevant message
    if "permission denied" in combined:
        return "Permission denied - path may be outside sandbox"

    if "read-only file system" in combined:
        return "Read-only file system - write access not allowed"

    if "operation not permitted" in combined:
        return "Operation not permitted - may violate sandbox policy"

    if "seccomp" in combined:
        return "Syscall blocked by seccomp filter"

    if "landlock" in combined:
        return "Filesystem access blocked by Landlock"

    if "sandbox" in combined:
        return "Action blocked by sandbox policy"

    return None
