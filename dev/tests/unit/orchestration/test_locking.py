"""Tests for AsyncRwLock."""

import asyncio

import pytest

from crystalyse.orchestration.locking import AsyncRwLock


@pytest.mark.asyncio
async def test_multiple_readers():
    """Multiple readers can hold lock simultaneously."""
    lock = AsyncRwLock()
    readers_inside = 0
    max_readers = 0

    async def reader():
        nonlocal readers_inside, max_readers
        async with lock.read():
            readers_inside += 1
            max_readers = max(max_readers, readers_inside)
            await asyncio.sleep(0.05)
            readers_inside -= 1

    # Start 3 readers concurrently
    await asyncio.gather(reader(), reader(), reader())
    assert max_readers == 3  # All readers ran simultaneously


@pytest.mark.asyncio
async def test_writer_exclusive():
    """Writer gets exclusive access."""
    lock = AsyncRwLock()
    events = []

    async def reader(name: str):
        async with lock.read():
            events.append(f"{name}_start")
            await asyncio.sleep(0.02)
            events.append(f"{name}_end")

    async def writer(name: str):
        async with lock.write():
            events.append(f"{name}_start")
            await asyncio.sleep(0.02)
            events.append(f"{name}_end")

    # Writer should block until reader finishes
    await asyncio.gather(reader("r1"), writer("w1"))

    # Writer must complete atomically (start and end together)
    w1_start = events.index("w1_start")
    w1_end = events.index("w1_end")
    assert w1_end == w1_start + 1  # No interleaving


@pytest.mark.asyncio
async def test_writer_blocks_readers():
    """Readers wait for writer to finish."""
    lock = AsyncRwLock()
    order = []

    async def writer():
        async with lock.write():
            order.append("writer_in")
            await asyncio.sleep(0.05)
            order.append("writer_out")

    async def reader():
        await asyncio.sleep(0.01)  # Let writer start first
        async with lock.read():
            order.append("reader_in")

    await asyncio.gather(writer(), reader())
    assert order == ["writer_in", "writer_out", "reader_in"]
