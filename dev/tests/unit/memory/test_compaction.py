"""Tests for context compaction module."""

import pytest

from crystalyse.memory.compaction import (
    CompactionConfig,
    CompactionResult,
    ContextManager,
    Message,
    estimate_tokens,
    format_messages_for_summary,
)


class TestEstimateTokens:
    """Tests for token estimation."""

    def test_empty_string(self):
        """Test empty string returns 0."""
        assert estimate_tokens("") == 0

    def test_short_string(self):
        """Test short string estimation."""
        # ~4 chars per token
        result = estimate_tokens("hello world")  # 11 chars
        assert result == 2  # 11 // 4 = 2

    def test_long_string(self):
        """Test longer string estimation."""
        text = "a" * 100
        assert estimate_tokens(text) == 25  # 100 // 4


class TestMessage:
    """Tests for Message dataclass."""

    def test_basic_message(self):
        """Test creating a basic message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.metadata == {}

    def test_message_with_name(self):
        """Test message with name."""
        msg = Message(role="tool", content="result", name="my_tool")
        assert msg.name == "my_tool"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        msg = Message(role="assistant", content="response")
        d = msg.to_dict()
        assert d == {"role": "assistant", "content": "response"}

    def test_to_dict_with_name(self):
        """Test conversion with name included."""
        msg = Message(role="tool", content="result", name="tool_name")
        d = msg.to_dict()
        assert d["name"] == "tool_name"


class TestCompactionConfig:
    """Tests for CompactionConfig."""

    def test_defaults(self):
        """Test default values."""
        config = CompactionConfig()
        assert config.max_tokens == 100_000
        assert config.threshold == 0.8
        assert config.keep_recent == 10
        assert config.summary_max_tokens == 2000

    def test_custom_values(self):
        """Test custom configuration."""
        config = CompactionConfig(
            max_tokens=50_000,
            threshold=0.7,
            keep_recent=5,
        )
        assert config.max_tokens == 50_000
        assert config.threshold == 0.7
        assert config.keep_recent == 5


class TestContextManager:
    """Tests for ContextManager."""

    def test_needs_compaction_below_threshold(self):
        """Test that small conversations don't trigger compaction."""
        config = CompactionConfig(max_tokens=1000, threshold=0.8)
        manager = ContextManager(config=config)

        messages = [
            Message(role="user", content="short"),
            Message(role="assistant", content="response"),
        ]

        assert not manager.needs_compaction(messages)

    def test_needs_compaction_above_threshold(self):
        """Test that large conversations trigger compaction."""
        config = CompactionConfig(max_tokens=100, threshold=0.8)
        manager = ContextManager(config=config)

        # Create messages that exceed threshold
        messages = [
            Message(role="user", content="x" * 400),  # ~100 tokens
        ]

        assert manager.needs_compaction(messages)

    @pytest.mark.asyncio
    async def test_compact_if_needed_no_compaction(self):
        """Test compact_if_needed when not needed."""
        config = CompactionConfig(max_tokens=10000, threshold=0.8)
        manager = ContextManager(config=config)

        messages = [Message(role="user", content="hi")]
        result = await manager.compact_if_needed(messages)

        assert not result.compacted
        assert result.messages == messages

    @pytest.mark.asyncio
    async def test_compact_preserves_recent(self):
        """Test that compaction preserves recent messages."""
        config = CompactionConfig(
            max_tokens=100,
            threshold=0.5,
            keep_recent=2,
        )
        manager = ContextManager(config=config)

        messages = [
            Message(role="user", content="old 1"),
            Message(role="assistant", content="old 2"),
            Message(role="user", content="recent 1"),
            Message(role="assistant", content="recent 2"),
        ]

        result = await manager.compact(messages)

        assert result.compacted
        # Should have summary + 2 recent
        assert len(result.messages) == 3
        # Last two should be preserved
        assert result.messages[-1].content == "recent 2"
        assert result.messages[-2].content == "recent 1"

    @pytest.mark.asyncio
    async def test_compact_creates_summary_message(self):
        """Test that compaction creates a summary message."""
        config = CompactionConfig(keep_recent=1)
        manager = ContextManager(config=config)

        messages = [
            Message(role="user", content="old message"),
            Message(role="assistant", content="old response"),
            Message(role="user", content="recent"),
        ]

        result = await manager.compact(messages)

        assert result.compacted
        # First message should be summary
        assert result.messages[0].role == "system"
        assert "Previous Context" in result.messages[0].content

    @pytest.mark.asyncio
    async def test_compact_too_few_messages(self):
        """Test compaction with fewer messages than keep_recent."""
        config = CompactionConfig(keep_recent=10)
        manager = ContextManager(config=config)

        messages = [
            Message(role="user", content="hi"),
            Message(role="assistant", content="hello"),
        ]

        result = await manager.compact(messages)

        assert not result.compacted
        assert len(result.messages) == 2

    def test_compaction_count(self):
        """Test that compaction count is tracked."""
        manager = ContextManager()
        assert manager.compaction_count == 0


class TestFormatMessagesForSummary:
    """Tests for format_messages_for_summary."""

    def test_basic_formatting(self):
        """Test basic message formatting."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
        ]
        result = format_messages_for_summary(messages)

        assert "[USER]: Hello" in result
        assert "[ASSISTANT]: Hi there" in result

    def test_includes_tool_name(self):
        """Test that tool names are included."""
        messages = [
            Message(role="tool", content="result", name="my_tool"),
        ]
        result = format_messages_for_summary(messages)

        assert "TOOL (my_tool)" in result

    def test_truncates_long_content(self):
        """Test that very long content is truncated."""
        messages = [
            Message(role="user", content="x" * 3000),
        ]
        result = format_messages_for_summary(messages)

        assert "[truncated]" in result
        assert len(result) < 3000


class TestCompactionResult:
    """Tests for CompactionResult dataclass."""

    def test_result_creation(self):
        """Test creating a compaction result."""
        messages = [Message(role="user", content="test")]
        result = CompactionResult(
            messages=messages,
            summary="Summary text",
            original_count=5,
            final_count=2,
            compacted=True,
        )

        assert result.compacted
        assert result.original_count == 5
        assert result.final_count == 2
        assert result.summary == "Summary text"


class TestExtractKeyPoints:
    """Tests for the fallback key point extraction."""

    @pytest.mark.asyncio
    async def test_extracts_findings(self):
        """Test that findings are extracted."""
        manager = ContextManager()

        messages = [
            Message(role="assistant", content="Found stable Li2O structure"),
            Message(role="user", content="What about Na?"),
        ]

        # With only 2 messages and keep_recent=10, compact won't trigger
        # so we test the extraction method directly
        summary = manager._extract_key_points(messages)

        assert "Found stable" in summary or "Li2O" in summary

    @pytest.mark.asyncio
    async def test_extracts_user_requests(self):
        """Test that user requests are extracted."""
        manager = ContextManager()

        messages = [
            Message(role="user", content="Find perovskite materials"),
        ]

        summary = manager._extract_key_points(messages)
        assert "User request" in summary or "perovskite" in summary

    @pytest.mark.asyncio
    async def test_extracts_errors(self):
        """Test that errors are extracted."""
        manager = ContextManager()

        messages = [
            Message(role="assistant", content="Error: SMACT validation failed"),
        ]

        summary = manager._extract_key_points(messages)
        assert "Issue" in summary or "error" in summary.lower()

    @pytest.mark.asyncio
    async def test_empty_messages(self):
        """Test with no extractable content."""
        manager = ContextManager()

        messages = [
            Message(role="assistant", content="ok"),
        ]

        summary = manager._extract_key_points(messages)
        assert "1 messages" in summary
