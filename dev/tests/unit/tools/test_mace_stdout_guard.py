"""``quiet_stdout()`` -- keeping third-party prints off the JSON-RPC stream.

The MCP servers in this repository speak JSON-RPC over stdio, and the MACE
imports are lazy, so ``mace.tools.cg``'s bare ``print()`` about a missing
cuequivariance can land in the middle of a response frame and make the client
reject it.  Two properties are what the servers actually rely on: nothing
written inside the block reaches stdout, and stdout is whole again afterwards
even if the wrapped import blew up.

The last test pins the property the helper deliberately does *not* have.
``contextlib.redirect_stdout`` swaps a module-level attribute, so the redirect
is process-wide: work that never entered the block loses stdout too.
"""

from __future__ import annotations

import sys
import threading

import pytest

from crystalyse.tools.mace._stdout_guard import quiet_stdout


def test_print_inside_the_block_reaches_stderr_not_stdout(capsys: pytest.CaptureFixture) -> None:
    with quiet_stdout():
        print("cuequivariance is not available")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cuequivariance is not available" in captured.err


def test_stdout_is_usable_again_after_the_block(capsys: pytest.CaptureFixture) -> None:
    with quiet_stdout():
        print("import chatter")
    print("protocol frame")

    captured = capsys.readouterr()
    assert captured.out == "protocol frame\n"
    assert "import chatter" in captured.err


def test_stdout_is_restored_when_the_body_raises(capsys: pytest.CaptureFixture) -> None:
    original = sys.stdout

    with pytest.raises(RuntimeError, match="model download failed"):
        with quiet_stdout():
            raise RuntimeError("model download failed")

    assert sys.stdout is original
    print("protocol frame")
    assert capsys.readouterr().out == "protocol frame\n"


def test_nested_blocks_restore_the_outer_stdout() -> None:
    original = sys.stdout

    with quiet_stdout():
        redirected = sys.stdout
        with quiet_stdout():
            pass
        assert sys.stdout is redirected

    assert sys.stdout is original


def test_work_that_never_entered_the_block_also_loses_stdout(
    capsys: pytest.CaptureFixture,
) -> None:
    """The known limitation: the redirect is process-wide, not block-scoped.

    ``redirect_stdout`` rebinds a module attribute, so a thread that never
    entered the block has its stdout diverted for the duration.  That is
    acceptable for the MCP servers, which import MACE from a single request
    path, and it is exactly why this helper must not be used to silence work
    running concurrently with output that matters.  The worker is joined inside
    the block, so the interleaving is fixed rather than raced.
    """

    def unrelated_worker() -> None:
        print("output from work that never entered the block")

    with quiet_stdout():
        worker = threading.Thread(target=unrelated_worker)
        worker.start()
        worker.join()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "output from work that never entered the block" in captured.err
