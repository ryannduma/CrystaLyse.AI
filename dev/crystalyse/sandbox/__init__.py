"""Sandbox package for secure command execution.

Provides platform-specific sandboxing backends:
- macOS: Seatbelt (sandbox-exec)
- Linux: Landlock + seccomp
- Fallback: No sandbox (with warning)

Based on Codex patterns for declarative sandbox policies.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .detection import CommandOutput, get_denial_reason, is_sandbox_denied
from .policy import SandboxLevel, SandboxPolicy, WritableRoot

if TYPE_CHECKING:
    pass

__all__ = [
    # Policy
    "SandboxLevel",
    "SandboxPolicy",
    "WritableRoot",
    # Backend
    "SandboxBackend",
    "SandboxResult",
    "get_backend",
    # Detection
    "CommandOutput",
    "is_sandbox_denied",
    "get_denial_reason",
]


@dataclass
class SandboxResult:
    """Result from sandboxed command execution.

    Attributes:
        stdout: Standard output.
        stderr: Standard error.
        exit_code: Process exit code.
        sandbox_type: Type of sandbox used.
        sandbox_denied: True if failure was due to sandbox.
        denial_reason: Human-readable reason if sandbox_denied.
    """

    stdout: str
    stderr: str
    exit_code: int
    sandbox_type: str
    sandbox_denied: bool = False
    denial_reason: str | None = None

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.exit_code == 0


class SandboxBackend(ABC):
    """Abstract base class for sandbox backends.

    Implementations provide platform-specific sandboxing.
    """

    @property
    @abstractmethod
    def sandbox_type(self) -> str:
        """Return the sandbox type identifier."""
        ...

    @abstractmethod
    async def execute(
        self,
        command: list[str],
        *,
        cwd: Path,
        policy: SandboxPolicy,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute a command under sandbox restrictions.

        Args:
            command: Command and arguments to execute.
            cwd: Working directory for the command.
            policy: Sandbox policy to apply.
            timeout: Optional timeout in seconds.
            env: Optional environment variables (merged with current).

        Returns:
            SandboxResult with output and status.
        """
        ...

    def transform_command(
        self,
        command: list[str],
        policy: SandboxPolicy,
        cwd: Path,
    ) -> list[str]:
        """Transform command to run under sandbox.

        Default implementation returns command unchanged.
        Platform backends override to wrap with sandbox executable.

        Args:
            command: Original command and arguments.
            policy: Sandbox policy to apply.
            cwd: Working directory for policy computation.

        Returns:
            Transformed command (may include sandbox wrapper).
        """
        return command


class NoSandboxBackend(SandboxBackend):
    """Fallback backend with no sandboxing.

    Used when no platform-specific sandbox is available.
    Logs a warning on first use.
    """

    _warned: bool = False

    @property
    def sandbox_type(self) -> str:
        return "none"

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Path,
        policy: SandboxPolicy,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute command without sandboxing."""
        import asyncio
        import os

        if not NoSandboxBackend._warned:
            import logging

            logging.getLogger(__name__).warning(
                "No sandbox backend available - commands run unrestricted"
            )
            NoSandboxBackend._warned = True

        # Prepare environment
        run_env = dict(os.environ)
        if env:
            run_env.update(env)

        # Mark as unsandboxed
        run_env["CRYSTALYSE_SANDBOX"] = "none"

        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                env=run_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    stdout="",
                    stderr=f"Command timed out after {timeout}s",
                    exit_code=-1,
                    sandbox_type="none",
                )

            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=proc.returncode or 0,
                sandbox_type="none",
            )

        except FileNotFoundError:
            return SandboxResult(
                stdout="",
                stderr=f"Command not found: {command[0]}",
                exit_code=127,
                sandbox_type="none",
            )
        except PermissionError:
            return SandboxResult(
                stdout="",
                stderr=f"Permission denied: {command[0]}",
                exit_code=126,
                sandbox_type="none",
            )


def get_backend() -> SandboxBackend:
    """Get the appropriate sandbox backend for the current platform.

    Returns:
        SandboxBackend implementation:
        - macOS: SeatbeltBackend
        - Linux: LandlockBackend
        - Other: NoSandboxBackend (with warning)
    """
    if sys.platform == "darwin":
        from .seatbelt import SeatbeltBackend

        return SeatbeltBackend()

    if sys.platform == "linux":
        from .landlock import LandlockBackend

        return LandlockBackend()

    # Fallback - no sandbox
    return NoSandboxBackend()
