"""Context compaction for long conversations.

Summarises old messages when approaching token limits to maintain
conversation continuity while staying within context windows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default compaction prompt
COMPACTION_PROMPT = """Summarise the following conversation history concisely.

Preserve:
- Key findings with their sources/provenance
- User constraints and preferences
- Important decisions made
- Errors encountered and how they were resolved
- Material compositions and properties discussed

Be concise but complete. Use bullet points for clarity.

Conversation to summarise:
{conversation}"""


@dataclass
class CompactionConfig:
    """Configuration for context compaction.

    Attributes:
        max_tokens: Maximum tokens before triggering compaction.
        threshold: Fraction of max_tokens that triggers compaction (0.0-1.0).
        keep_recent: Number of recent messages to preserve uncompacted.
        summary_max_tokens: Maximum tokens for the summary.
    """

    max_tokens: int = 100_000
    threshold: float = 0.8
    keep_recent: int = 10
    summary_max_tokens: int = 2000


@dataclass
class Message:
    """A conversation message.

    Attributes:
        role: Message role (system, user, assistant, tool).
        content: Message content.
        name: Optional name for tool messages.
        metadata: Optional metadata.
    """

    role: str
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class CompactionResult:
    """Result of a compaction operation.

    Attributes:
        messages: The compacted message list.
        summary: The generated summary (if compaction occurred).
        original_count: Number of messages before compaction.
        final_count: Number of messages after compaction.
        compacted: Whether compaction was performed.
    """

    messages: list[Message]
    summary: str | None
    original_count: int
    final_count: int
    compacted: bool


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token.
    This is a rough approximation suitable for triggering compaction.
    """
    return len(text) // 4


def estimate_message_tokens(messages: list[Message]) -> int:
    """Estimate total tokens in a message list."""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.content)
        if msg.name:
            total += estimate_tokens(msg.name)
        # Add overhead for role and structure
        total += 4
    return total


def format_messages_for_summary(messages: list[Message]) -> str:
    """Format messages for summarisation.

    Args:
        messages: Messages to format.

    Returns:
        Formatted string suitable for summarisation.
    """
    parts = []
    for msg in messages:
        role = msg.role.upper()
        if msg.name:
            role = f"{role} ({msg.name})"

        # Truncate very long messages
        content = msg.content
        if len(content) > 2000:
            content = content[:2000] + "... [truncated]"

        parts.append(f"[{role}]: {content}")

    return "\n\n".join(parts)


class ContextManager:
    """Manages context compaction for conversations.

    Monitors token usage and compacts old messages when approaching
    the context limit, preserving recent messages and generating
    a summary of older content.
    """

    def __init__(
        self,
        config: CompactionConfig | None = None,
        summariser: Any | None = None,
    ):
        """Initialize the context manager.

        Args:
            config: Compaction configuration.
            summariser: Optional callable for generating summaries.
                        If None, uses a simple concatenation fallback.
        """
        self.config = config or CompactionConfig()
        self.summariser = summariser
        self._compaction_count = 0

    @property
    def compaction_count(self) -> int:
        """Number of compactions performed."""
        return self._compaction_count

    def needs_compaction(self, messages: list[Message]) -> bool:
        """Check if messages need compaction.

        Args:
            messages: Current message list.

        Returns:
            True if token count exceeds threshold.
        """
        current_tokens = estimate_message_tokens(messages)
        threshold_tokens = int(self.config.max_tokens * self.config.threshold)
        return current_tokens >= threshold_tokens

    async def compact_if_needed(
        self,
        messages: list[Message],
    ) -> CompactionResult:
        """Compact messages if approaching token limit.

        Args:
            messages: Current message list.

        Returns:
            CompactionResult with potentially compacted messages.
        """
        if not self.needs_compaction(messages):
            return CompactionResult(
                messages=messages,
                summary=None,
                original_count=len(messages),
                final_count=len(messages),
                compacted=False,
            )

        return await self.compact(messages)

    async def compact(
        self,
        messages: list[Message],
    ) -> CompactionResult:
        """Compact messages by summarising older content.

        Keeps recent messages intact and summarises older ones.

        Args:
            messages: Current message list.

        Returns:
            CompactionResult with compacted messages.
        """
        original_count = len(messages)

        # Split into old and recent
        if len(messages) <= self.config.keep_recent:
            # Nothing to compact
            return CompactionResult(
                messages=messages,
                summary=None,
                original_count=original_count,
                final_count=original_count,
                compacted=False,
            )

        split_point = len(messages) - self.config.keep_recent
        old_messages = messages[:split_point]
        recent_messages = messages[split_point:]

        # Generate summary
        summary = await self._generate_summary(old_messages)

        # Create compacted message list
        summary_message = Message(
            role="system",
            content=f"## Previous Context Summary\n\n{summary}",
            metadata={"compacted": True, "original_count": len(old_messages)},
        )

        compacted = [summary_message, *recent_messages]

        self._compaction_count += 1

        logger.info(
            f"Compacted {original_count} messages to {len(compacted)} "
            f"(summarised {len(old_messages)} old messages)"
        )

        return CompactionResult(
            messages=compacted,
            summary=summary,
            original_count=original_count,
            final_count=len(compacted),
            compacted=True,
        )

    async def _generate_summary(self, messages: list[Message]) -> str:
        """Generate a summary of messages.

        Args:
            messages: Messages to summarise.

        Returns:
            Summary text.
        """
        if self.summariser:
            # Use provided summariser
            formatted = format_messages_for_summary(messages)
            prompt = COMPACTION_PROMPT.format(conversation=formatted)
            return await self.summariser(prompt)

        # Fallback: extract key points without LLM
        return self._extract_key_points(messages)

    def _extract_key_points(self, messages: list[Message]) -> str:
        """Extract key points without LLM summarisation.

        A simple fallback that preserves important information.
        """
        points = []

        for msg in messages:
            content = msg.content

            # Look for findings/results
            if any(
                kw in content.lower()
                for kw in ["found", "result", "discovered", "stable", "unstable"]
            ):
                # Extract first sentence or line
                first_line = content.split("\n")[0]
                if len(first_line) < 200:
                    points.append(f"- {msg.role}: {first_line}")

            # Look for user constraints
            if msg.role == "user" and len(content) < 200:
                points.append(f"- User request: {content}")

            # Look for errors
            if "error" in content.lower() or "failed" in content.lower():
                first_line = content.split("\n")[0]
                if len(first_line) < 200:
                    points.append(f"- Issue: {first_line}")

        if not points:
            return f"Previous conversation contained {len(messages)} messages."

        # Limit to reasonable size
        if len(points) > 20:
            points = points[:20]
            points.append("- [additional context truncated]")

        return "\n".join(points)


async def create_summariser_from_openai(
    model: str = "gpt-4o-mini",
    max_tokens: int = 2000,
) -> Any:
    """Create a summariser using OpenAI API.

    Args:
        model: Model to use for summarisation.
        max_tokens: Maximum tokens for summary.

    Returns:
        Async callable that generates summaries.
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("OpenAI not available for summarisation")
        return None

    client = AsyncOpenAI()

    async def summarise(prompt: str) -> str:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    return summarise
