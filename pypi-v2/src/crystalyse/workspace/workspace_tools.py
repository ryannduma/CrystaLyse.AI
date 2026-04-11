"""
Tools for the agent to interact with the local file system workspace and the user.
"""

from typing import Callable, List, Optional, Dict, Any
from pathlib import Path
from agents import function_tool
from pydantic import BaseModel, Field

from .materials_workspace import MaterialsWorkspace
from dataclasses import dataclass


# --- Placeholder Callbacks ---
# These are replaced by the CLI at runtime to connect the tools to the UI.

def _default_approval_callback(path: Path, content: str) -> bool:
    print(f"WARNING: Approval callback not implemented. Auto-approving write to {path}.")
    return True

async def _default_clarification_callback(request: 'ClarificationRequest') -> Dict[str, Any]:
    print("WARNING: Clarification callback not implemented. Returning empty answers.")
    return {}

APPROVAL_CALLBACK: Callable[[Path, str], bool] = _default_approval_callback
CLARIFICATION_CALLBACK: Callable[['ClarificationRequest'], Any] = _default_clarification_callback


# --- Pydantic Models for Structured Tool Input ---

class Question(BaseModel):
    """A single, structured question to ask the user."""
    id: str = Field(..., description="A unique identifier for the question (e.g., 'application_type').")
    text: str = Field(..., description="The question to ask the user (e.g., 'What is the primary application?').")
    options: Optional[List[str]] = Field(None, description="A list of options for the user to choose from, if applicable.")

class ClarificationRequest(BaseModel):
    """A request for clarification from the user, containing one or more questions."""
    questions: List[Question]

@dataclass
class QueryAnalysis:
    """Analysis of user query for mode selection"""
    expertise_level: str  # novice, intermediate, expert
    specificity_score: float  # 0.0 to 1.0
    urgency_indicators: List[str]
    complexity_factors: Dict[str, bool]
    domain_confidence: float  # 0.0 to 1.0
    interaction_style: str  # exploratory, validation, synthesis

# --- Tool Implementation ---

def get_workspace_for_project(project_name: str) -> MaterialsWorkspace:
    """Factory function to create a workspace instance for a given project."""
    return MaterialsWorkspace(
        project_name=project_name,
        approval_callback=APPROVAL_CALLBACK
    )

@function_tool
def read_file(project_name: str, relative_path: str) -> str:
    """
    Reads the content of a file from the specified project workspace.
    Use this to retrieve data, review previous results, or read generated code.

    :param project_name: The name of the project workspace.
    :param relative_path: The path to the file relative to the project root.
    :return: The content of the file as a string, or an error message.
    """
    workspace = get_workspace_for_project(project_name)
    return workspace.read_file(relative_path)

@function_tool
def write_file(project_name: str, relative_path: str, content: str) -> str:
    """
    Writes content to a file in the specified project workspace. This action
    requires user approval. Use it to save results, create reports, or generate code.

    :param project_name: The name of the project workspace.
    :param relative_path: The path to the file relative to the project root.
    :param content: The content to write to the file.
    :return: A message indicating success, user denial, or an error.
    """
    workspace = get_workspace_for_project(project_name)
    return workspace.write_file(relative_path, content)

@function_tool
def list_files(project_name: str, relative_path: str = ".") -> str:
    """
    Lists the files and directories within a specified path in the project workspace.

    :param project_name: The name of the project workspace.
    :param relative_path: The path to the directory relative to the project root.
    :return: A tree-like string representation of the directory contents.
    """
    workspace = get_workspace_for_project(project_name)
    return workspace.list_files(relative_path)