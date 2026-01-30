"""
Materials Agent - Core agent for Crystalyse V2.

This module provides the main MaterialsAgent class that uses a skills-based
architecture instead of MCP servers. Skills provide procedural knowledge
through SKILL.md files, with scripts executable via subprocess.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

try:
    from agents import Agent, Runner
    from agents.items import ItemHelpers
    from agents.model_settings import ModelSettings
    from agents.models.openai_provider import OpenAIProvider
    from agents.run import RunConfig

    SDK_AVAILABLE = True
except ImportError as e:
    SDK_AVAILABLE = False
    logging.warning(f"OpenAI Agents SDK not available: {e}")

from ..config import Config
from ..skills.injector import SkillInjector
from ..skills.loader import SkillLoader
from ..skills.registry import SkillRegistry
from ..workspace import workspace_tools

logger = logging.getLogger(__name__)

# Model configuration
CREATIVE_MODEL = "gpt-5-mini"  # Fast, cost-efficient ($0.25/$2 per 1M tokens)
RIGOROUS_MODEL = "gpt-5.2"  # Flagship for coding/agentic tasks ($1.75/$14 per 1M tokens)


class MaterialsAgent:
    """
    Skills-based materials discovery agent.

    This agent uses skills (SKILL.md files with scripts) instead of MCP servers
    for tool execution. Two modes are supported:

    - creative (default): Uses gpt-5-mini for fast exploration
    - rigorous: Uses gpt-5.2 for thorough, validated analysis

    The mode is controlled via the --rigorous flag in the CLI.
    """

    def __init__(
        self,
        rigorous: bool = False,
        config: Config | None = None,
        project_name: str = "crystalyse_session",
    ):
        """
        Initialize the MaterialsAgent.

        Args:
            rigorous: If True, use gpt-5.2 model for thorough analysis.
                      If False (default), use gpt-5-mini for fast exploration.
            config: Configuration object. If None, loads from defaults.
            project_name: Name for this session/project.
        """
        self.rigorous = rigorous
        self.model = RIGOROUS_MODEL if rigorous else CREATIVE_MODEL
        self.config = config or Config.load()
        self.project_name = project_name

        # Initialize skills infrastructure
        self.skill_loader = SkillLoader(
            project_root=self.config.base_dir.parent,
            package_skills_dir=self._find_skills_dir(),
        )
        self.skill_registry = SkillRegistry(self.skill_loader)
        self.skill_injector = SkillInjector(
            loader=self.skill_loader,
            registry=self.skill_registry,
        )

        # Load skills
        self._load_skills()

        # Create tools list
        self.tools = self._create_tools()

        logger.info(
            f"MaterialsAgent initialized: model={self.model}, "
            f"rigorous={rigorous}, skills_loaded={len(self.skill_registry.get_skill_names())}"
        )

    def _find_skills_dir(self) -> Path | None:
        """Find the skills directory."""
        possible_paths = [
            self.config.base_dir.parent / "skills",  # dev/skills/
            self.config.base_dir / "skills",  # dev/crystalyse/skills/
            Path(__file__).parent.parent.parent / "skills",  # relative to this file
        ]

        for path in possible_paths:
            if path.exists():
                logger.debug(f"Found skills directory: {path}")
                return path

        logger.warning("No skills directory found")
        return None

    def _load_skills(self) -> None:
        """Load all available skills."""
        outcome = self.skill_loader.load_skills()

        if outcome.errors:
            for error in outcome.errors:
                logger.warning(f"Skill load error: {error}")

        if outcome.warnings:
            for warning in outcome.warnings:
                logger.debug(f"Skill load warning: {warning}")

        logger.info(f"Loaded {outcome.total_loaded} skills")

    def _create_tools(self) -> list:
        """Create the list of tools available to the agent."""
        tools = []

        # Built-in workspace tools
        tools.extend(
            [
                workspace_tools.read_file,
                workspace_tools.write_file,
                workspace_tools.list_files,
            ]
        )

        # Import skill executor tool
        try:
            from ..skills.executor import execute_skill_script

            tools.append(execute_skill_script)
            logger.debug("Added skill executor tool")
        except ImportError as e:
            logger.warning(f"Could not import skill executor: {e}")

        # Import new tools
        try:
            from ..tools.shell import run_shell_command

            tools.append(run_shell_command)
            logger.debug("Added shell tool")
        except ImportError as e:
            logger.debug(f"Shell tool not available: {e}")

        try:
            from ..tools.code_runner import execute_python

            tools.append(execute_python)
            logger.debug("Added code runner tool")
        except ImportError as e:
            logger.debug(f"Code runner tool not available: {e}")

        try:
            from ..tools.optimade import query_optimade

            tools.append(query_optimade)
            logger.debug("Added OPTIMADE tool")
        except ImportError as e:
            logger.debug(f"OPTIMADE tool not available: {e}")

        try:
            from ..tools.web_search import web_search

            tools.append(web_search)
            logger.debug("Added web search tool")
        except ImportError as e:
            logger.debug(f"Web search tool not available: {e}")

        # Artifact tools for session management
        try:
            from ..tools.artifacts import list_artifacts, read_artifact, write_artifact

            tools.extend([write_artifact, read_artifact, list_artifacts])
            logger.debug("Added artifact tools")
        except ImportError as e:
            logger.debug(f"Artifact tools not available: {e}")

        return tools

    def _create_instructions(self) -> str:
        """Create the system instructions for the agent."""
        # Load base prompt
        try:
            prompt_path = self.config.base_dir / "prompts" / "lead_agent_prompt.md"
            with open(prompt_path) as f:
                base_instructions = f.read()
        except Exception as e:
            logger.warning(f"Could not load unified prompt: {e}, using fallback")
            base_instructions = """You are CrystaLyse, an advanced autonomous materials discovery agent.

You help researchers discover and analyze inorganic materials using:
- SMACT validation for composition feasibility
- Chemeleon for crystal structure prediction
- MACE for energy calculations
- PyMatgen for thermodynamic analysis

Always validate materials before detailed analysis. Report your findings clearly."""

        # Add mode-specific context
        mode_context = self._get_mode_context()
        instructions = f"{base_instructions}\n\n{mode_context}"

        # Inject skills section
        instructions = self.skill_injector.inject_into_instructions(
            instructions,
            position="end",
        )

        return instructions

    def _get_mode_context(self) -> str:
        """Get mode-specific context for the agent instructions."""
        if self.rigorous:
            return """## Rigorous Mode Active

You are operating in RIGOROUS mode. This means:
- Use comprehensive validation at every step
- Perform full thermodynamic analysis including phase diagrams
- Check stability against all competing phases
- Provide detailed uncertainty estimates
- Cross-validate results using multiple methods
- Take time to ensure accuracy over speed"""
        else:
            return """## Creative Mode Active

You are operating in CREATIVE mode. This means:
- Focus on rapid exploration and novel possibilities
- Use fast ML predictions (MACE, Chemeleon)
- Prioritize breadth over exhaustive validation
- Report promising candidates quickly
- Skip detailed phase diagram analysis unless specifically requested
- Optimize for discovery speed"""

    async def query(
        self,
        prompt: str,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Process a query and return the result.

        Args:
            prompt: The user's query/request.
            timeout: Optional timeout in seconds. Defaults based on mode.

        Returns:
            Dictionary with status, response, and metadata.
        """
        if not SDK_AVAILABLE:
            return {
                "status": "failed",
                "error": "OpenAI Agents SDK is not installed.",
            }

        # Set timeout based on mode
        if timeout is None:
            timeout = 300 if self.rigorous else 120

        try:
            # Create the agent
            instructions = self._create_instructions()

            sdk_agent = Agent(
                name="CrystaLyse",
                model=self.model,
                instructions=instructions,
                tools=self.tools,
                model_settings=ModelSettings(tool_choice="auto"),
            )

            # Create run config with API key
            run_config = self._create_run_config()

            # Run the agent
            final_response = "No response generated."

            async with asyncio.timeout(timeout):
                result = Runner.run_streamed(
                    starting_agent=sdk_agent,
                    input=prompt,
                    max_turns=100,
                    run_config=run_config,
                )

                message_outputs = []
                async for event in result.stream_events():
                    # Capture message outputs
                    if hasattr(event, "item") and hasattr(event.item, "type"):
                        if event.item.type == "message_output_item":
                            text = ItemHelpers.text_message_output(event.item)
                            if text:
                                message_outputs.append(text)
                                final_response = text

                # Try to get final output
                try:
                    final_result = await result
                    if hasattr(final_result, "final_output") and final_result.final_output:
                        final_response = final_result.final_output
                except Exception as e:
                    logger.debug(f"Could not extract final result: {e}")

            return {
                "status": "completed",
                "query": prompt,
                "response": final_response,
                "model": self.model,
                "mode": "rigorous" if self.rigorous else "creative",
            }

        except TimeoutError:
            logger.error(f"Query timed out after {timeout} seconds")
            return {
                "status": "failed",
                "error": f"The operation timed out after {timeout} seconds.",
                "query": prompt,
            }
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "query": prompt,
            }

    def _create_run_config(self) -> RunConfig | None:
        """Create a RunConfig with the API key."""
        try:
            import time

            trace_timestamp = int(time.time())
            trace_id = f"trace_crystalyse_{self.project_name}_{trace_timestamp}"

            mdg_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
            if mdg_api_key:
                model_provider = OpenAIProvider(api_key=mdg_api_key)
                return RunConfig(trace_id=trace_id, model_provider=model_provider)
            else:
                return RunConfig(trace_id=trace_id)
        except (ImportError, TypeError) as e:
            logger.warning(f"Could not create RunConfig: {e}")
            return None

    def get_available_skills(self) -> list[str]:
        """Get list of available skill names."""
        return self.skill_registry.get_skill_names()

    def get_skill_info(self, skill_name: str) -> dict[str, Any] | None:
        """Get information about a specific skill."""
        skill = self.skill_loader.get_skill(skill_name)
        if skill is None:
            return None

        return {
            "name": skill.name,
            "description": skill.description,
            "path": str(skill.path),
            "scope": skill.scope.value,
            "tags": skill.tags,
        }


# Backwards compatibility alias
EnhancedCrystaLyseAgent = MaterialsAgent
