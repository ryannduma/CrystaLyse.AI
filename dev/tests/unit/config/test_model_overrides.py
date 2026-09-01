"""Tests for ``[models.*]`` overrides in ``.crystalyse/config.toml``.

Two things are under test:

1. Value-like fields on built-in entries can be overridden, and whole new
   entries can be defined, with provenance reported for each.
2. Every malformed table **raises**.  This is the point of the feature: a
   ``reasoning_effort`` that looked authoritative but was silently ignored is
   what motivated it, so a silently-dropped override would be the same bug
   wearing a different hat.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crystalyse.config.model_overrides import (
    BUILTIN,
    OVERRIDE,
    USER_DEFINED,
    ModelOverrideError,
    load_model_registry,
)
from crystalyse.config.models import MODEL_REGISTRY, ModelBackend


def _write_config(tmp_path: Path, toml: str) -> Path:
    """Write *toml* as a user-level config and return the fake home."""
    home = tmp_path / "home"
    (home / ".crystalyse").mkdir(parents=True)
    (home / ".crystalyse" / "config.toml").write_text(toml)
    return home


def _load(tmp_path: Path, toml: str):
    return load_model_registry(project_root=None, user_home=_write_config(tmp_path, toml))


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_no_config_returns_builtins_only(tmp_path: Path) -> None:
    registry, provenance = load_model_registry(
        project_root=None, user_home=tmp_path / "nonexistent"
    )
    assert set(registry) == set(MODEL_REGISTRY)
    assert set(provenance.values()) == {BUILTIN}


def test_override_model_id_on_builtin(tmp_path: Path) -> None:
    registry, provenance = _load(
        tmp_path,
        '[models.anthropic_claude_opus]\nmodel_id = "anthropic/claude-opus-4-6"\n',
    )
    assert registry["anthropic_claude_opus"].model_id == "anthropic/claude-opus-4-6"
    assert provenance["anthropic_claude_opus"] == OVERRIDE
    # Untouched fields survive.
    assert registry["anthropic_claude_opus"].backend is ModelBackend.LITELLM
    # Other entries are unaffected.
    assert provenance["openai_o3"] == BUILTIN


def test_override_multiple_value_fields(tmp_path: Path) -> None:
    registry, _ = _load(
        tmp_path,
        "[models.openai_o3]\n"
        'reasoning_effort = "low"\n'
        "context_window = 64000\n"
        "temperature = 0.25\n",
    )
    cfg = registry["openai_o3"]
    assert (cfg.reasoning_effort, cfg.context_window, cfg.temperature) == ("low", 64000, 0.25)


def test_define_new_entry(tmp_path: Path) -> None:
    registry, provenance = _load(
        tmp_path,
        "[models.my_local]\n"
        'backend = "openai-compat"\n'
        'model_id = "qwen3-32b"\n'
        'api_key_env_var = ""\n'
        'base_url = "http://localhost:8000/v1"\n'
        'supported_modes = ["explore"]\n',
    )
    cfg = registry["my_local"]
    assert cfg.name == "my_local"
    assert cfg.backend is ModelBackend.OPENAI_COMPATIBLE
    assert cfg.supported_modes == frozenset({"explore"})
    assert provenance["my_local"] == USER_DEFINED


def test_project_config_wins_over_user_config(tmp_path: Path) -> None:
    home = _write_config(tmp_path, '[models.openai_o3]\nmodel_id = "from-user"\n')
    root = tmp_path / "project"
    (root / ".crystalyse").mkdir(parents=True)
    (root / ".crystalyse" / "config.toml").write_text(
        '[models.openai_o3]\nmodel_id = "from-project"\n'
    )
    registry, _ = load_model_registry(project_root=root, user_home=home)
    assert registry["openai_o3"].model_id == "from-project"


def test_builtin_table_is_never_mutated(tmp_path: Path) -> None:
    """Overrides produce a new mapping; MODEL_REGISTRY stays the code-owned table."""
    before = MODEL_REGISTRY["openai_gpt4o_mini"].model_id
    registry, _ = _load(tmp_path, '[models.openai_gpt4o_mini]\nmodel_id = "gpt-4o-mini-2024"\n')
    assert registry["openai_gpt4o_mini"].model_id == "gpt-4o-mini-2024"
    assert MODEL_REGISTRY["openai_gpt4o_mini"].model_id == before
    assert MODEL_REGISTRY["openai_gpt4o_mini"] is not registry["openai_gpt4o_mini"]


def test_effective_registry_backs_resolution(tmp_path: Path, monkeypatch) -> None:
    """resolve_model_config() reads the effective registry, not the built-ins."""
    from crystalyse.config import models as models_mod

    home = _write_config(tmp_path, '[models.openai_gpt4o_mini]\nmodel_id = "gpt-4o-mini-2024"\n')
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    models_mod.get_effective_registry(refresh=True)
    try:
        cfg = models_mod.resolve_model_config("openai_gpt4o_mini")
        assert cfg is not None
        assert cfg.model_id == "gpt-4o-mini-2024"
    finally:
        # Drop the cache so later tests see the unpatched home.
        models_mod._EFFECTIVE_REGISTRY = None
        models_mod._EFFECTIVE_PROVENANCE = None


# ---------------------------------------------------------------------------
# Loud failures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("toml", "expected_fragment"),
    [
        ('[models.openai_o3]\nmodel_i = "o3-pro"\n', "unknown field"),
        ("[models.openai_o3]\nsupports_structured_output = true\n", "capability field"),
        ("[models.openai_o3]\nsupports_tool_calling = false\n", "capability field"),
        ('[models.openai_o3]\nbackend = "litellm"\n', "capability field"),
        ('[models.openai_o3]\nreasoning_effort = "extreme"\n', "reasoning_effort must be one of"),
        ('[models.brand_new]\nmodel_id = "x"\n', "missing required field"),
        (
            '[models.brand_new]\nbackend = "telepathy"\nmodel_id = "x"\napi_key_env_var = ""\n',
            "backend must be one of",
        ),
        (
            "[models.brand_new]\n"
            'backend = "openai"\n'
            'model_id = "x"\n'
            'api_key_env_var = ""\n'
            'supported_modes = ["turbo"]\n',
            "unknown modes",
        ),
    ],
)
def test_invalid_tables_raise(tmp_path: Path, toml: str, expected_fragment: str) -> None:
    with pytest.raises(ModelOverrideError) as exc:
        _load(tmp_path, toml)
    assert expected_fragment in str(exc.value)


def test_error_names_the_offending_file_and_table(tmp_path: Path) -> None:
    """A config error should say which table in which file is wrong."""
    with pytest.raises(ModelOverrideError) as exc:
        _load(tmp_path, "[models.openai_o3]\nnonsense = 1\n")
    message = str(exc.value)
    assert "[models.openai_o3]" in message
    assert "config.toml" in message


def test_models_table_of_wrong_type_raises(tmp_path: Path) -> None:
    with pytest.raises(ModelOverrideError):
        _load(tmp_path, 'models = "not-a-table"\n')
