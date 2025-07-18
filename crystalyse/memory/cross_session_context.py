"""
Cross-Session Context - Layer 4 of CrystaLyse Simple Memory System

Auto-generated markdown summaries for long-term memory.
No fancy graphs, just useful summaries - like gemini-cli.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging
from .discovery_cache import DiscoveryCache
from .user_memory import UserMemory

logger = logging.getLogger(__name__)


class CrossSessionContext:
    """
    Auto-generated insights and summaries for cross-session memory.
    
    Generates weekly summaries of discoveries, research patterns,
    and insights to help the agent maintain long-term context
    across multiple sessions.
    """
    
    def __init__(self, memory_dir: Optional[Path] = None, user_id: str = "default"):
        """
        Initialize cross-session context.
        
        Args:
            memory_dir: Directory for memory files (default: ~/.crystalyse)
            user_id: User identifier
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".crystalyse"
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.user_id = user_id
        self.insights_file = self.memory_dir / f"insights_{user_id}.md"
        
        # Initialize related components
        self.discovery_cache = DiscoveryCache(self.memory_dir)
        self.user_memory = UserMemory(self.memory_dir, user_id)
        
        logger.info(f"CrossSessionContext initialized for user {user_id}")
    
    def generate_weekly_summary(self) -> str:
        """
        Generate a weekly summary of discoveries and patterns.
        
        Returns:
            Weekly summary as markdown string
        """
        # Get recent discoveries (last 7 days)
        recent_discoveries = self._get_recent_discoveries(days=7)
        
        # Analyze patterns
        patterns = self._analyze_patterns(recent_discoveries)
        
        # Generate summary
        summary = self._create_summary(recent_discoveries, patterns)
        
        # Save summary
        self._save_insights(summary)
        
        return summary
    
    def _get_recent_discoveries(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get discoveries from the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent discoveries
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_discoveries = []
        
        # Get all discoveries from cache
        all_discoveries = self.discovery_cache.get_recent_discoveries(limit=100)
        
        for discovery in all_discoveries:
            try:
                # Parse timestamp
                timestamp_str = discovery.get("timestamp", "")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp >= cutoff_date:
                        recent_discoveries.append(discovery)
            except (ValueError, TypeError):
                continue
        
        return recent_discoveries
    
    def _analyze_patterns(self, discoveries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze patterns in discoveries.
        
        Args:
            discoveries: List of discoveries to analyze
            
        Returns:
            Dictionary of identified patterns
        """
        patterns = {
            "material_types": {},
            "applications": {},
            "elements": {},
            "common_queries": [],
            "success_rate": 0
        }
        
        if not discoveries:
            return patterns
        
        # Analyze material types and elements
        for discovery in discoveries:
            formula = discovery.get("formula", "")
            properties = discovery.get("properties", {})
            
            # Count elements
            for char in formula:
                if char.isupper():
                    patterns["elements"][char] = patterns["elements"].get(char, 0) + 1
            
            # Look for applications in properties
            if isinstance(properties, dict):
                for key, value in properties.items():
                    if "application" in key.lower():
                        app = str(value).lower()
                        patterns["applications"][app] = patterns["applications"].get(app, 0) + 1
        
        # Calculate success rate (simplified)
        patterns["success_rate"] = len(discoveries)
        
        return patterns
    
    def _create_summary(self, discoveries: List[Dict[str, Any]], patterns: Dict[str, Any]) -> str:
        """
        Create markdown summary from discoveries and patterns.
        
        Args:
            discoveries: List of discoveries
            patterns: Analyzed patterns
            
        Returns:
            Markdown summary string
        """
        current_date = datetime.now().strftime('%Y-%m-%d')
        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        summary = f"""# Weekly Materials Insights - {current_date}

## Key Discoveries This Week ({week_start} to {current_date})

"""
        
        # Add discoveries
        if discoveries:
            for i, discovery in enumerate(discoveries[:5], 1):  # Top 5 discoveries
                formula = discovery.get("formula", "Unknown")
                properties = discovery.get("properties", {})
                cached_at = discovery.get("cached_at", "Unknown time")
                
                summary += f"{i}. **{formula}** - analyzed at {cached_at}\n"
                
                # Add key properties
                if isinstance(properties, dict):
                    for key, value in list(properties.items())[:2]:  # Top 2 properties
                        summary += f"   - {key}: {value}\n"
                
                summary += "\n"
        else:
            summary += "No discoveries recorded this week.\n\n"
        
        # Add patterns
        summary += "## Research Patterns\n\n"
        
        if patterns["elements"]:
            top_elements = sorted(patterns["elements"].items(), key=lambda x: x[1], reverse=True)[:5]
            summary += f"**Most studied elements:** {', '.join([f'{elem} ({count})' for elem, count in top_elements])}\n\n"
        
        if patterns["applications"]:
            top_apps = sorted(patterns["applications"].items(), key=lambda x: x[1], reverse=True)[:3]
            summary += f"**Primary applications:** {', '.join([f'{app} ({count})' for app, count in top_apps])}\n\n"
        
        summary += f"**Discovery rate:** {len(discoveries)} materials analyzed this week\n\n"
        
        # Add research focus
        user_interests = self.user_memory.get_research_interests()
        if user_interests:
            summary += "## Current Research Focus\n\n"
            for interest in user_interests[:3]:
                summary += f"- {interest}\n"
            summary += "\n"
        
        # Add recommendations
        summary += "## Recommendations for Next Week\n\n"
        summary += self._generate_recommendations(discoveries, patterns)
        
        summary += f"\n---\n*Generated automatically: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return summary
    
    def _generate_recommendations(self, discoveries: List[Dict[str, Any]], patterns: Dict[str, Any]) -> str:
        """
        Generate recommendations based on discoveries and patterns.
        
        Args:
            discoveries: List of discoveries
            patterns: Analyzed patterns
            
        Returns:
            Recommendations as markdown string
        """
        recommendations = []
        
        if len(discoveries) > 0:
            # Pattern-based recommendations
            if patterns["elements"]:
                top_element = max(patterns["elements"].items(), key=lambda x: x[1])[0]
                recommendations.append(f"- Continue exploring {top_element}-based materials")
            
            if patterns["applications"]:
                top_app = max(patterns["applications"].items(), key=lambda x: x[1])[0]
                recommendations.append(f"- Focus on {top_app} applications")
        
        # General recommendations
        recommendations.extend([
            "- Validate promising candidates with experimental data",
            "- Consider scaling up synthesis for top materials",
            "- Review literature for similar materials"
        ])
        
        return "\n".join(recommendations)
    
    def _save_insights(self, insights: str) -> None:
        """
        Save insights to the insights file.
        
        Args:
            insights: Insights content to save
        """
        try:
            # Read existing insights
            existing_content = ""
            if self.insights_file.exists():
                with open(self.insights_file, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            
            # Prepend new insights
            updated_content = insights + "\n\n" + existing_content
            
            # Keep only last 4 weeks (4 entries)
            sections = updated_content.split("# Weekly Materials Insights")
            if len(sections) > 5:  # Keep header + 4 weeks
                sections = sections[:5]
                updated_content = "# Weekly Materials Insights".join(sections)
            
            # Save updated content
            with open(self.insights_file, "w", encoding="utf-8") as f:
                f.write(updated_content)
                
            logger.info(f"Saved insights to {self.insights_file}")
            
        except OSError as e:
            logger.error(f"Failed to save insights: {e}")
    
    def read_insights(self) -> str:
        """
        Read current insights file.
        
        Returns:
            Insights content as string
        """
        try:
            if self.insights_file.exists():
                with open(self.insights_file, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                return "No insights available yet. Generate weekly summary first."
        except OSError as e:
            logger.error(f"Failed to read insights: {e}")
            return ""
    
    def get_context_summary(self) -> str:
        """
        Get a context summary for the agent.
        
        Returns:
            Context summary string
        """
        insights = self.read_insights()
        
        # Extract key points from insights
        lines = insights.split('\n')
        key_points = []
        
        for line in lines:
            if line.startswith("## Key Discoveries") or line.startswith("## Research Patterns"):
                # Skip section headers
                continue
            elif line.startswith("- ") or line.startswith("**"):
                key_points.append(line.strip())
                if len(key_points) >= 5:  # Limit to top 5 points
                    break
        
        if key_points:
            return "**Recent Research Context:**\n" + "\n".join(key_points)
        else:
            return "No recent research context available."
    
    def should_generate_summary(self) -> bool:
        """
        Check if a new summary should be generated.
        
        Returns:
            True if summary should be generated, False otherwise
        """
        if not self.insights_file.exists():
            return True
        
        try:
            # Check file modification time
            mod_time = datetime.fromtimestamp(self.insights_file.stat().st_mtime)
            days_since_update = (datetime.now() - mod_time).days
            
            # Generate if more than 7 days since last update
            return days_since_update >= 7
            
        except OSError:
            return True
    
    def auto_generate_if_needed(self) -> Optional[str]:
        """
        Auto-generate summary if needed.
        
        Returns:
            Generated summary if created, None otherwise
        """
        if self.should_generate_summary():
            logger.info("Auto-generating weekly summary")
            return self.generate_weekly_summary()
        else:
            logger.debug("Weekly summary not needed yet")
            return None 