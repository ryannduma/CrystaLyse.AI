"""
Memory Tools for Crystalyse Agent

Function tools for OpenAI Agents SDK to interact with the simple memory system.
Provides save_to_memory, search_memory, and discovery caching capabilities.
"""

import logging
from datetime import datetime

try:
    from agents import function_tool
except ImportError:
    # Fallback for testing without agents SDK
    def function_tool(func):
        return func


logger = logging.getLogger(__name__)


@function_tool
def save_to_memory(fact: str, section: str = "Important Notes") -> str:
    """
    Save important information to user memory.

    Use this tool to remember important facts, discoveries, patterns, or
    preferences that should be retained across sessions.

    Args:
        fact: Important fact or information to save
        section: Section to save to (options: "Important Notes", "User Preferences",
                "Recent Discoveries", "Common Patterns")

    Returns:
        Confirmation message
    """
    try:
        # Get memory system from context (will be injected by agent)
        # For now, create a simple fallback with default user
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(save_to_memory, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        memory.save_to_memory(fact, section)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"✓ Saved to memory ({section}): {fact[:50]}{'...' if len(fact) > 50 else ''} [{timestamp}]"

    except Exception as e:
        logger.error(f"save_to_memory error: {e}")
        return f"❌ Failed to save to memory: {str(e)}"


@function_tool
def search_memory(query: str) -> str:
    """
    Search user memory for relevant information.

    Use this tool to find information previously saved in memory, including
    user preferences, past discoveries, and important notes.

    Args:
        query: Search query to find relevant memory entries

    Returns:
        Formatted search results
    """
    try:
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(search_memory, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        results = memory.search_memory(query)

        if results:
            formatted_results = []
            for i, result in enumerate(results[:5], 1):  # Top 5 results
                formatted_results.append(f"{i}. {result}")

            return f"📝 Found {len(results)} memory entries for '{query}':\n" + "\n".join(
                formatted_results
            )
        else:
            return f"🔍 No memory entries found for '{query}'"

    except Exception as e:
        logger.error(f"search_memory error: {e}")
        return f"❌ Failed to search memory: {str(e)}"


@function_tool
def save_discovery(formula: str, properties: str) -> str:
    """
    Save a material discovery to the cache.

    Use this tool to cache expensive computational results (MACE energies,
    Chemeleon structures, SMACT validations) to avoid re-computation.

    Args:
        formula: Chemical formula of the material
        properties: JSON string of material properties and calculations

    Returns:
        Confirmation message
    """
    try:
        import json

        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(save_discovery, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        # Parse properties string as JSON
        properties_dict = json.loads(properties) if isinstance(properties, str) else properties
        memory.save_discovery(formula, properties_dict)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"💾 Cached discovery: {formula} [{timestamp}]"

    except Exception as e:
        logger.error(f"save_discovery error: {e}")
        return f"❌ Failed to cache discovery: {str(e)}"


@function_tool
def search_discoveries(query: str, limit: int = 5) -> str:
    """
    Search cached discoveries for similar materials.

    Use this tool to find previously analyzed materials that might be
    relevant to the current query.

    Args:
        query: Search query for materials
        limit: Maximum number of results to return

    Returns:
        Formatted search results
    """
    try:
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(search_discoveries, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        results = memory.search_discoveries(query, limit)

        if results:
            formatted_results = []
            for i, result in enumerate(results, 1):
                formula = result.get("formula", "Unknown")
                cached_at = result.get("cached_at", "Unknown time")

                # Extract key properties
                properties = result.get("properties", {})
                key_props = []
                if isinstance(properties, dict):
                    for key, value in list(properties.items())[:2]:  # Top 2 properties
                        key_props.append(f"{key}: {value}")

                props_str = ", ".join(key_props) if key_props else "No properties"
                formatted_results.append(f"{i}. {formula} - {props_str} (cached: {cached_at})")

            return f"🔬 Found {len(results)} cached discoveries for '{query}':\n" + "\n".join(
                formatted_results
            )
        else:
            return f"🔍 No cached discoveries found for '{query}'"

    except Exception as e:
        logger.error(f"search_discoveries error: {e}")
        return f"❌ Failed to search discoveries: {str(e)}"


@function_tool
def get_cached_discovery(formula: str) -> str:
    """
    Get cached discovery result for a specific formula.

    Use this tool to check if a material has been previously analyzed
    and avoid re-running expensive calculations.

    Args:
        formula: Chemical formula to look up

    Returns:
        Cached result if available, or indication that no cache exists
    """
    try:
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(get_cached_discovery, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        result = memory.get_cached_discovery(formula)

        if result:
            cached_at = result.get("cached_at", "Unknown time")
            properties = result.get("properties", {})

            # Format properties
            if isinstance(properties, dict):
                prop_lines = []
                for key, value in properties.items():
                    prop_lines.append(f"  - {key}: {value}")
                props_str = "\n".join(prop_lines)
            else:
                props_str = str(properties)

            return f"💾 Cached result for {formula} (cached: {cached_at}):\n{props_str}"
        else:
            return f"🔍 No cached result found for {formula}"

    except Exception as e:
        logger.error(f"get_cached_discovery error: {e}")
        return f"❌ Failed to get cached discovery: {str(e)}"


@function_tool
def get_memory_context() -> str:
    """
    Get comprehensive memory context for the agent.

    Use this tool to get a summary of all memory layers including
    session history, user preferences, and recent discoveries.

    Returns:
        Comprehensive memory context
    """
    try:
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(get_memory_context, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        context = memory.get_context_for_agent()

        return f"📚 Memory Context:\n{context}"

    except Exception as e:
        logger.error(f"get_memory_context error: {e}")
        return f"❌ Failed to get memory context: {str(e)}"


@function_tool
def generate_weekly_summary() -> str:
    """
    Generate a weekly summary of research progress.

    Use this tool to create an automatic summary of discoveries, patterns,
    and research progress from the past week.

    Returns:
        Weekly summary in markdown format
    """
    try:
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(generate_weekly_summary, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        summary = memory.generate_weekly_summary()

        return f"📊 Weekly Research Summary:\n{summary}"

    except Exception as e:
        logger.error(f"generate_weekly_summary error: {e}")
        return f"❌ Failed to generate weekly summary: {str(e)}"


@function_tool
def get_memory_statistics() -> str:
    """
    Get statistics about the memory system.

    Use this tool to check memory usage, cache statistics, and
    system health information.

    Returns:
        Memory system statistics
    """
    try:
        from .crystalyse_memory import CrystaLyseMemory

        # Try to get user_id from global context or use default
        user_id = getattr(get_memory_statistics, "_user_id", "default")
        memory = CrystaLyseMemory(user_id=user_id)
        stats = memory.get_memory_statistics()

        formatted_stats = []
        formatted_stats.append(f"**User ID:** {stats['user_id']}")
        formatted_stats.append(f"**Memory Directory:** {stats['memory_directory']}")
        formatted_stats.append(
            f"**Session Interactions:** {stats['session']['total_interactions']}"
        )
        formatted_stats.append(f"**Cached Discoveries:** {stats['cache']['total_entries']}")
        formatted_stats.append(f"**User Preferences:** {stats['user_preferences']}")
        formatted_stats.append(f"**Research Interests:** {stats['research_interests']}")
        formatted_stats.append(f"**Recent Discoveries:** {stats['recent_discoveries']}")
        formatted_stats.append(f"**Insights Available:** {stats['insights_available']}")

        return "📈 Memory Statistics:\n" + "\n".join(formatted_stats)

    except Exception as e:
        logger.error(f"get_memory_statistics error: {e}")
        return f"❌ Failed to get memory statistics: {str(e)}"


def get_memory_tools(user_id: str = "default") -> list[callable]:
    """
    Get all memory tools for the agent.

    Args:
        user_id: User ID to set context for memory tools

    Returns:
        List of memory tool functions with user context set
    """
    # Set user context on all memory tools
    tools = [
        save_to_memory,
        search_memory,
        save_discovery,
        search_discoveries,
        get_cached_discovery,
        get_memory_context,
        generate_weekly_summary,
        get_memory_statistics,
    ]

    # Set user_id attribute on all tools
    for tool in tools:
        tool._user_id = user_id

    return tools


# Tool metadata for OpenAI Agents SDK
MEMORY_TOOLS_METADATA = {
    "save_to_memory": {
        "description": "Save important information to user memory",
        "parameters": {
            "fact": {"type": "string", "description": "Important fact to save"},
            "section": {
                "type": "string",
                "description": "Section to save to",
                "default": "Important Notes",
            },
        },
    },
    "search_memory": {
        "description": "Search user memory for relevant information",
        "parameters": {"query": {"type": "string", "description": "Search query"}},
    },
    "save_discovery": {
        "description": "Save a material discovery to the cache",
        "parameters": {
            "formula": {"type": "string", "description": "Chemical formula"},
            "properties": {"type": "object", "description": "Material properties dictionary"},
        },
    },
    "search_discoveries": {
        "description": "Search cached discoveries for similar materials",
        "parameters": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Maximum results", "default": 5},
        },
    },
    "get_cached_discovery": {
        "description": "Get cached discovery result for a specific formula",
        "parameters": {"formula": {"type": "string", "description": "Chemical formula to look up"}},
    },
    "get_memory_context": {
        "description": "Get comprehensive memory context for the agent",
        "parameters": {},
    },
    "generate_weekly_summary": {
        "description": "Generate a weekly summary of research progress",
        "parameters": {},
    },
    "get_memory_statistics": {
        "description": "Get statistics about the memory system",
        "parameters": {},
    },
}
