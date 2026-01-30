"""Tests for sandbox denial detection."""

from crystalyse.sandbox.detection import (
    SANDBOX_DENIED_KEYWORDS,
    CommandOutput,
    get_denial_reason,
    is_sandbox_denied,
)


class TestCommandOutput:
    """Tests for CommandOutput dataclass."""

    def test_command_output_creation(self):
        """Test creating a CommandOutput."""
        output = CommandOutput(stdout="hello", stderr="", exit_code=0)
        assert output.stdout == "hello"
        assert output.stderr == ""
        assert output.exit_code == 0


class TestIsSandboxDenied:
    """Tests for is_sandbox_denied function."""

    def test_success_not_denied(self):
        """Test that successful commands are not marked as denied."""
        output = CommandOutput(stdout="ok", stderr="", exit_code=0)
        assert not is_sandbox_denied("macos-seatbelt", output)
        assert not is_sandbox_denied("linux-landlock", output)

    def test_no_sandbox_not_denied(self):
        """Test that failures without sandbox are not marked as denied."""
        output = CommandOutput(stdout="", stderr="some error", exit_code=1)
        assert not is_sandbox_denied("none", output)

    def test_permission_denied_keyword(self):
        """Test detection of 'permission denied' keyword."""
        output = CommandOutput(
            stdout="",
            stderr="bash: /protected/file: Permission denied",
            exit_code=1,
        )
        assert is_sandbox_denied("macos-seatbelt", output)
        assert is_sandbox_denied("linux-landlock", output)

    def test_operation_not_permitted_keyword(self):
        """Test detection of 'operation not permitted' keyword."""
        output = CommandOutput(
            stdout="",
            stderr="bash: /dev/secret: Operation not permitted",
            exit_code=1,
        )
        assert is_sandbox_denied("macos-seatbelt", output)

    def test_read_only_filesystem_keyword(self):
        """Test detection of 'read-only file system' keyword."""
        output = CommandOutput(
            stdout="",
            stderr="cp: cannot create regular file: Read-only file system",
            exit_code=1,
        )
        assert is_sandbox_denied("linux-landlock", output)

    def test_landlock_keyword(self):
        """Test detection of 'landlock' keyword."""
        output = CommandOutput(
            stdout="",
            stderr="Error: landlock restriction violated",
            exit_code=1,
        )
        assert is_sandbox_denied("linux-landlock", output)

    def test_seccomp_keyword(self):
        """Test detection of 'seccomp' keyword."""
        output = CommandOutput(
            stdout="",
            stderr="seccomp filter blocked syscall",
            exit_code=1,
        )
        assert is_sandbox_denied("linux-landlock", output)

    def test_sandbox_keyword(self):
        """Test detection of 'sandbox' keyword."""
        output = CommandOutput(
            stdout="sandbox policy violation",
            stderr="",
            exit_code=1,
        )
        assert is_sandbox_denied("macos-seatbelt", output)

    def test_sigsys_exit_code_linux(self):
        """Test detection of SIGSYS exit code on Linux."""
        # SIGSYS is signal 31, so exit code is 128 + 31 = 159
        output = CommandOutput(stdout="", stderr="", exit_code=159)
        assert is_sandbox_denied("linux-landlock", output)

    def test_sigsys_exit_code_not_on_macos(self):
        """Test that SIGSYS exit code is not detected on macOS."""
        output = CommandOutput(stdout="", stderr="", exit_code=159)
        assert not is_sandbox_denied("macos-seatbelt", output)

    def test_unrelated_failure_not_denied(self):
        """Test that unrelated failures are not marked as denied."""
        output = CommandOutput(
            stdout="",
            stderr="command not found: nosuchcommand",
            exit_code=127,
        )
        assert not is_sandbox_denied("macos-seatbelt", output)
        assert not is_sandbox_denied("linux-landlock", output)

    def test_case_insensitive_detection(self):
        """Test that keyword detection is case-insensitive."""
        output = CommandOutput(
            stdout="",
            stderr="PERMISSION DENIED",
            exit_code=1,
        )
        assert is_sandbox_denied("macos-seatbelt", output)


class TestGetDenialReason:
    """Tests for get_denial_reason function."""

    def test_permission_denied_reason(self):
        """Test reason for permission denied."""
        output = CommandOutput(stdout="", stderr="Permission denied", exit_code=1)
        reason = get_denial_reason(output)
        assert reason is not None
        assert "permission" in reason.lower() or "path" in reason.lower()

    def test_read_only_reason(self):
        """Test reason for read-only filesystem."""
        output = CommandOutput(stdout="", stderr="Read-only file system", exit_code=1)
        reason = get_denial_reason(output)
        assert reason is not None
        assert "read-only" in reason.lower() or "write" in reason.lower()

    def test_operation_not_permitted_reason(self):
        """Test reason for operation not permitted."""
        output = CommandOutput(stdout="", stderr="Operation not permitted", exit_code=1)
        reason = get_denial_reason(output)
        assert reason is not None
        assert "operation" in reason.lower() or "sandbox" in reason.lower()

    def test_seccomp_reason(self):
        """Test reason for seccomp violation."""
        output = CommandOutput(stdout="", stderr="seccomp blocked", exit_code=1)
        reason = get_denial_reason(output)
        assert reason is not None
        assert "seccomp" in reason.lower()

    def test_landlock_reason(self):
        """Test reason for landlock violation."""
        output = CommandOutput(stdout="", stderr="landlock denied", exit_code=1)
        reason = get_denial_reason(output)
        assert reason is not None
        assert "landlock" in reason.lower()

    def test_no_reason_for_unrelated_error(self):
        """Test that no reason is given for unrelated errors."""
        output = CommandOutput(stdout="", stderr="syntax error", exit_code=1)
        reason = get_denial_reason(output)
        assert reason is None


class TestSandboxDeniedKeywords:
    """Tests for the SANDBOX_DENIED_KEYWORDS constant."""

    def test_keywords_tuple(self):
        """Test that keywords is a tuple of strings."""
        assert isinstance(SANDBOX_DENIED_KEYWORDS, tuple)
        assert all(isinstance(kw, str) for kw in SANDBOX_DENIED_KEYWORDS)

    def test_keywords_are_lowercase(self):
        """Test that all keywords are lowercase for case-insensitive matching."""
        for kw in SANDBOX_DENIED_KEYWORDS:
            assert kw == kw.lower(), f"Keyword '{kw}' should be lowercase"

    def test_essential_keywords_present(self):
        """Test that essential keywords are in the list."""
        essential = ["permission denied", "operation not permitted", "sandbox"]
        for kw in essential:
            assert kw in SANDBOX_DENIED_KEYWORDS, f"Missing essential keyword: {kw}"
