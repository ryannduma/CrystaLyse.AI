"""
Tools for the agent to interact with the local file system workspace and the user.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents import function_tool
from pydantic import BaseModel, Field

from .materials_workspace import MaterialsWorkspace

# --- Placeholder Callbacks ---
# These are replaced by the CLI at runtime to connect the tools to the UI.


def _default_approval_callback(path: Path, content: str) -> bool:
    print(f"WARNING: Approval callback not implemented. Auto-approving write to {path}.")
    return True


async def _default_clarification_callback(request: "ClarificationRequest") -> dict[str, Any]:
    print("WARNING: Clarification callback not implemented. Returning empty answers.")
    return {}


APPROVAL_CALLBACK: Callable[[Path, str], bool] = _default_approval_callback
CLARIFICATION_CALLBACK: Callable[["ClarificationRequest"], Any] = _default_clarification_callback


# --- Pydantic Models for Structured Tool Input ---


class Question(BaseModel):
    """A single, structured question to ask the user."""

    id: str = Field(
        ..., description="A unique identifier for the question (e.g., 'application_type')."
    )
    text: str = Field(
        ..., description="The question to ask the user (e.g., 'What is the primary application?')."
    )
    options: list[str] | None = Field(
        None, description="A list of options for the user to choose from, if applicable."
    )


class ClarificationRequest(BaseModel):
    """A request for clarification from the user, containing one or more questions."""

    questions: list[Question]


@dataclass
class QueryAnalysis:
    """Analysis of user query for mode selection"""

    expertise_level: str  # novice, intermediate, expert
    specificity_score: float  # 0.0 to 1.0
    urgency_indicators: list[str]
    complexity_factors: dict[str, bool]
    domain_confidence: float  # 0.0 to 1.0
    interaction_style: str  # exploratory, validation, synthesis


# --- Tool Implementation ---


def get_workspace_for_project(project_name: str) -> MaterialsWorkspace:
    """Factory function to create a workspace instance for a given project."""
    return MaterialsWorkspace(project_name=project_name, approval_callback=APPROVAL_CALLBACK)


@function_tool
async def request_user_clarification(questions: list[Question]) -> str:
    """
    When a user's query is too broad or ambiguous, use this tool to ask clarifying
    questions. This will pause your execution and prompt the user for more
    information. The user's answers will be provided back to you to continue your task.

    :param questions: A list of questions to ask the user. Each question should have an id,
                      text, and optional list of choices.
    :return: A JSON string containing the user's answers, keyed by question id.
    """
    request = ClarificationRequest(questions=questions)

    # Handle both sync and async callbacks
    callback = CLARIFICATION_CALLBACK
    if callable(callback):
        import inspect

        if inspect.iscoroutinefunction(callback):
            answers = await callback(request)
        else:
            answers = callback(request)
    else:
        answers = await callback(request)

    # Extract full context and structured answers for the main agent
    full_context = answers.get("_full_context", "")
    interpretation_method = answers.get("_interpretation_method", "unknown")

    # Remove metadata from structured answers
    structured_answers = {k: v for k, v in answers.items() if not k.startswith("_")}

    # Create comprehensive response for the main agent
    result = {
        "structured_answers": structured_answers,
        "interpretation_method": interpretation_method,
    }

    if full_context:
        result["full_user_context"] = full_context
        response_text = f'User provided clarifications with comprehensive context.\n\nStructured answers: {json.dumps(structured_answers)}\n\nFull user context: "{full_context}"\n\nInterpretation method: {interpretation_method}'
    else:
        response_text = (
            f"User provided the following clarifications: {json.dumps(structured_answers)}"
        )

    return response_text


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


@function_tool
def extract_and_save_cif_from_structures(
    project_name: str,
    structures_result: str,
    filename: str = "structure.cif",
    sample_index: int = 0,
) -> str:
    """
    Extract CIF data from structure generation results and save to a file.

    Use this when the user wants to save generated structures to CIF files.
    The structures_result should be the JSON output from generate_structures tool.

    :param project_name: The name of the project workspace.
    :param structures_result: JSON string containing structure generation results.
    :param filename: Name for the output CIF file (default: structure.cif).
    :param sample_index: Which structure sample to extract (default: 0 for most stable).
    :return: Success message or error description.
    """
    try:
        import json

        # Parse the structures result
        if isinstance(structures_result, str):
            # Handle the case where it might be wrapped in a text field
            if structures_result.startswith('{"type": "text"'):
                result_data = json.loads(structures_result)
                if "text" in result_data:
                    actual_data = json.loads(result_data["text"])
                else:
                    actual_data = result_data
            else:
                actual_data = json.loads(structures_result)
        else:
            actual_data = structures_result

        # Extract CIF from the specified sample
        if "structures" in actual_data and len(actual_data["structures"]) > sample_index:
            structure = actual_data["structures"][sample_index]

            # Check if CIF is available
            if "cif" in structure:
                cif_content = structure["cif"]
            elif "structure" in structure and isinstance(structure["structure"], dict):
                # Generate CIF from structure data if direct CIF not available
                struct_data = structure["structure"]
                formula = structure.get("formula", "Unknown")

                # Create a basic CIF from the structure data
                cif_content = f"""data_{formula}_sample{sample_index}
_chemical_formula_structural  {formula}
_chemical_formula_sum         "{formula}"

# Cell parameters from structure data
"""
                if "cell" in struct_data:
                    cell = struct_data["cell"]
                    if len(cell) >= 3 and len(cell[0]) >= 3:
                        # Calculate cell parameters from cell matrix
                        import numpy as np

                        cell_matrix = np.array(cell)
                        a = np.linalg.norm(cell_matrix[0])
                        b = np.linalg.norm(cell_matrix[1])
                        c = np.linalg.norm(cell_matrix[2])

                        alpha = (
                            np.arccos(np.dot(cell_matrix[1], cell_matrix[2]) / (b * c))
                            * 180
                            / np.pi
                        )
                        beta = (
                            np.arccos(np.dot(cell_matrix[0], cell_matrix[2]) / (a * c))
                            * 180
                            / np.pi
                        )
                        gamma = (
                            np.arccos(np.dot(cell_matrix[0], cell_matrix[1]) / (a * b))
                            * 180
                            / np.pi
                        )

                        cif_content += f"""_cell_length_a       {a:.6f}
_cell_length_b       {b:.6f}
_cell_length_c       {c:.6f}
_cell_angle_alpha    {alpha:.6f}
_cell_angle_beta     {beta:.6f}
_cell_angle_gamma    {gamma:.6f}
_space_group_name_H-M_alt    "P 1"
_space_group_IT_number       1

loop_
  _atom_site_type_symbol
  _atom_site_label
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  _atom_site_occupancy
"""
                        # Add atomic positions if available
                        if "positions" in struct_data and "species" in struct_data:
                            positions = struct_data["positions"]
                            species = struct_data["species"]

                            # Convert Cartesian to fractional coordinates
                            inv_cell = np.linalg.inv(cell_matrix)

                            for i, (pos, symbol) in enumerate(
                                zip(positions, species, strict=False)
                            ):
                                frac_pos = np.dot(inv_cell, pos)
                                cif_content += f"  {symbol}  {symbol}{i + 1}   {frac_pos[0]:.6f}  {frac_pos[1]:.6f}  {frac_pos[2]:.6f}  1.0\n"

            else:
                return f"Error: No CIF data or structure information found in sample {sample_index}"

            # Save the CIF file
            workspace = get_workspace_for_project(project_name)
            result = workspace.write_file(filename, cif_content)

            if "successfully" in result.lower():
                return f"Successfully extracted and saved CIF data for {structure.get('formula', 'structure')} (sample {sample_index}) to {filename}"
            else:
                return f"Error saving CIF file: {result}"

        else:
            return f"Error: Sample {sample_index} not found in structures result. Available samples: {len(actual_data.get('structures', []))}"

    except json.JSONDecodeError as e:
        return f"Error parsing structures result JSON: {e}"
    except Exception as e:
        return f"Error extracting CIF data: {e}"
