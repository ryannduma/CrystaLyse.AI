"""
Mode Injection System for CrystaLyse.AI

Automatically injects the correct mode parameter into tool calls,
eliminating the need to rely on the agent following instructions.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class ModeInjectingToolWrapper:
    """
    Wraps tools to automatically inject the mode parameter for specific functions.
    This ensures the correct mode is always used regardless of what the agent passes.
    """

    def __init__(self, original_tool: Callable, current_mode: str, tool_name: str):
        self.original_tool = original_tool
        self.current_mode = current_mode
        self.tool_name = tool_name

        # Tools that need mode injection
        self.mode_required_tools = {
            "comprehensive_materials_analysis",
            "chemistry_creative_analysis",
            "materials_discovery_pipeline",
            "advanced_materials_analysis",
        }

    async def __call__(self, *args, **kwargs):
        """
        Intercept tool calls and inject mode parameter if needed.
        """
        # Check if this tool needs mode injection
        if self.tool_name in self.mode_required_tools or "analysis" in self.tool_name.lower():
            # Always inject the current mode, overriding any agent-provided mode
            if "mode" in kwargs:
                original_mode = kwargs["mode"]
                if original_mode != self.current_mode:
                    logger.info(
                        f"Mode injection: Overriding agent mode '{original_mode}' with current mode '{self.current_mode}' for {self.tool_name}"
                    )
            else:
                logger.info(
                    f"Mode injection: Adding mode '{self.current_mode}' to {self.tool_name}"
                )

            kwargs["mode"] = self.current_mode

        # Call the original tool
        try:
            result = await self.original_tool(*args, **kwargs)
            logger.debug(f"Tool {self.tool_name} completed with mode={self.current_mode}")
            return result
        except Exception as e:
            logger.error(f"Tool {self.tool_name} failed with mode={self.current_mode}: {e}")
            raise


class GlobalModeManager:
    """
    Global singleton to manage the current mode across all tool calls.
    This ensures consistent mode usage throughout the session.
    """

    _instance = None
    _current_mode = "adaptive"
    _mode_locked = False  # When True, prevents dynamic mode changes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_mode(cls, mode: str, lock_mode: bool = True):
        """
        Set the global mode and optionally lock it to prevent dynamic changes.

        Args:
            mode: The mode to set ("creative", "adaptive", "rigorous")
            lock_mode: If True, prevents dynamic mode switching
        """
        valid_modes = ["creative", "adaptive", "rigorous"]
        if mode not in valid_modes:
            logger.warning(f"Invalid mode '{mode}', keeping current mode '{cls._current_mode}'")
            return

        old_mode = cls._current_mode
        cls._current_mode = mode
        cls._mode_locked = lock_mode

        logger.info(f"Global mode changed: {old_mode} -> {mode} (locked={lock_mode})")

    @classmethod
    def get_mode(cls) -> str:
        """Get the current global mode."""
        return cls._current_mode

    @classmethod
    def is_locked(cls) -> bool:
        """Check if mode is locked against dynamic changes."""
        return cls._mode_locked

    @classmethod
    def unlock_mode(cls):
        """Unlock mode to allow dynamic changes."""
        cls._mode_locked = False
        logger.info("Mode unlocked - dynamic switching enabled")


def inject_mode_into_mcp_servers(mcp_servers: list[Any], current_mode: str) -> list[Any]:
    """
    Inject mode into MCP server tools.

    This is a more advanced approach that would require modifying the MCP server
    integration, but provides the most robust solution.
    """
    # Set the global mode
    GlobalModeManager.set_mode(current_mode, lock_mode=True)

    logger.info(
        f"Mode injection configured for {len(mcp_servers)} MCP servers with mode='{current_mode}'"
    )

    # For now, we rely on the global mode manager
    # In the future, we could wrap individual MCP server tools here
    return mcp_servers


def create_mode_aware_instructions(base_instructions: str, mode: str) -> str:
    """
    Create instructions that emphasize the REQUIRED mode parameter with enforcement.
    """
    mode_enforcement = f"""

## CRITICAL MODE ENFORCEMENT - THIS OVERRIDES ALL OTHER INSTRUCTIONS

THE CURRENT SESSION MODE IS: {mode.upper()}

**MANDATORY RULE**: You MUST ALWAYS pass mode="{mode}" to ALL analysis tools.

**CRITICAL TOOLS THAT REQUIRE MODE**:
- comprehensive_materials_analysis(mode="{mode}", ...)
- chemistry_creative_analysis(mode="{mode}", ...)
- materials_discovery_pipeline(mode="{mode}", ...)

**MODE ENFORCEMENT SYSTEM ACTIVE**:
- Mode parameter will be automatically injected if missing
- Any other mode you pass will be overridden to "{mode}"
- This ensures 100% consistency with user's selected mode

**YOUR TASK**: Focus on the analysis, not the mode parameter - it's handled automatically.

"""

    return base_instructions + mode_enforcement


class DynamicModeSuppressor:
    """
    Suppresses dynamic mode switching when mode is explicitly set.
    """

    @staticmethod
    def should_suppress_dynamic_switching() -> bool:
        """Check if dynamic mode switching should be suppressed."""
        return GlobalModeManager.is_locked()

    @staticmethod
    def log_suppressed_switch(attempted_mode: str, reason: str):
        """Log when a dynamic mode switch is suppressed."""
        current_mode = GlobalModeManager.get_mode()
        logger.info(
            f"Dynamic mode switch suppressed: {current_mode} -> {attempted_mode} (reason: {reason}) - Mode is locked"
        )
