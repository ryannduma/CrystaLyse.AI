# crystalyse_memory/tools/scratchpad_tools.py
"""
Scratchpad Tools for CrystaLyse.AI Memory System

Provides function tools for OpenAI Agents SDK to interact with agent scratchpad.
Enables transparent reasoning and planning capabilities.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def write_to_scratchpad(
    content: str,
    section: str = "reasoning",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Write reasoning, plans, or progress to the agent's scratchpad.
    
    Use this tool to document your thought process, create plans, track progress,
    or note observations during complex multi-step queries.
    
    Args:
        content: What to write to the scratchpad
        section: Type of content:
            - "plan": Current approach/strategy
            - "reasoning": Thought process and analysis
            - "progress": What has been accomplished
            - "tools_used": Tools used and their results
            - "observation": What you observed from tool results
            - "thought": General thoughts
            - "analysis": Data analysis and insights
            - "conclusion": Final conclusions
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.write_to_scratchpad(content, section)
        
        return f"✅ Written to scratchpad ({section}): {content[:50]}{'...' if len(content) > 50 else ''}"
        
    except Exception as e:
        logger.error(f"write_to_scratchpad error: {e}")
        return f"Error writing to scratchpad: {str(e)}"


def read_scratchpad(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Read current scratchpad contents to review reasoning and plans.
    
    Use this tool to review what you've written previously, check your
    current plan, or maintain context in complex queries.
    
    Returns:
        Current scratchpad contents
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        content = dual_memory.read_scratchpad()
        
        if not content.strip():
            return "📝 Scratchpad is empty"
        
        return f"📖 Current scratchpad contents:\n\n{content}"
        
    except Exception as e:
        logger.error(f"read_scratchpad error: {e}")
        return f"Error reading scratchpad: {str(e)}"


def update_plan(
    new_plan: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Update the current plan, replacing any existing plan.
    
    Use this tool when you need to revise your approach based on
    new information or when starting a complex multi-step query.
    
    Args:
        new_plan: New plan to solve the current query
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.update_plan(new_plan)
        
        return f"🎯 Plan updated: {new_plan[:50]}{'...' if len(new_plan) > 50 else ''}"
        
    except Exception as e:
        logger.error(f"update_plan error: {e}")
        return f"Error updating plan: {str(e)}"


def get_current_plan(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the current plan from the scratchpad.
    
    Use this tool to check what plan is currently active.
    
    Returns:
        Current plan or message if no plan exists
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        plan = dual_memory.get_current_plan()
        
        if plan:
            return f"🎯 Current plan:\n{plan}"
        else:
            return "📝 No current plan set"
        
    except Exception as e:
        logger.error(f"get_current_plan error: {e}")
        return f"Error getting current plan: {str(e)}"


def erase_scratchpad_section(
    section: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Erase a specific section from the scratchpad.
    
    Use this tool to remove outdated reasoning, old plans, or
    irrelevant observations.
    
    Args:
        section: Section to erase:
            - "plan": Remove current plan
            - "reasoning": Remove reasoning steps
            - "progress": Remove progress updates
            - "tools_used": Remove tool usage logs
            - "observation": Remove observations
            - "thought": Remove thoughts
            - "analysis": Remove analysis
            - "conclusion": Remove conclusions
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.erase_scratchpad_section(section)
        
        return f"🗑️ Erased section: {section}"
        
    except Exception as e:
        logger.error(f"erase_scratchpad_section error: {e}")
        return f"Error erasing section: {str(e)}"


def clear_scratchpad(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Completely clear the scratchpad to start fresh.
    
    Use this tool when you want to start over with a clean
    reasoning workspace.
    
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.clear_scratchpad()
        
        return "🧹 Scratchpad cleared - starting fresh"
        
    except Exception as e:
        logger.error(f"clear_scratchpad error: {e}")
        return f"Error clearing scratchpad: {str(e)}"


def log_tool_usage(
    tool_name: str,
    parameters: Dict[str, Any],
    result_summary: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log tool usage with parameters and results to scratchpad.
    
    Use this tool to keep track of what tools you've used and
    their outcomes for complex workflows.
    
    Args:
        tool_name: Name of the tool used
        parameters: Parameters passed to the tool
        result_summary: Brief summary of the result
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.log_tool_usage(tool_name, parameters, result_summary)
        
        return f"📋 Logged tool usage: {tool_name}"
        
    except Exception as e:
        logger.error(f"log_tool_usage error: {e}")
        return f"Error logging tool usage: {str(e)}"


def log_reasoning_step(
    reasoning: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log a reasoning step to the scratchpad.
    
    Use this tool to document your logical thought process
    during complex problem solving.
    
    Args:
        reasoning: Your reasoning or thought process
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.log_reasoning_step(reasoning)
        
        return f"🧠 Logged reasoning: {reasoning[:50]}{'...' if len(reasoning) > 50 else ''}"
        
    except Exception as e:
        logger.error(f"log_reasoning_step error: {e}")
        return f"Error logging reasoning: {str(e)}"


def log_observation(
    observation: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log an observation from tool results.
    
    Use this tool to document what you learned from tool
    outputs or data analysis.
    
    Args:
        observation: What you observed or learned
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.log_observation(observation)
        
        return f"👁️ Logged observation: {observation[:50]}{'...' if len(observation) > 50 else ''}"
        
    except Exception as e:
        logger.error(f"log_observation error: {e}")
        return f"Error logging observation: {str(e)}"


def log_progress(
    progress: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log progress update to the scratchpad.
    
    Use this tool to track what you've accomplished and
    what remains to be done.
    
    Args:
        progress: Progress update description
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.log_progress(progress)
        
        return f"✅ Logged progress: {progress[:50]}{'...' if len(progress) > 50 else ''}"
        
    except Exception as e:
        logger.error(f"log_progress error: {e}")
        return f"Error logging progress: {str(e)}"


def conclude_query(
    conclusion: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log final conclusion to the scratchpad.
    
    Use this tool to document your final answer or conclusion
    after completing a complex query.
    
    Args:
        conclusion: Final conclusion or answer
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        dual_memory.conclude_query(conclusion)
        
        return f"🏁 Logged conclusion: {conclusion[:50]}{'...' if len(conclusion) > 50 else ''}"
        
    except Exception as e:
        logger.error(f"conclude_query error: {e}")
        return f"Error logging conclusion: {str(e)}"


def get_scratchpad_stats(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get statistics about the current scratchpad session.
    
    Use this tool to understand how much reasoning has been
    documented in the current session.
    
    Returns:
        Scratchpad statistics
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No scratchpad available in context"
        
        dual_memory = context["dual_working_memory"]
        stats = dual_memory.get_stats()
        
        scratchpad_stats = stats.get("reasoning_scratchpad", {})
        
        sections = scratchpad_stats.get("section_counts", {})
        total_steps = scratchpad_stats.get("total_steps", 0)
        
        stats_text = f"📊 Scratchpad Statistics:\n"
        stats_text += f"Total reasoning steps: {total_steps}\n"
        
        if sections:
            stats_text += "Sections:\n"
            for section, count in sections.items():
                stats_text += f"  - {section}: {count}\n"
        
        return stats_text
        
    except Exception as e:
        logger.error(f"get_scratchpad_stats error: {e}")
        return f"Error getting scratchpad stats: {str(e)}"


# Tool registry for easy access
SCRATCHPAD_TOOLS = {
    "write_to_scratchpad": write_to_scratchpad,
    "read_scratchpad": read_scratchpad,
    "update_plan": update_plan,
    "get_current_plan": get_current_plan,
    "erase_scratchpad_section": erase_scratchpad_section,
    "clear_scratchpad": clear_scratchpad,
    "log_tool_usage": log_tool_usage,
    "log_reasoning_step": log_reasoning_step,
    "log_observation": log_observation,
    "log_progress": log_progress,
    "conclude_query": conclude_query,
    "get_scratchpad_stats": get_scratchpad_stats
}