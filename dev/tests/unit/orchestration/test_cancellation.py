"""Tests for CancellationToken."""

import asyncio

import pytest

from crystalyse.orchestration.cancellation import CancellationToken


@pytest.mark.asyncio
async def test_cancel():
    """Token can be cancelled."""
    token = CancellationToken()
    assert not token.is_cancelled()

    token.cancel()
    assert token.is_cancelled()


@pytest.mark.asyncio
async def test_child_inherits_cancellation():
    """Child tokens are cancelled when parent is cancelled."""
    parent = CancellationToken()
    child = parent.child()

    assert not child.is_cancelled()

    parent.cancel()
    await asyncio.sleep(0.01)  # Let propagation happen

    assert child.is_cancelled()


@pytest.mark.asyncio
async def test_child_can_cancel_independently():
    """Child can be cancelled without affecting parent."""
    parent = CancellationToken()
    child = parent.child()

    child.cancel()

    assert child.is_cancelled()
    assert not parent.is_cancelled()


@pytest.mark.asyncio
async def test_wait_cancelled():
    """Can await cancellation."""
    token = CancellationToken()

    async def cancel_after_delay():
        await asyncio.sleep(0.05)
        token.cancel()

    asyncio.create_task(cancel_after_delay())
    await asyncio.wait_for(token.wait_cancelled(), timeout=1.0)

    assert token.is_cancelled()
