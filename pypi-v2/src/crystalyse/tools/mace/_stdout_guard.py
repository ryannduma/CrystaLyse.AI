"""Keep third-party import chatter off stdout.

The MCP servers in this repository speak JSON-RPC over stdio, so *any* stray
write to stdout corrupts the protocol stream and the client rejects the frame
with a ``JSONRPCMessage`` validation error.

``mace.tools.cg`` uses a bare ``print()`` when cuequivariance is unavailable
(the normal case on CPU/MPS machines), and the MACE imports here are lazy --
they run inside tool calls, not only at startup -- so the notice can land in
the middle of a response.  Wrap those imports in ``quiet_stdout()`` to send
anything they print to stderr, where logs belong.
"""

import contextlib
import sys
from collections.abc import Iterator


@contextlib.contextmanager
def quiet_stdout() -> Iterator[None]:
    """Redirect ``sys.stdout`` writes to ``sys.stderr`` for the block."""
    with contextlib.redirect_stdout(sys.stderr):
        yield
