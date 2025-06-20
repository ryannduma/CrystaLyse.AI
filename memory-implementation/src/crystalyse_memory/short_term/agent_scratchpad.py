# crystalyse_memory/short_term/agent_scratchpad.py
"""
Agent Scratchpad for CrystaLyse.AI Memory System

Provides erasable reasoning workspace for agent planning and thought processes.
Based on OpenAI Agents SDK patterns for "Thought → Tool → Observation → Answer" workflows.
"""

from typing import Dict, List, Optional
from datetime import datetime
import tempfile
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AgentScratchpad:
    """
    Erasable scratchpad for agent reasoning and planning.
    
    Provides a persistent markdown file where the agent can write thoughts,
    plans, progress updates, and reasoning steps during complex queries.
    """
    
    def __init__(self, session_id: str, user_id: str, base_dir: Optional[Path] = None):
        """
        Initialise agent scratchpad.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            base_dir: Base directory for scratchpad files
        """
        self.session_id = session_id
        self.user_id = user_id
        self.scratchpad_content = ""
        self.reasoning_steps: List[Dict[str, str]] = []
        self.current_plan: Optional[str] = None
        
        # Set up file path
        self.base_dir = base_dir or Path("./memory/scratchpads")
        user_dir = self.base_dir / self.user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        self.temp_file_path = user_dir / f"scratchpad_{self.session_id}.md"
        
        # Initialise file
        self._initialise_file()
        
        logger.info(f"AgentScratchpad initialised: {self.temp_file_path}")
    
    def _initialise_file(self) -> None:
        """Initialise the scratchpad markdown file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        initial_content = f"""# Agent Scratchpad - Session {self.session_id}

**User**: {self.user_id}  
**Started**: {timestamp}  
**Session**: {self.session_id}

---

This is the agent's reasoning workspace for the current session.
The agent uses this scratchpad to plan, reason, and track progress.

"""
        
        with open(self.temp_file_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
    
    def write_to_scratchpad(self, content: str, section: str = "reasoning") -> None:
        """
        Agent writes to scratchpad.
        
        Args:
            content: Content to write
            section: Section type (plan, reasoning, progress, tools_used, observation)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format content based on section type
        section_icons = {
            "plan": "🎯",
            "reasoning": "🧠", 
            "progress": "✅",
            "tools_used": "🔧",
            "observation": "👁️",
            "thought": "💭",
            "analysis": "📊",
            "conclusion": "🏁"
        }
        
        icon = section_icons.get(section, "📝")
        
        if section == "plan":
            self.current_plan = content
            new_content = f"\n## {icon} Current Plan ({timestamp})\n\n{content}\n"
        elif section == "reasoning":
            new_content = f"\n## {icon} Reasoning Step ({timestamp})\n\n{content}\n"
        elif section == "progress":
            new_content = f"\n## {icon} Progress Update ({timestamp})\n\n{content}\n"
        elif section == "tools_used":
            new_content = f"\n## {icon} Tools Used ({timestamp})\n\n{content}\n"
        elif section == "observation":
            new_content = f"\n## {icon} Observation ({timestamp})\n\n{content}\n"
        elif section == "thought":
            new_content = f"\n## {icon} Thought ({timestamp})\n\n{content}\n"
        elif section == "analysis":
            new_content = f"\n## {icon} Analysis ({timestamp})\n\n{content}\n"
        elif section == "conclusion":
            new_content = f"\n## {icon} Conclusion ({timestamp})\n\n{content}\n"
        else:
            new_content = f"\n## {icon} {section.title()} ({timestamp})\n\n{content}\n"
        
        self.scratchpad_content += new_content
        self.reasoning_steps.append({
            "timestamp": timestamp,
            "section": section,
            "content": content
        })
        
        # Update file
        self._update_file()
        
        logger.debug(f"Added {section} to scratchpad: {content[:50]}...")
    
    def read_scratchpad(self) -> str:
        """Read current scratchpad contents."""
        return self.scratchpad_content
    
    def get_current_plan(self) -> Optional[str]:
        """Get current plan if any."""
        return self.current_plan
    
    def update_plan(self, new_plan: str) -> None:
        """
        Update current plan, erasing old one.
        
        Args:
            new_plan: New plan to replace existing plan
        """
        self.erase_section("plan")
        self.write_to_scratchpad(new_plan, "plan")
        logger.debug(f"Plan updated: {new_plan[:50]}...")
    
    def erase_section(self, section: str) -> None:
        """
        Erase specific section from scratchpad.
        
        Args:
            section: Section type to remove
        """
        # Remove from reasoning steps
        original_count = len(self.reasoning_steps)
        self.reasoning_steps = [
            step for step in self.reasoning_steps 
            if step["section"] != section
        ]
        removed_count = original_count - len(self.reasoning_steps)
        
        # Clear current plan if erasing plan section
        if section == "plan":
            self.current_plan = None
        
        # Rebuild scratchpad content
        self._rebuild_content()
        
        logger.debug(f"Erased {removed_count} entries of section '{section}'")
    
    def clear_scratchpad(self) -> None:
        """Completely clear scratchpad."""
        self.scratchpad_content = ""
        self.reasoning_steps = []
        self.current_plan = None
        self._update_file()
        logger.debug("Scratchpad cleared")
    
    def _rebuild_content(self) -> None:
        """Rebuild scratchpad content from reasoning steps."""
        self.scratchpad_content = ""
        
        # Sort by timestamp to maintain order
        sorted_steps = sorted(self.reasoning_steps, 
                            key=lambda x: x["timestamp"])
        
        for step in sorted_steps:
            timestamp = step["timestamp"]
            section = step["section"]
            content = step["content"]
            
            # Use same formatting as write_to_scratchpad
            section_icons = {
                "plan": "🎯",
                "reasoning": "🧠", 
                "progress": "✅",
                "tools_used": "🔧",
                "observation": "👁️",
                "thought": "💭",
                "analysis": "📊",
                "conclusion": "🏁"
            }
            
            icon = section_icons.get(section, "📝")
            
            if section == "plan":
                self.scratchpad_content += f"\n## {icon} Current Plan ({timestamp})\n\n{content}\n"
            elif section == "reasoning":
                self.scratchpad_content += f"\n## {icon} Reasoning Step ({timestamp})\n\n{content}\n"
            elif section == "progress":
                self.scratchpad_content += f"\n## {icon} Progress Update ({timestamp})\n\n{content}\n"
            elif section == "tools_used":
                self.scratchpad_content += f"\n## {icon} Tools Used ({timestamp})\n\n{content}\n"
            elif section == "observation":
                self.scratchpad_content += f"\n## {icon} Observation ({timestamp})\n\n{content}\n"
            elif section == "thought":
                self.scratchpad_content += f"\n## {icon} Thought ({timestamp})\n\n{content}\n"
            elif section == "analysis":
                self.scratchpad_content += f"\n## {icon} Analysis ({timestamp})\n\n{content}\n"
            elif section == "conclusion":
                self.scratchpad_content += f"\n## {icon} Conclusion ({timestamp})\n\n{content}\n"
            else:
                self.scratchpad_content += f"\n## {icon} {section.title()} ({timestamp})\n\n{content}\n"
        
        # Update file
        self._update_file()
    
    def _update_file(self) -> None:
        """Update the scratchpad markdown file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        full_content = f"""# Agent Scratchpad - Session {self.session_id}

**User**: {self.user_id}  
**Last Updated**: {timestamp}  
**Session**: {self.session_id}

---

This is the agent's reasoning workspace for the current session.
The agent uses this scratchpad to plan, reason, and track progress.

{self.scratchpad_content}

---
*End of scratchpad*
"""
        
        try:
            with open(self.temp_file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
        except Exception as e:
            logger.error(f"Failed to update scratchpad file: {e}")
    
    def get_file_path(self) -> str:
        """Get path to scratchpad file for agent reference."""
        return str(self.temp_file_path)
    
    def get_recent_steps(self, section: Optional[str] = None, limit: int = 5) -> List[Dict[str, str]]:
        """
        Get recent reasoning steps.
        
        Args:
            section: Filter by section type, None for all sections
            limit: Maximum number of steps to return
            
        Returns:
            List of recent reasoning steps
        """
        steps = self.reasoning_steps
        
        if section:
            steps = [step for step in steps if step["section"] == section]
        
        # Sort by timestamp (most recent first) and limit
        sorted_steps = sorted(steps, key=lambda x: x["timestamp"], reverse=True)
        return sorted_steps[:limit]
    
    def get_stats(self) -> Dict[str, any]:
        """Get scratchpad statistics."""
        section_counts = {}
        for step in self.reasoning_steps:
            section = step["section"]
            section_counts[section] = section_counts.get(section, 0) + 1
        
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "total_steps": len(self.reasoning_steps),
            "section_counts": section_counts,
            "current_plan": self.current_plan is not None,
            "file_path": str(self.temp_file_path),
            "file_exists": self.temp_file_path.exists()
        }
    
    def cleanup(self) -> None:
        """Clean up scratchpad file when session ends."""
        try:
            if self.temp_file_path.exists():
                # Archive instead of delete for debugging
                archive_path = self.temp_file_path.with_suffix('.archived.md')
                self.temp_file_path.rename(archive_path)
                logger.info(f"Scratchpad archived: {archive_path}")
        except Exception as e:
            logger.warning(f"Failed to archive scratchpad: {e}")
    
    def export_summary(self) -> Dict[str, any]:
        """Export a summary of the scratchpad session."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "final_plan": self.current_plan,
            "total_reasoning_steps": len(self.reasoning_steps),
            "reasoning_summary": self.reasoning_steps,
            "file_path": str(self.temp_file_path)
        }