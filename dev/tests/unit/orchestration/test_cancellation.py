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

    try:
        assert not child.is_cancelled()

        parent.cancel()
        await asyncio.sleep(0.01)  # Let propagation happen

        assert child.is_cancelled()
    finally:
        child.cleanup()


@pytest.mark.asyncio
async def test_child_can_cancel_independently():
    """Child can be cancelled without affecting parent."""
    parent = CancellationToken()
    child = parent.child()

    try:
        child.cancel()

        assert child.is_cancelled()
        assert not parent.is_cancelled()
    finally:
        child.cleanup()


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


@pytest.mark.asyncio
async def test_child_scope_context_manager():
    """Context manager cleans up child token automatically."""
    parent = CancellationToken()

    async with parent.child_scope() as child:
        assert not child.is_cancelled()
        # Watcher task exists
        assert child._watcher is not None
        assert not child._watcher.done()

    # After exiting, watcher should be cancelled
    await asyncio.sleep(0.01)  # Let cancellation propagate
    assert child._watcher.done()


@pytest.mark.asyncio
async def test_cleanup_cancels_watcher():
    """cleanup() cancels the watcher task."""
    parent = CancellationToken()
    child = parent.child()

    assert child._watcher is not None
    assert not child._watcher.done()

    child.cleanup()

    await asyncio.sleep(0.01)  # Let cancellation propagate
    assert child._watcher.done()


@pytest.mark.asyncio
async def test_is_cancelled_checks_parent_immediately():
    """is_cancelled() checks parent state without waiting for watcher."""
    parent = CancellationToken()
    child = parent.child()

    try:
        # Cancel parent
        parent.cancel()

        # Child should detect immediately via is_cancelled() check
        # (without waiting for watcher task)
        assert child.is_cancelled()
    finally:
        child.cleanup()


@pytest.mark.asyncio
async def test_wait_cancelled_with_parent():
    """wait_cancelled() returns when parent is cancelled."""
    parent = CancellationToken()
    child = parent.child()

    try:

        async def cancel_parent():
            await asyncio.sleep(0.02)
            parent.cancel()

        asyncio.create_task(cancel_parent())
        await asyncio.wait_for(child.wait_cancelled(), timeout=1.0)

        assert child.is_cancelled()
    finally:
        child.cleanup()
