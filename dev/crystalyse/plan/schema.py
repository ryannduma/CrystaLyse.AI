"""Plan artifact schema: Pydantic-validated frontmatter + freeform markdown body.

Plans are NOT fully-structured Pydantic objects.  Only the YAML frontmatter is
Pydantic-validated; the body stays opaque markdown that the agent can iterate on
freely.  This matches the Gemini CLI reference pattern (spec §14.4) and lets
users edit plan files in an external editor before approval.

Key invariants
--------------
* ``query_hash`` uses ``hashlib.sha256(query.strip().encode()).hexdigest()`` —
  strip only, **no** case normalisation.  Consistency between hash-write and
  hash-verify matters for ``--plan-file`` replay in Feature 2.5 (spec W6).
* ``schema_version: Literal["1.0"]`` is load-bearing for future-compat (spec
  W10).  ``from_markdown`` rejects incompatible versions with a clear error.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import frontmatter
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Pydantic models — frontmatter only
# ---------------------------------------------------------------------------


class PlanBudget(BaseModel):
    """Resource budget estimated during the research phase."""

    wall_time_seconds: int
    estimated_tokens: int
    polymorph_count: int
    tool_scope: Literal["chemistry_creative", "chemistry_unified"]


class PlanMetadata(BaseModel):
    """YAML frontmatter fields.  The agent is forbidden from modifying these
    after the plan is created — they are set once at plan-creation time."""

    schema_version: Literal["1.0"]
    session_id: str
    created_at: datetime
    query: str
    query_hash: str
    intended_mode: Literal["explore", "validate", "auto"]
    model: str
    budget: PlanBudget

    @field_validator("query_hash")
    @classmethod
    def _check_query_hash(cls, v: str, info) -> str:
        """Validate that query_hash matches the canonical hash of query."""
        query = info.data.get("query")
        if query is not None:
            expected = hashlib.sha256(query.strip().encode()).hexdigest()
            if v != expected:
                msg = (
                    f"query_hash mismatch: got {v!r}, expected sha256(query.strip()) = {expected!r}"
                )
                raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Plan composite — NOT a Pydantic model
# ---------------------------------------------------------------------------


@dataclass
class Plan:
    """A plan artifact: Pydantic-validated metadata + freeform markdown body.

    The body is opaque — no programmatic structure enforcement.  The prompt
    (Feature 2.3) tells the agent what sections to include; the schema doesn't
    enforce it.
    """

    metadata: PlanMetadata
    body: str
    path: Path

    def to_markdown(self) -> str:
        """Serialise the plan to a markdown string with YAML frontmatter."""
        meta_dict = self.metadata.model_dump(mode="json")
        post = frontmatter.Post(self.body, **meta_dict)
        return frontmatter.dumps(post) + "\n"

    @staticmethod
    def from_markdown(path: Path) -> Plan:
        """Parse a plan markdown file.  Validates frontmatter via Pydantic.

        Raises
        ------
        ValueError
            If ``schema_version`` is not ``"1.0"`` or any required frontmatter
            field is missing / invalid.
        FileNotFoundError
            If *path* does not exist.
        """
        text = path.read_text(encoding="utf-8")
        post = frontmatter.loads(text)

        raw_meta = dict(post.metadata)

        # --- schema_version gate (W10) ---
        version = raw_meta.get("schema_version")
        if version != "1.0":
            msg = (
                f"Unsupported plan schema_version {version!r} in {path}. "
                f"Only '1.0' is supported.  This plan file may have been "
                f"created by a newer version of CrystaLyse."
            )
            raise ValueError(msg)

        metadata = PlanMetadata(**raw_meta)
        body = post.content
        return Plan(metadata=metadata, body=body, path=path)


def compute_query_hash(query: str) -> str:
    """Canonical query hash: sha256 of stripped (but not case-normalised) query."""
    return hashlib.sha256(query.strip().encode()).hexdigest()
