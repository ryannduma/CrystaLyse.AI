"""Tests for crystalyse.plan.schema — Feature 2.1 acceptance criteria.

Acceptance criteria from spec §5 Feature 2.1:
  AC1: Round-trip test: Plan → to_markdown() → from_markdown() → equal
  AC2: Pydantic frontmatter validation catches missing required fields
  AC3: query_hash matches sha256(query.strip().encode()).hexdigest()
  AC4: PlanBudget.tool_scope literal type rejects unknown values
  AC5: Manually-edited body parses successfully with intact frontmatter
  AC6: schema_version != "1.0" raises clear error on from_markdown()
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from crystalyse.plan.schema import Plan, PlanBudget, PlanMetadata, compute_query_hash

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_QUERY = "  Discover stable perovskites for photovoltaics  "
SAMPLE_QUERY_HASH = hashlib.sha256(SAMPLE_QUERY.strip().encode()).hexdigest()
SAMPLE_CREATED_AT = datetime(2026, 4, 12, 14, 30, 0, tzinfo=UTC)

SAMPLE_BODY = """\
## Research findings

Perovskites ABX3 with A = Cs, MA; B = Pb, Sn; X = I, Br show promise.

## Planned steps

1. SMACT filter for charge-neutral compositions
2. Chemeleon generation of candidate structures
3. MACE energy ranking
4. Phase diagram analysis via PyMatGen

## Assumptions

- Room temperature stability is the primary concern
- Lead-free alternatives preferred but not required
"""


def _make_budget(**overrides) -> PlanBudget:
    defaults = {
        "wall_time_seconds": 300,
        "estimated_tokens": 50000,
        "polymorph_count": 5,
        "tool_scope": "chemistry_creative",
    }
    defaults.update(overrides)
    return PlanBudget(**defaults)


def _make_metadata(**overrides) -> PlanMetadata:
    defaults = {
        "schema_version": "1.0",
        "session_id": "sess-abc123",
        "created_at": SAMPLE_CREATED_AT,
        "query": SAMPLE_QUERY,
        "query_hash": SAMPLE_QUERY_HASH,
        "intended_mode": "explore",
        "model": "openai_o4_mini",
        "budget": _make_budget(),
    }
    defaults.update(overrides)
    return PlanMetadata(**defaults)


def _make_plan(tmp_path: Path, **meta_overrides) -> Plan:
    return Plan(
        metadata=_make_metadata(**meta_overrides),
        body=SAMPLE_BODY,
        path=tmp_path / "test-plan.md",
    )


# ---------------------------------------------------------------------------
# AC1: Round-trip test
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """AC1: create a Plan, call to_markdown(), parse with from_markdown(),
    assert metadata pydantic-equal AND body string-equal."""

    def test_round_trip_metadata_equal(self, tmp_path):
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata == plan.metadata

    def test_round_trip_body_equal(self, tmp_path):
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.body.strip() == plan.body.strip()

    def test_round_trip_full(self, tmp_path):
        """Full round-trip: metadata AND body both survive."""
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata == plan.metadata
        assert restored.body.strip() == plan.body.strip()

    def test_round_trip_with_unified_tool_scope(self, tmp_path):
        plan = _make_plan(tmp_path, budget=_make_budget(tool_scope="chemistry_unified"))
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata.budget.tool_scope == "chemistry_unified"


# ---------------------------------------------------------------------------
# AC2: Pydantic frontmatter validation catches missing required fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    """AC2: Pydantic catches missing required frontmatter fields."""

    def test_missing_session_id(self):
        with pytest.raises(ValidationError, match="session_id"):
            PlanMetadata(
                schema_version="1.0",
                # session_id missing
                created_at=SAMPLE_CREATED_AT,
                query=SAMPLE_QUERY,
                query_hash=SAMPLE_QUERY_HASH,
                intended_mode="explore",
                model="openai_o4_mini",
                budget=_make_budget(),
            )

    def test_missing_query(self):
        with pytest.raises(ValidationError, match="query"):
            PlanMetadata(
                schema_version="1.0",
                session_id="sess-abc",
                created_at=SAMPLE_CREATED_AT,
                # query missing
                query_hash="deadbeef",
                intended_mode="explore",
                model="openai_o4_mini",
                budget=_make_budget(),
            )

    def test_missing_budget(self):
        with pytest.raises(ValidationError, match="budget"):
            PlanMetadata(
                schema_version="1.0",
                session_id="sess-abc",
                created_at=SAMPLE_CREATED_AT,
                query=SAMPLE_QUERY,
                query_hash=SAMPLE_QUERY_HASH,
                intended_mode="explore",
                model="openai_o4_mini",
                # budget missing
            )

    def test_missing_schema_version(self):
        with pytest.raises(ValidationError, match="schema_version"):
            PlanMetadata(
                # schema_version missing
                session_id="sess-abc",
                created_at=SAMPLE_CREATED_AT,
                query=SAMPLE_QUERY,
                query_hash=SAMPLE_QUERY_HASH,
                intended_mode="explore",
                model="openai_o4_mini",
                budget=_make_budget(),
            )

    def test_from_markdown_missing_field(self, tmp_path):
        """Frontmatter with a missing required field fails on parse."""
        content = """\
---
schema_version: '1.0'
session_id: sess-abc
---
Body text.
"""
        path = tmp_path / "bad-plan.md"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValidationError):
            Plan.from_markdown(path)


# ---------------------------------------------------------------------------
# AC3: query_hash canonicalisation
# ---------------------------------------------------------------------------


class TestQueryHash:
    """AC3: query_hash matches sha256(query.strip().encode()).hexdigest() —
    verify the exact canonicalisation rule."""

    def test_hash_matches_stripped_query(self):
        query = "  Discover stable perovskites  "
        expected = hashlib.sha256(query.strip().encode()).hexdigest()
        meta = _make_metadata(query=query, query_hash=expected)
        assert meta.query_hash == expected

    def test_hash_mismatch_raises(self):
        """Wrong query_hash is caught by the Pydantic validator."""
        with pytest.raises(ValidationError, match="query_hash mismatch"):
            _make_metadata(query_hash="0000bad0000")

    def test_no_case_normalisation(self):
        """Strip only — no lowercasing.  'ABC' and 'abc' hash differently."""
        q_upper = "ABC"
        q_lower = "abc"
        hash_upper = hashlib.sha256(q_upper.strip().encode()).hexdigest()
        hash_lower = hashlib.sha256(q_lower.strip().encode()).hexdigest()
        assert hash_upper != hash_lower

        # Upper-case hash must be accepted for upper-case query
        meta = _make_metadata(query=q_upper, query_hash=hash_upper)
        assert meta.query_hash == hash_upper

        # And lower-case hash must NOT match upper-case query
        with pytest.raises(ValidationError, match="query_hash mismatch"):
            _make_metadata(query=q_upper, query_hash=hash_lower)

    def test_compute_query_hash_helper(self):
        query = "  some query  "
        expected = hashlib.sha256(b"some query").hexdigest()
        assert compute_query_hash(query) == expected

    def test_round_trip_preserves_hash(self, tmp_path):
        """Hash survives serialisation → deserialisation."""
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")
        restored = Plan.from_markdown(plan.path)
        assert restored.metadata.query_hash == plan.metadata.query_hash


# ---------------------------------------------------------------------------
# AC4: PlanBudget.tool_scope rejects unknown values
# ---------------------------------------------------------------------------


class TestToolScope:
    """AC4: PlanBudget.tool_scope literal type rejects unknown values."""

    def test_chemistry_creative_accepted(self):
        b = _make_budget(tool_scope="chemistry_creative")
        assert b.tool_scope == "chemistry_creative"

    def test_chemistry_unified_accepted(self):
        b = _make_budget(tool_scope="chemistry_unified")
        assert b.tool_scope == "chemistry_unified"

    def test_unknown_scope_rejected(self):
        with pytest.raises(ValidationError, match="tool_scope"):
            _make_budget(tool_scope="chemistry_fast")

    def test_empty_scope_rejected(self):
        with pytest.raises(ValidationError, match="tool_scope"):
            _make_budget(tool_scope="")


# ---------------------------------------------------------------------------
# AC5: Manually-edited body parses with intact frontmatter
# ---------------------------------------------------------------------------


class TestEditedBody:
    """AC5: A plan with a manually-edited body (extra text, reordered sections)
    parses successfully as long as frontmatter is intact."""

    def test_extra_text_in_body(self, tmp_path):
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        # Append extra text to the body
        md_with_extra = md + "\n\n## Extra section added by user\n\nSome extra notes.\n"
        plan.path.write_text(md_with_extra, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata == plan.metadata
        assert "Extra section added by user" in restored.body

    def test_reordered_sections_in_body(self, tmp_path):
        """Reordering markdown sections in the body doesn't break parsing."""
        reordered_body = """\
## Assumptions

- Room temperature stability

## Research findings

Some findings here.

## Planned steps

1. Do something
2. Do something else
"""
        plan = Plan(
            metadata=_make_metadata(),
            body=reordered_body,
            path=tmp_path / "reordered.md",
        )
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata == plan.metadata
        assert "Assumptions" in restored.body
        assert "Research findings" in restored.body

    def test_empty_body(self, tmp_path):
        """A plan with no body content still parses."""
        plan = Plan(
            metadata=_make_metadata(),
            body="",
            path=tmp_path / "empty-body.md",
        )
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata == plan.metadata

    def test_body_with_yaml_like_content(self, tmp_path):
        """Body containing YAML-like strings doesn't confuse the parser."""
        tricky_body = """\
## Notes

The config uses:
```yaml
key: value
nested:
  foo: bar
```

And some `---` dividers in the text.
"""
        plan = Plan(
            metadata=_make_metadata(),
            body=tricky_body,
            path=tmp_path / "tricky.md",
        )
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata == plan.metadata
        assert "key: value" in restored.body


# ---------------------------------------------------------------------------
# AC6: schema_version != "1.0" raises a clear error
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    """AC6: schema_version != '1.0' raises a clear error on from_markdown()."""

    def test_version_2_0_rejected(self, tmp_path):
        path = tmp_path / "v2-plan.md"
        content = """\
---
schema_version: '2.0'
session_id: sess-abc
created_at: '2026-04-12T14:30:00+00:00'
query: test query
query_hash: {hash}
intended_mode: explore
model: openai_o4_mini
budget:
  wall_time_seconds: 300
  estimated_tokens: 50000
  polymorph_count: 5
  tool_scope: chemistry_creative
---
Body text.
""".format(hash=hashlib.sha256(b"test query").hexdigest())
        path.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported plan schema_version"):
            Plan.from_markdown(path)

    def test_missing_version_rejected(self, tmp_path):
        """No schema_version at all is also rejected."""
        path = tmp_path / "no-version.md"
        content = """\
---
session_id: sess-abc
created_at: '2026-04-12T14:30:00+00:00'
query: test query
query_hash: placeholder
intended_mode: explore
model: openai_o4_mini
budget:
  wall_time_seconds: 300
  estimated_tokens: 50000
  polymorph_count: 5
  tool_scope: chemistry_creative
---
Body text.
"""
        path.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported plan schema_version"):
            Plan.from_markdown(path)

    def test_version_1_0_accepted(self, tmp_path):
        """Version 1.0 parses without error (positive case)."""
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.metadata.schema_version == "1.0"

    def test_pydantic_rejects_wrong_version_at_construction(self):
        """Even without from_markdown, constructing with bad version fails."""
        with pytest.raises(ValidationError, match="schema_version"):
            _make_metadata(schema_version="2.0")


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_intended_mode_rejects_old_names(self):
        """Old mode names (creative/rigorous/adaptive) are not accepted."""
        with pytest.raises(ValidationError, match="intended_mode"):
            _make_metadata(intended_mode="creative")

    def test_intended_mode_accepts_all_canonical(self):
        for mode in ("explore", "validate", "auto"):
            meta = _make_metadata(intended_mode=mode)
            assert meta.intended_mode == mode

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Plan.from_markdown(Path("/nonexistent/plan.md"))

    def test_plan_path_preserved(self, tmp_path):
        """from_markdown stores the path it was loaded from."""
        plan = _make_plan(tmp_path)
        md = plan.to_markdown()
        plan.path.write_text(md, encoding="utf-8")

        restored = Plan.from_markdown(plan.path)
        assert restored.path == plan.path
