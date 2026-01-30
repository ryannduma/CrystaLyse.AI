"""Tests for ParallelToolExecutor."""

import asyncio

import pytest

from crystalyse.orchestration import (
    CancellationToken,
    ParallelToolExecutor,
    ToolCall,
    ToolSpec,
)


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""

    async def read_tool(key: str) -> dict:
        await asyncio.sleep(0.01)
        return {"key": key, "value": f"data_{key}"}

    async def write_tool(path: str, content: str) -> dict:
        await asyncio.sleep(0.02)
        return {"written": path}

    async def slow_tool() -> str:
        await asyncio.sleep(0.5)
        return "slow_result"

    async def failing_tool() -> str:
        raise ValueError("Tool failed")

    return {
        "read": ToolSpec("read", read_tool, supports_parallel=True),
        "write": ToolSpec("write", write_tool, supports_parallel=False),
        "slow": ToolSpec("slow", slow_tool, supports_parallel=True),
        "fail": ToolSpec("fail", failing_tool, supports_parallel=True),
    }


@pytest.mark.asyncio
async def test_parallel_reads(mock_tools):
    """Parallel tools execute concurrently."""
    executor = ParallelToolExecutor(mock_tools)
    token = CancellationToken()

    # Queue multiple reads
    for i in range(3):
        executor.queue(
            ToolCall(id=f"call_{i}", name="read", input={"key": f"k{i}"}),
            token.child(),
        )

    results = await executor.drain()
    assert len(results) == 3
    assert all(r.error is None for r in results)


@pytest.mark.asyncio
async def test_serialised_writes(mock_tools):
    """Non-parallel tools execute serially."""
    executor = ParallelToolExecutor(mock_tools)
    token = CancellationToken()

    # Queue multiple writes
    for i in range(2):
        executor.queue(
            ToolCall(id=f"call_{i}", name="write", input={"path": f"p{i}", "content": "x"}),
            token.child(),
        )

    results = await executor.drain()
    assert len(results) == 2
    assert all(r.error is None for r in results)


@pytest.mark.asyncio
async def test_result_order_preserved(mock_tools):
    """Results are returned in call order."""
    executor = ParallelToolExecutor(mock_tools)
    token = CancellationToken()

    # Queue in specific order
    executor.queue(ToolCall(id="first", name="read", input={"key": "a"}), token.child())
    executor.queue(ToolCall(id="second", name="read", input={"key": "b"}), token.child())
    executor.queue(ToolCall(id="third", name="read", input={"key": "c"}), token.child())

    results = await executor.drain()
    assert [r.tool_call_id for r in results] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_handles_tool_failure(mock_tools):
    """Failed tools return error in result."""
    executor = ParallelToolExecutor(mock_tools)
    token = CancellationToken()

    executor.queue(ToolCall(id="fail_call", name="fail", input={}), token.child())
    results = await executor.drain()

    assert len(results) == 1
    assert results[0].error is not None
    assert "Tool failed" in results[0].error


@pytest.mark.asyncio
async def test_unknown_tool(mock_tools):
    """Unknown tools return error."""
    executor = ParallelToolExecutor(mock_tools)
    token = CancellationToken()

    executor.queue(ToolCall(id="x", name="nonexistent", input={}), token.child())
    results = await executor.drain()

    assert results[0].error == "Unknown tool: nonexistent"


@pytest.mark.asyncio
async def test_timeout(mock_tools):
    """Slow tools timeout."""
    executor = ParallelToolExecutor(mock_tools, timeout=0.1)
    token = CancellationToken()

    executor.queue(ToolCall(id="slow_call", name="slow", input={}), token.child())
    results = await executor.drain()

    assert "timed out" in results[0].error
