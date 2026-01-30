"""Tests for OrderedFutures."""

import asyncio

import pytest

from crystalyse.orchestration.futures import OrderedFutures


@pytest.mark.asyncio
async def test_empty_drain():
    """Draining empty queue returns empty list."""
    futures = OrderedFutures()
    results = await futures.drain()
    assert results == []


@pytest.mark.asyncio
async def test_maintains_order():
    """Results are returned in submission order, not completion order."""
    futures = OrderedFutures()

    async def slow():
        await asyncio.sleep(0.1)
        return "slow"

    async def fast():
        return "fast"

    # Push slow first, then fast
    futures.push(slow())
    futures.push(fast())

    results = await futures.drain()
    assert results == ["slow", "fast"]  # Order preserved


@pytest.mark.asyncio
async def test_len():
    """Length reflects pending tasks."""
    futures = OrderedFutures()
    assert len(futures) == 0

    async def noop():
        return None

    futures.push(noop())
    assert len(futures) == 1

    futures.push(noop())
    assert len(futures) == 2

    await futures.drain()
    assert len(futures) == 0


@pytest.mark.asyncio
async def test_aiter():
    """Can iterate over results."""
    futures = OrderedFutures()

    async def value(x):
        return x

    for i in range(3):
        futures.push(value(i))

    results = [r async for r in futures]
    assert results == [0, 1, 2]
