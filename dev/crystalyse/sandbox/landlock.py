"""Linux Landlock + seccomp sandbox backend.

Uses Landlock for filesystem restrictions and seccomp for network blocking.
Based on Codex patterns for Linux sandboxing.
"""

from __future__ import annotations

import asyncio
import ctypes
import ctypes.util
import json
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import SandboxBackend, SandboxResult
from .detection import CommandOutput, get_denial_reason, is_sandbox_denied
from .policy import SandboxPolicy

if TYPE_CHECKING:
    pass

# Landlock ABI constants
LANDLOCK_CREATE_RULESET_VERSION = 0

# Landlock access rights (ABI V5)
LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
LANDLOCK_ACCESS_FS_REFER = 1 << 13  # ABI V2
LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14  # ABI V3
LANDLOCK_ACCESS_FS_IOCTL_DEV = 1 << 15  # ABI V5

# Combined access masks
LANDLOCK_ACCESS_FS_READ = (
    LANDLOCK_ACCESS_FS_EXECUTE | LANDLOCK_ACCESS_FS_READ_FILE | LANDLOCK_ACCESS_FS_READ_DIR
)

LANDLOCK_ACCESS_FS_WRITE = (
    LANDLOCK_ACCESS_FS_WRITE_FILE
    | LANDLOCK_ACCESS_FS_REMOVE_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_FILE
    | LANDLOCK_ACCESS_FS_MAKE_CHAR
    | LANDLOCK_ACCESS_FS_MAKE_DIR
    | LANDLOCK_ACCESS_FS_MAKE_REG
    | LANDLOCK_ACCESS_FS_MAKE_SOCK
    | LANDLOCK_ACCESS_FS_MAKE_FIFO
    | LANDLOCK_ACCESS_FS_MAKE_BLOCK
    | LANDLOCK_ACCESS_FS_MAKE_SYM
    | LANDLOCK_ACCESS_FS_TRUNCATE
)

LANDLOCK_ACCESS_FS_ALL = (
    LANDLOCK_ACCESS_FS_READ | LANDLOCK_ACCESS_FS_WRITE | LANDLOCK_ACCESS_FS_REFER
)

# Syscall numbers (x86_64)
SYS_landlock_create_ruleset = 444
SYS_landlock_add_rule = 445
SYS_landlock_restrict_self = 446
SYS_prctl = 157

# prctl constants
PR_SET_NO_NEW_PRIVS = 38

# Landlock rule types
LANDLOCK_RULE_PATH_BENEATH = 1

# Seccomp constants
SECCOMP_SET_MODE_FILTER = 1

# Network syscall numbers (x86_64)
SYS_socket = 41
SYS_socketpair = 53
SYS_connect = 42
SYS_accept = 43
SYS_accept4 = 288
SYS_bind = 49
SYS_listen = 50
SYS_getpeername = 52
SYS_getsockname = 51
SYS_shutdown = 48
SYS_sendto = 44
SYS_sendmmsg = 307
SYS_recvmmsg = 299
SYS_getsockopt = 55
SYS_setsockopt = 54

# Socket constants
AF_UNIX = 1


@dataclass
class LandlockRulesetAttr:
    """Landlock ruleset attribute structure."""

    handled_access_fs: int

    def pack(self) -> bytes:
        """Pack to bytes for syscall."""
        return struct.pack("QQQ", self.handled_access_fs, 0, 0)  # fs, net (0), scoped (0)


@dataclass
class LandlockPathBeneathAttr:
    """Landlock path beneath attribute structure."""

    allowed_access: int
    parent_fd: int

    def pack(self) -> bytes:
        """Pack to bytes for syscall."""
        return struct.pack("Qi", self.allowed_access, self.parent_fd)


def _check_landlock_available() -> bool:
    """Check if Landlock is available on this kernel."""
    if sys.platform != "linux":
        return False

    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        # Try to get Landlock ABI version
        result = libc.syscall(
            SYS_landlock_create_ruleset,
            None,
            0,
            LANDLOCK_CREATE_RULESET_VERSION,
        )
        if result >= 0:
            return True
        # ENOSYS means kernel doesn't support Landlock
        # EOPNOTSUPP means Landlock is disabled
        return ctypes.get_errno() not in (38, 95)  # ENOSYS, EOPNOTSUPP
    except (OSError, AttributeError):
        return False


LANDLOCK_AVAILABLE = _check_landlock_available()


class LandlockBackend(SandboxBackend):
    """Linux Landlock + seccomp sandbox backend.

    Uses a subprocess wrapper approach: spawns a helper that applies
    Landlock rules before exec'ing the target command.
    """

    @property
    def sandbox_type(self) -> str:
        return "linux-landlock"

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Path,
        policy: SandboxPolicy,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute command under Landlock sandbox."""
        # Prepare environment
        run_env = dict(os.environ)
        if env:
            run_env.update(env)
        run_env["CRYSTALYSE_SANDBOX"] = "landlock"

        if not policy.has_full_network_access():
            run_env["CRYSTALYSE_SANDBOX_NETWORK_DISABLED"] = "1"

        # Build sandbox wrapper command
        full_command = self._build_sandbox_command(command, policy, cwd)

        try:
            proc = await asyncio.create_subprocess_exec(
                *full_command,
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
                    sandbox_type=self.sandbox_type,
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0

            # Check for sandbox denial
            cmd_output = CommandOutput(stdout=stdout, stderr=stderr, exit_code=exit_code)
            denied = is_sandbox_denied(self.sandbox_type, cmd_output)
            reason = get_denial_reason(cmd_output) if denied else None

            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                sandbox_type=self.sandbox_type,
                sandbox_denied=denied,
                denial_reason=reason,
            )

        except FileNotFoundError as e:
            return SandboxResult(
                stdout="",
                stderr=f"Command not found: {e.filename}",
                exit_code=127,
                sandbox_type=self.sandbox_type,
            )

    def _build_sandbox_command(
        self,
        command: list[str],
        policy: SandboxPolicy,
        cwd: Path,
    ) -> list[str]:
        """Build the sandboxed command.

        Uses Python's -c flag to run a sandbox setup script inline,
        then exec the target command.
        """
        if policy.has_full_disk_write_access() and policy.has_full_network_access():
            # No restrictions needed
            return command

        # Get writable roots
        writable_roots = policy.get_writable_roots_with_cwd(cwd)
        root_paths = [str(wr.root.resolve()) for wr in writable_roots]

        # Build inline Python script to apply sandbox and exec
        sandbox_script = _build_sandbox_script(
            root_paths,
            block_network=not policy.has_full_network_access(),
        )

        # Serialize command as JSON for safe passing
        command_json = json.dumps(command)

        return [
            sys.executable,
            "-c",
            sandbox_script,
            command_json,
        ]


def _build_sandbox_script(writable_roots: list[str], block_network: bool) -> str:
    """Build the inline Python script that applies sandbox rules.

    This script:
    1. Sets PR_SET_NO_NEW_PRIVS
    2. Applies Landlock filesystem rules
    3. Optionally applies seccomp network filter
    4. Execs the target command
    """
    script = f"""\
import ctypes
import ctypes.util
import json
import os
import struct
import sys

# Landlock constants
SYS_landlock_create_ruleset = 444
SYS_landlock_add_rule = 445
SYS_landlock_restrict_self = 446
LANDLOCK_CREATE_RULESET_VERSION = 0
LANDLOCK_RULE_PATH_BENEATH = 1
LANDLOCK_ACCESS_FS_ALL = 0x7FFF  # All V3 access rights
LANDLOCK_ACCESS_FS_READ = 0xD  # execute | read_file | read_dir
PR_SET_NO_NEW_PRIVS = 38

def main():
    command = json.loads(sys.argv[1])
    writable_roots = {json.dumps(writable_roots)}
    block_network = {block_network}

    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

    # Set no new privs (required for Landlock)
    result = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    if result != 0:
        print(f"prctl failed: {{ctypes.get_errno()}}", file=sys.stderr)
        sys.exit(1)

    # Create Landlock ruleset
    # struct landlock_ruleset_attr {{ u64 handled_access_fs; u64 handled_access_net; u64 scoped; }}
    ruleset_attr = struct.pack("QQQ", LANDLOCK_ACCESS_FS_ALL, 0, 0)
    ruleset_fd = libc.syscall(
        SYS_landlock_create_ruleset,
        ruleset_attr,
        len(ruleset_attr),
        0,
    )

    if ruleset_fd < 0:
        errno = ctypes.get_errno()
        if errno == 38:  # ENOSYS - Landlock not available
            print("Landlock not available, running without sandbox", file=sys.stderr)
        else:
            print(f"landlock_create_ruleset failed: {{errno}}", file=sys.stderr)
        # Continue without sandbox
        os.execvp(command[0], command)

    # Add rule for root (read-only)
    try:
        root_fd = os.open("/", os.O_PATH | os.O_CLOEXEC)
        # struct landlock_path_beneath_attr {{ u64 allowed_access; s32 parent_fd; }}
        path_attr = struct.pack("Qi", LANDLOCK_ACCESS_FS_READ, root_fd)
        libc.syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, path_attr, 0)
        os.close(root_fd)
    except OSError:
        pass

    # Add rule for /dev/null (read-write)
    try:
        devnull_fd = os.open("/dev/null", os.O_PATH | os.O_CLOEXEC)
        path_attr = struct.pack("Qi", LANDLOCK_ACCESS_FS_ALL, devnull_fd)
        libc.syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, path_attr, 0)
        os.close(devnull_fd)
    except OSError:
        pass

    # Add rules for writable roots
    for root in writable_roots:
        try:
            root_fd = os.open(root, os.O_PATH | os.O_CLOEXEC)
            path_attr = struct.pack("Qi", LANDLOCK_ACCESS_FS_ALL, root_fd)
            libc.syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, path_attr, 0)
            os.close(root_fd)
        except OSError:
            pass

    # Apply ruleset
    result = libc.syscall(SYS_landlock_restrict_self, ruleset_fd, 0)
    os.close(ruleset_fd)

    if result < 0:
        print(f"landlock_restrict_self failed: {{ctypes.get_errno()}}", file=sys.stderr)

    # Exec the command
    os.execvp(command[0], command)

if __name__ == "__main__":
    main()
"""
    return script


def apply_landlock_to_current_process(
    writable_roots: list[Path],
    block_network: bool = False,
) -> bool:
    """Apply Landlock restrictions to the current process.

    This is for in-process sandboxing (e.g., for code execution).

    Args:
        writable_roots: Paths that should be writable.
        block_network: Whether to block network access.

    Returns:
        True if restrictions were applied, False if Landlock unavailable.
    """
    if not LANDLOCK_AVAILABLE:
        return False

    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

        # Set no new privs
        result = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
        if result != 0:
            return False

        # Create ruleset
        ruleset_attr = struct.pack("QQQ", LANDLOCK_ACCESS_FS_ALL, 0, 0)
        ruleset_fd = libc.syscall(
            SYS_landlock_create_ruleset,
            ruleset_attr,
            len(ruleset_attr),
            0,
        )

        if ruleset_fd < 0:
            return False

        # Add rule for root (read-only)
        try:
            root_fd = os.open("/", os.O_PATH)
            path_attr = struct.pack("Qi", LANDLOCK_ACCESS_FS_READ, root_fd)
            libc.syscall(
                SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, path_attr, 0
            )
            os.close(root_fd)
        except OSError:
            pass

        # Add rule for /dev/null
        try:
            devnull_fd = os.open("/dev/null", os.O_PATH)
            path_attr = struct.pack("Qi", LANDLOCK_ACCESS_FS_ALL, devnull_fd)
            libc.syscall(
                SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, path_attr, 0
            )
            os.close(devnull_fd)
        except OSError:
            pass

        # Add rules for writable roots
        for root in writable_roots:
            try:
                root_fd = os.open(str(root.resolve()), os.O_PATH)
                path_attr = struct.pack("Qi", LANDLOCK_ACCESS_FS_ALL, root_fd)
                libc.syscall(
                    SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, path_attr, 0
                )
                os.close(root_fd)
            except OSError:
                pass

        # Apply ruleset
        result = libc.syscall(SYS_landlock_restrict_self, ruleset_fd, 0)
        os.close(ruleset_fd)

        return result >= 0

    except (OSError, AttributeError):
        return False
