"""macOS Seatbelt sandbox backend.

Uses sandbox-exec to run commands under a Seatbelt profile.
Based on Codex patterns for SBPL policy generation.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from . import SandboxBackend, SandboxResult
from .detection import CommandOutput, get_denial_reason, is_sandbox_denied
from .policy import SandboxPolicy, WritableRoot

if TYPE_CHECKING:
    pass

# Path to sandbox-exec - hardcoded to defend against PATH injection
SANDBOX_EXEC_PATH = "/usr/bin/sandbox-exec"

# Base SBPL policy - deny by default, allow essential operations
# Based on Codex seatbelt_base_policy.sbpl
SEATBELT_BASE_POLICY = """\
(version 1)

; start with closed-by-default
(deny default)

; child processes inherit the policy of their parent
(allow process-exec)
(allow process-fork)
(allow signal (target same-sandbox))

; Allow cf prefs to work.
(allow user-preference-read)

; process-info
(allow process-info* (target same-sandbox))

(allow file-write-data
  (require-all
    (path "/dev/null")
    (vnode-type CHARACTER-DEVICE)))

; sysctls permitted.
(allow sysctl-read
  (sysctl-name "hw.activecpu")
  (sysctl-name "hw.busfrequency_compat")
  (sysctl-name "hw.byteorder")
  (sysctl-name "hw.cacheconfig")
  (sysctl-name "hw.cachelinesize_compat")
  (sysctl-name "hw.cpufamily")
  (sysctl-name "hw.cpufrequency_compat")
  (sysctl-name "hw.cputype")
  (sysctl-name "hw.l1dcachesize_compat")
  (sysctl-name "hw.l1icachesize_compat")
  (sysctl-name "hw.l2cachesize_compat")
  (sysctl-name "hw.l3cachesize_compat")
  (sysctl-name "hw.logicalcpu_max")
  (sysctl-name "hw.machine")
  (sysctl-name "hw.memsize")
  (sysctl-name "hw.ncpu")
  (sysctl-name "hw.nperflevels")
  (sysctl-name-prefix "hw.optional.arm.")
  (sysctl-name-prefix "hw.optional.armv8_")
  (sysctl-name "hw.packages")
  (sysctl-name "hw.pagesize_compat")
  (sysctl-name "hw.pagesize")
  (sysctl-name "hw.physicalcpu")
  (sysctl-name "hw.physicalcpu_max")
  (sysctl-name "hw.tbfrequency_compat")
  (sysctl-name "hw.vectorunit")
  (sysctl-name "kern.argmax")
  (sysctl-name "kern.hostname")
  (sysctl-name "kern.maxfilesperproc")
  (sysctl-name "kern.maxproc")
  (sysctl-name "kern.osproductversion")
  (sysctl-name "kern.osrelease")
  (sysctl-name "kern.ostype")
  (sysctl-name "kern.osvariant_status")
  (sysctl-name "kern.osversion")
  (sysctl-name "kern.secure_kernel")
  (sysctl-name "kern.usrstack64")
  (sysctl-name "kern.version")
  (sysctl-name "sysctl.proc_cputype")
  (sysctl-name "vm.loadavg")
  (sysctl-name-prefix "hw.perflevel")
  (sysctl-name-prefix "kern.proc.pgrp.")
  (sysctl-name-prefix "kern.proc.pid.")
  (sysctl-name-prefix "net.routetable.")
)

; Allow Java to read some CPU info
(allow sysctl-write
  (sysctl-name "kern.grade_cputype"))

; IOKit
(allow iokit-open
  (iokit-registry-entry-class "RootDomainUserClient")
)

; needed to look up user info
(allow mach-lookup
  (global-name "com.apple.system.opendirectoryd.libinfo")
)

; Needed for python multiprocessing on macOS
(allow ipc-posix-sem)

(allow mach-lookup
  (global-name "com.apple.PowerManagement.control")
)

; allow openpty()
(allow pseudo-tty)
(allow file-read* file-write* file-ioctl (literal "/dev/ptmx"))
(allow file-read* file-write*
  (require-all
    (regex #"^/dev/ttys[0-9]+")
    (extension "com.apple.sandbox.pty")))
(allow file-ioctl (regex #"^/dev/ttys[0-9]+"))
"""

# Network policy addon
SEATBELT_NETWORK_POLICY = """\
(allow network-outbound)
(allow network-inbound)
(allow system-socket)

(allow mach-lookup
    (global-name "com.apple.bsd.dirhelper")
    (global-name "com.apple.system.opendirectoryd.membership")
    (global-name "com.apple.SecurityServer")
    (global-name "com.apple.networkd")
    (global-name "com.apple.ocspd")
    (global-name "com.apple.trustd.agent")
    (global-name "com.apple.SystemConfiguration.DNSConfiguration")
    (global-name "com.apple.SystemConfiguration.configd")
)

(allow sysctl-read
  (sysctl-name-regex #"^net.routetable")
)

(allow file-write*
  (subpath (param "DARWIN_USER_CACHE_DIR"))
)
"""


class SeatbeltBackend(SandboxBackend):
    """macOS Seatbelt sandbox backend.

    Uses sandbox-exec to run commands under a dynamically generated
    Seatbelt profile (SBPL).
    """

    @property
    def sandbox_type(self) -> str:
        return "macos-seatbelt"

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Path,
        policy: SandboxPolicy,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute command under Seatbelt sandbox."""
        # Prepare environment
        run_env = dict(os.environ)
        if env:
            run_env.update(env)
        run_env["CRYSTALYSE_SANDBOX"] = "seatbelt"

        # Transform command to run under sandbox-exec
        full_command = self.transform_command(command, policy, cwd)

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

        except FileNotFoundError:
            return SandboxResult(
                stdout="",
                stderr=f"sandbox-exec not found at {SANDBOX_EXEC_PATH}",
                exit_code=127,
                sandbox_type=self.sandbox_type,
            )

    def transform_command(
        self,
        command: list[str],
        policy: SandboxPolicy,
        cwd: Path,
    ) -> list[str]:
        """Transform command to run under sandbox-exec.

        Generates SBPL policy and wraps command with sandbox-exec.
        """
        # Build the SBPL policy and parameters
        sbpl_policy, params = _create_seatbelt_policy(policy, cwd)

        # Build sandbox-exec args: -p <policy> -D<key>=<value>... -- <command>
        args = [SANDBOX_EXEC_PATH, "-p", sbpl_policy]

        for key, value in params:
            args.append(f"-D{key}={value}")

        args.append("--")
        args.extend(command)

        return args


def _create_seatbelt_policy(
    policy: SandboxPolicy,
    cwd: Path,
) -> tuple[str, list[tuple[str, str]]]:
    """Generate SBPL policy text and parameter definitions.

    Returns:
        Tuple of (policy_text, [(param_name, param_value), ...])
    """
    params: list[tuple[str, str]] = []

    # File write policy
    if policy.has_full_disk_write_access():
        # Allow writes everywhere
        file_write_policy = r'(allow file-write* (regex #"^/"))'
    else:
        # Generate parameterised policy for writable roots
        writable_roots = policy.get_writable_roots_with_cwd(cwd)
        file_write_policy, write_params = _create_file_write_policy(writable_roots)
        params.extend(write_params)

    # File read policy
    if policy.has_full_disk_read_access():
        file_read_policy = "; allow read-only file operations\n(allow file-read*)"
    else:
        file_read_policy = ""

    # Network policy
    if policy.has_full_network_access():
        network_policy = SEATBELT_NETWORK_POLICY
        # Add Darwin user cache dir parameter for network policy
        cache_dir = _get_darwin_user_cache_dir()
        if cache_dir:
            params.append(("DARWIN_USER_CACHE_DIR", cache_dir))
    else:
        network_policy = ""

    # Compose full policy
    full_policy = (
        f"{SEATBELT_BASE_POLICY}\n{file_read_policy}\n{file_write_policy}\n{network_policy}"
    )

    return full_policy, params


def _create_file_write_policy(
    writable_roots: list[WritableRoot],
) -> tuple[str, list[tuple[str, str]]]:
    """Generate the file-write* policy section.

    Returns:
        Tuple of (policy_text, [(param_name, param_value), ...])
    """
    if not writable_roots:
        return "", []

    params: list[tuple[str, str]] = []
    policy_parts: list[str] = []

    for index, wr in enumerate(writable_roots):
        # Canonicalise to avoid /var vs /private/var mismatches
        try:
            canonical_root = wr.root.resolve()
        except OSError:
            canonical_root = wr.root

        root_param = f"WRITABLE_ROOT_{index}"
        params.append((root_param, str(canonical_root)))

        if not wr.read_only_subpaths:
            # Simple case: whole root is writable
            policy_parts.append(f'(subpath (param "{root_param}"))')
        else:
            # Complex case: root writable except for subpaths
            require_parts = [f'(subpath (param "{root_param}"))']

            for subpath_index, ro_path in enumerate(wr.read_only_subpaths):
                try:
                    canonical_ro = ro_path.resolve()
                except OSError:
                    canonical_ro = ro_path

                ro_param = f"WRITABLE_ROOT_{index}_RO_{subpath_index}"
                require_parts.append(f'(require-not (subpath (param "{ro_param}")))')
                params.append((ro_param, str(canonical_ro)))

            policy_component = f"(require-all {' '.join(require_parts)} )"
            policy_parts.append(policy_component)

    policy_text = f"(allow file-write*\n{' '.join(policy_parts)}\n)"
    return policy_text, params


def _get_darwin_user_cache_dir() -> str | None:
    """Get the Darwin user cache directory.

    This is typically something like /var/folders/.../C/
    """
    import ctypes
    import ctypes.util

    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c"))
        # _CS_DARWIN_USER_CACHE_DIR = 65538
        buf = ctypes.create_string_buffer(1024)
        result = libc.confstr(65538, buf, 1024)
        if result > 0:
            path = buf.value.decode("utf-8")
            try:
                return str(Path(path).resolve())
            except OSError:
                return path
    except (OSError, AttributeError):
        pass

    return None
