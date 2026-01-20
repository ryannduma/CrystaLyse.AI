"""
User Memory - Layer 3 of CrystaLyse Simple Memory System

Simple markdown file for user preferences and notes.
No machine learning, just explicit preferences - like gemini-cli.
"""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class UserMemory:
    """
    Simple markdown-based user preferences and memory system.

    Stores user preferences, research interests, and important notes
    in a human-readable markdown file. Agent reads it as context
    for personalized interactions.
    """

    def __init__(self, memory_dir: Path | None = None, user_id: str = "default"):
        """
        Initialize user memory.

        Args:
            memory_dir: Directory for memory files (default: ~/.crystalyse)
            user_id: User identifier
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".crystalyse"

        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.user_id = user_id
        self.memory_file = self.memory_dir / f"memory_{user_id}.md"

        # Initialize memory file if it doesn't exist
        if not self.memory_file.exists():
            self._initialize_memory_file()

        logger.info(f"UserMemory initialized for user {user_id} at {self.memory_file}")

    def _initialize_memory_file(self) -> None:
        """Initialize memory file with default template."""
        template = f"""# CrystaLyse Memory - User {self.user_id}

## User Preferences
- Default analysis mode: rigorous
- Preferred visualization: interactive
- Focus areas: materials discovery

## Research Interests
- Material types: Add your preferred material types here
- Applications: Add target applications here
- Constraints: Add any constraints (e.g., avoid toxic elements)

## Recent Discoveries
- Add important discoveries here as you work

## Common Patterns
- Add patterns you notice in your research
- Note recurring themes or preferences

## Important Notes
- Add any important notes or reminders here

---
*File created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                f.write(template)
            logger.info(f"Initialized memory file for user {self.user_id}")
        except OSError as e:
            logger.error(f"Failed to initialize memory file: {e}")

    def read_memory(self) -> str:
        """
        Read entire memory file content.

        Returns:
            Memory file content as string
        """
        try:
            with open(self.memory_file, encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            logger.error(f"Failed to read memory file: {e}")
            return ""

    def add_fact(self, fact: str, section: str = "Important Notes") -> None:
        """
        Add a fact to user memory.

        Args:
            fact: Fact to add
            section: Section to add fact to
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        fact_entry = f"- {fact} ({timestamp})"

        self._add_to_section(section, fact_entry)
        logger.info(f"Added fact to {section}: {fact[:50]}...")

    def add_discovery(self, discovery: str) -> None:
        """
        Add a discovery to user memory.

        Args:
            discovery: Discovery to add
        """
        self.add_fact(discovery, "Recent Discoveries")

    def add_preference(self, preference: str) -> None:
        """
        Add a preference to user memory.

        Args:
            preference: Preference to add
        """
        self.add_fact(preference, "User Preferences")

    def add_pattern(self, pattern: str) -> None:
        """
        Add a common pattern to user memory.

        Args:
            pattern: Pattern to add
        """
        self.add_fact(pattern, "Common Patterns")

    def _add_to_section(self, section: str, content: str) -> None:
        """
        Add content to a specific section of the memory file.

        Args:
            section: Section name
            content: Content to add
        """
        try:
            # Read current content
            current_content = self.read_memory()

            # Find the section
            lines = current_content.split("\n")
            section_line = f"## {section}"

            # Find section index
            section_index = -1
            for i, line in enumerate(lines):
                if line.strip() == section_line:
                    section_index = i
                    break

            if section_index == -1:
                # Section doesn't exist, add it
                lines.append(f"\n## {section}")
                lines.append(content)
            else:
                # Find next section or end of file
                next_section_index = len(lines)
                for i in range(section_index + 1, len(lines)):
                    if lines[i].startswith("## "):
                        next_section_index = i
                        break

                # Insert content before next section
                lines.insert(next_section_index, content)

            # Write back to file
            updated_content = "\n".join(lines)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                f.write(updated_content)

        except OSError as e:
            logger.error(f"Failed to add to section {section}: {e}")

    def search_memory(self, query: str) -> list[str]:
        """
        Search memory for relevant information.

        Args:
            query: Search query

        Returns:
            List of relevant memory lines
        """
        query_lower = query.lower()
        content = self.read_memory()

        matches = []
        for line in content.split("\n"):
            if query_lower in line.lower() and line.strip():
                matches.append(line.strip())

        return matches

    def get_preferences(self) -> list[str]:
        """
        Get user preferences.

        Returns:
            List of user preferences
        """
        return self._get_section_content("User Preferences")

    def get_research_interests(self) -> list[str]:
        """
        Get research interests.

        Returns:
            List of research interests
        """
        return self._get_section_content("Research Interests")

    def get_recent_discoveries(self) -> list[str]:
        """
        Get recent discoveries.

        Returns:
            List of recent discoveries
        """
        return self._get_section_content("Recent Discoveries")

    def _get_section_content(self, section: str) -> list[str]:
        """
        Get content from a specific section.

        Args:
            section: Section name

        Returns:
            List of content lines from the section
        """
        content = self.read_memory()
        lines = content.split("\n")
        section_line = f"## {section}"

        # Find section
        section_index = -1
        for i, line in enumerate(lines):
            if line.strip() == section_line:
                section_index = i
                break

        if section_index == -1:
            return []

        # Find next section or end
        next_section_index = len(lines)
        for i in range(section_index + 1, len(lines)):
            if lines[i].startswith("## "):
                next_section_index = i
                break

        # Extract content
        section_content = []
        for i in range(section_index + 1, next_section_index):
            line = lines[i].strip()
            if line and not line.startswith("---"):
                section_content.append(line)

        return section_content

    def update_preference(self, key: str, value: str) -> None:
        """
        Update a specific preference.

        Args:
            key: Preference key
            value: New value
        """
        preference_text = f"{key}: {value}"
        self.add_preference(preference_text)

    def get_context_summary(self) -> str:
        """
        Get a summary of user memory for context.

        Returns:
            Formatted context summary
        """
        preferences = self.get_preferences()[:3]  # Top 3 preferences
        interests = self.get_research_interests()[:3]  # Top 3 interests
        discoveries = self.get_recent_discoveries()[:3]  # Top 3 discoveries

        summary_parts = []

        if preferences:
            summary_parts.append("**User Preferences:**")
            summary_parts.extend(preferences)

        if interests:
            summary_parts.append("**Research Interests:**")
            summary_parts.extend(interests)

        if discoveries:
            summary_parts.append("**Recent Discoveries:**")
            summary_parts.extend(discoveries)

        return "\n".join(summary_parts) if summary_parts else "No user memory available."
