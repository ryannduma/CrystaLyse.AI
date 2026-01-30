"""Artifact tools for Crystalyse.

Provides write_artifact and read_artifact tools for managing session artifacts.
Artifacts are used to store intermediate results, provenance data, and full
outputs that are too large to include in agent responses.

This follows the pattern from the V2 architecture where workers write full data
to artifacts and return summaries to the lead agent.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from agents import function_tool

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

    def function_tool(func):
        return func


logger = logging.getLogger(__name__)

# Default session directory
DEFAULT_SESSION_DIR = Path.cwd() / "session"


def _get_session_dir() -> Path:
    """Get or create the session directory."""
    session_dir = DEFAULT_SESSION_DIR
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _ensure_parent_dir(path: Path) -> None:
    """Ensure the parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


@function_tool
def write_artifact(
    filename: str,
    content: str,
    artifact_type: str = "json",
) -> dict:
    """Write data to a session artifact file.

    Use this tool to save intermediate results, full query outputs, or any
    data that should be persisted for later reference or provenance.

    Artifacts are stored in the /session/ directory and can be referenced
    in reports by their path.

    Common artifact types:
    - json: Structured data (query results, computations)
    - cif: Crystal structure files
    - txt: Plain text (logs, notes)
    - csv: Tabular data

    Args:
        filename: Name of the artifact file (e.g., "optimade_results.json")
        content: Content to write to the file (JSON string for .json files)
        artifact_type: Type hint for the artifact (json, cif, txt, csv)

    Returns:
        Dictionary with:
        - success: True if write succeeded
        - path: Full path to the artifact
        - error: Error message if write failed

    Example:
        write_artifact(
            filename="ba_sn_o_phases.json",
            content='{"phases": [...], "count": 12}',
            artifact_type="json"
        )
    """
    try:
        session_dir = _get_session_dir()
        artifact_path = session_dir / filename

        # Ensure parent directories exist (for nested paths like structures/foo.cif)
        _ensure_parent_dir(artifact_path)

        # Validate JSON if artifact_type is json
        if artifact_type == "json":
            try:
                # Parse and re-serialize to ensure valid JSON
                data = json.loads(content)
                content = json.dumps(data, indent=2)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "path": str(artifact_path),
                    "error": f"Invalid JSON content: {e}",
                }

        # Write the content
        with open(artifact_path, "w") as f:
            f.write(content)

        logger.info(f"Wrote artifact: {artifact_path}")

        return {
            "success": True,
            "path": str(artifact_path),
            "size": len(content),
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to write artifact {filename}: {e}")
        return {
            "success": False,
            "path": str(DEFAULT_SESSION_DIR / filename),
            "error": str(e),
        }


@function_tool
def read_artifact(
    filename: str,
    parse_json: bool = True,
) -> dict:
    """Read data from a session artifact file.

    Use this tool to load previously saved artifacts for reference or
    to include in provenance tables.

    Args:
        filename: Name of the artifact file to read
        parse_json: If True, attempt to parse JSON files (default: True)

    Returns:
        Dictionary with:
        - success: True if read succeeded
        - content: File content (parsed dict for JSON, string otherwise)
        - path: Full path to the artifact
        - error: Error message if read failed

    Example:
        read_artifact(filename="optimade_results.json")
    """
    try:
        session_dir = _get_session_dir()
        artifact_path = session_dir / filename

        if not artifact_path.exists():
            return {
                "success": False,
                "content": None,
                "path": str(artifact_path),
                "error": f"Artifact not found: {filename}",
            }

        with open(artifact_path) as f:
            content = f.read()

        # Try to parse JSON if requested and file appears to be JSON
        if parse_json and filename.endswith(".json"):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                # Return as string if not valid JSON
                pass

        return {
            "success": True,
            "content": content,
            "path": str(artifact_path),
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to read artifact {filename}: {e}")
        return {
            "success": False,
            "content": None,
            "path": str(DEFAULT_SESSION_DIR / filename),
            "error": str(e),
        }


@function_tool
def list_artifacts() -> dict:
    """List all artifacts in the current session.

    Returns:
        Dictionary with:
        - success: True if listing succeeded
        - artifacts: List of artifact info (name, size, modified)
        - session_dir: Path to session directory
        - error: Error message if listing failed
    """
    try:
        session_dir = _get_session_dir()

        artifacts = []
        for path in session_dir.rglob("*"):
            if path.is_file():
                stat = path.stat()
                artifacts.append(
                    {
                        "name": str(path.relative_to(session_dir)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        return {
            "success": True,
            "artifacts": artifacts,
            "session_dir": str(session_dir),
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}")
        return {
            "success": False,
            "artifacts": [],
            "session_dir": str(DEFAULT_SESSION_DIR),
            "error": str(e),
        }


def update_provenance_log(
    property_name: str,
    value: Any,
    unit: str,
    source_type: str,
    source_details: dict[str, Any],
) -> dict[str, Any]:
    """Update the session provenance log with a new value.

    This is a helper function (not a tool) for tracking provenance.
    The provenance log is stored at /session/provenance.json.

    Args:
        property_name: Name of the property (e.g., "formation_energy")
        value: The computed/retrieved value
        unit: Unit of the value (e.g., "eV/atom")
        source_type: Type of source (computation, database, literature, derived)
        source_details: Additional source details (method, entry_id, doi, etc.)

    Returns:
        Status dict with success flag.
    """
    try:
        session_dir = _get_session_dir()
        provenance_path = session_dir / "provenance.json"

        # Load existing provenance log
        if provenance_path.exists():
            with open(provenance_path) as f:
                log = json.load(f)
        else:
            log = {"values": [], "created": datetime.now().isoformat()}

        # Add new entry
        entry = {
            "property": property_name,
            "value": value,
            "unit": unit,
            "source": {"type": source_type, **source_details},
            "timestamp": datetime.now().isoformat(),
        }
        log["values"].append(entry)

        # Write back
        with open(provenance_path, "w") as f:
            json.dump(log, f, indent=2, default=str)

        return {"success": True, "entry": entry}

    except Exception as e:
        logger.error(f"Failed to update provenance log: {e}")
        return {"success": False, "error": str(e)}
