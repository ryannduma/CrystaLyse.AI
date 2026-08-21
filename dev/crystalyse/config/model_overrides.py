"""User-editable model registry overrides from ``.crystalyse/config.toml``.

Why this exists
---------------

``MODEL_REGISTRY`` in :mod:`crystalyse.config.models` is a *capability table*,
not a preference file: ``backend``, ``supports_tool_calling``,
``supports_structured_output`` and ``supported_modes`` are behavioural
contracts the agent depends on, and they belong under type checking and the
contract tests.

But the value-like parts of an entry churn fast and are the parts that bite.
Provider model IDs in particular are strings that go stale between releases,
and shipping a package to correct a string is the wrong weight.  Adding a
provider should also not require editing installed package code.

So: built-ins stay in code, and ``config.toml`` may **override the value-like
fields** of a built-in or **define a whole new entry**.

Layout
------

Tables live under ``[models.<name>]``, using the same two-layer precedence as
:mod:`crystalyse.config.settings` (project config wins over user config)::

    # ~/.crystalyse/config.toml or <project>/.crystalyse/config.toml

    # Override one field of a built-in entry.
    [models.anthropic_claude_opus]
    model_id = "anthropic/claude-opus-4-6"

    # Define a new entry.  New entries must declare their capabilities.
    [models.my_local_llm]
    backend = "openai-compat"
    model_id = "qwen3-32b"
    api_key_env_var = ""
    base_url = "http://localhost:8000/v1"
    supported_modes = ["explore"]

Failing loudly
--------------

Every problem here raises :class:`ModelOverrideError` rather than being
skipped.  This is deliberate: ``reasoning_effort`` sat in ``ModelConfig`` for
a whole release being silently ignored, and
:func:`crystalyse.config.settings.load_settings` still drops unrecognised keys
without comment.  A config value that looks authoritative and does nothing is
worse than a crash.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from .models import MODE_DEFAULTS, MODEL_REGISTRY, ModelBackend, ModelConfig

logger = logging.getLogger(__name__)

#: Fields a config file may override on a **built-in** entry.  These are
#: value-like: getting one wrong produces a provider error, not a silently
#: mis-behaving agent.
OVERRIDABLE_FIELDS: frozenset[str] = frozenset(
    {
        "model_id",
        "base_url",
        "context_window",
        "max_tokens",
        "temperature",
        "reasoning_effort",
        "thinking_budget_tokens",
        "notes",
    }
)

#: Fields that describe what a model can *do*.  Settable when defining a new
#: entry, refused when overriding a built-in -- see the module docstring.
CAPABILITY_FIELDS: frozenset[str] = frozenset(
    {
        "backend",
        "api_key_env_var",
        "supports_tool_calling",
        "supports_structured_output",
        "supported_modes",
    }
)

#: Required when defining a new entry.  ``api_key_env_var`` is required but may
#: be the empty string, which means "no key needed" (local Ollama).
REQUIRED_FOR_NEW: tuple[str, ...] = ("backend", "model_id", "api_key_env_var")

VALID_EFFORTS: frozenset[str] = frozenset({"low", "medium", "high"})

#: Provenance labels reported by :func:`load_model_registry`.
BUILTIN = "built-in"
OVERRIDE = "user-override"
USER_DEFINED = "user-defined"


class ModelOverrideError(ValueError):
    """A ``[models.*]`` table in config.toml is invalid."""


def _fail(name: str, source: Path, message: str) -> None:
    raise ModelOverrideError(f"[models.{name}] in {source}: {message}")


def _validate_effort(name: str, source: Path, value: Any) -> None:
    if value is not None and value not in VALID_EFFORTS:
        _fail(
            name,
            source,
            f"reasoning_effort must be one of {sorted(VALID_EFFORTS)}, got {value!r}",
        )


def _coerce_backend(name: str, source: Path, value: Any) -> ModelBackend:
    try:
        return ModelBackend(value)
    except ValueError:
        valid = [b.value for b in ModelBackend]
        _fail(name, source, f"backend must be one of {valid}, got {value!r}")
        raise  # unreachable; keeps type checkers happy


def _coerce_modes(name: str, source: Path, value: Any) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(m, str) for m in value):
        _fail(name, source, f"supported_modes must be a list of strings, got {value!r}")
    unknown = set(value) - set(MODE_DEFAULTS)
    if unknown:
        _fail(
            name,
            source,
            f"supported_modes contains unknown modes {sorted(unknown)}; "
            f"valid modes are {sorted(MODE_DEFAULTS)}",
        )
    return frozenset(value)


def _build_override(name: str, table: dict, source: Path) -> ModelConfig:
    """Apply an override table to the built-in entry *name*."""
    base = MODEL_REGISTRY[name]

    unknown = set(table) - OVERRIDABLE_FIELDS
    if unknown:
        capability = sorted(unknown & CAPABILITY_FIELDS)
        if capability:
            _fail(
                name,
                source,
                f"cannot override capability field(s) {capability} on the built-in "
                f"entry {name!r}. Those describe what the model can do and are "
                f"code-owned; define a new [models.*] entry instead if you need "
                f"different capabilities.",
            )
        _fail(
            name,
            source,
            f"unknown field(s) {sorted(unknown)}; overridable fields are "
            f"{sorted(OVERRIDABLE_FIELDS)}",
        )

    if "reasoning_effort" in table:
        _validate_effort(name, source, table["reasoning_effort"])

    try:
        return replace(base, **table)
    except TypeError as e:  # pragma: no cover - guarded by the checks above
        _fail(name, source, str(e))
        raise


def _build_new(name: str, table: dict, source: Path) -> ModelConfig:
    """Construct a brand-new entry from a config table."""
    allowed = OVERRIDABLE_FIELDS | CAPABILITY_FIELDS
    unknown = set(table) - allowed
    if unknown:
        _fail(
            name,
            source,
            f"unknown field(s) {sorted(unknown)}; valid fields are {sorted(allowed)}",
        )

    missing = [f for f in REQUIRED_FOR_NEW if f not in table]
    if missing:
        _fail(
            name,
            source,
            f"new entry is missing required field(s) {missing}. A new model must "
            f"declare its backend, model_id and api_key_env_var (use an empty "
            f"string for a local model that needs no key).",
        )

    kwargs: dict[str, Any] = dict(table)
    kwargs["backend"] = _coerce_backend(name, source, kwargs["backend"])
    if "supported_modes" in kwargs:
        kwargs["supported_modes"] = _coerce_modes(name, source, kwargs["supported_modes"])
    if "reasoning_effort" in kwargs:
        _validate_effort(name, source, kwargs["reasoning_effort"])

    try:
        return ModelConfig(name=name, **kwargs)
    except TypeError as e:  # pragma: no cover - guarded by the checks above
        _fail(name, source, str(e))
        raise


def _model_tables(config_path: Path) -> dict[str, dict]:
    """Read the ``[models.*]`` tables out of one config.toml."""
    from .settings import _load_toml

    raw = _load_toml(config_path)
    models = raw.get("models")
    if models is None:
        return {}
    if not isinstance(models, dict):
        raise ModelOverrideError(
            f"{config_path}: [models] must be a table of per-model tables, "
            f"got {type(models).__name__}"
        )
    for name, table in models.items():
        if not isinstance(table, dict):
            raise ModelOverrideError(
                f"{config_path}: [models.{name}] must be a table, got "
                f"{type(table).__name__} — did you mean [models.{name}] "
                f"with fields under it?"
            )
    return models


def load_model_registry(
    *,
    project_root: Path | None = None,
    user_home: Path | None = None,
) -> tuple[dict[str, ModelConfig], dict[str, str]]:
    """Merge built-in entries with any ``[models.*]`` tables from config.toml.

    Precedence matches :func:`crystalyse.config.settings.load_settings`:
    built-ins, then the user config, then the project config.

    Returns
    -------
    (registry, provenance)
        *registry* maps name to :class:`ModelConfig`.  *provenance* maps the
        same names to ``"built-in"``, ``"user-override"`` or
        ``"user-defined"``, so ``crystalyse models list`` can show where each
        entry came from.

    Raises
    ------
    ModelOverrideError
        On any unknown field, bad enum value, missing required field, or an
        attempt to override a capability field on a built-in.
    """
    from .workspace import find_crystalyse_root

    registry: dict[str, ModelConfig] = dict(MODEL_REGISTRY)
    provenance: dict[str, str] = dict.fromkeys(MODEL_REGISTRY, BUILTIN)

    home = user_home or Path.home()
    candidates = [home / ".crystalyse" / "config.toml"]
    root = project_root or find_crystalyse_root()
    if root is not None:
        candidates.append(root / ".crystalyse" / "config.toml")

    for config_path in candidates:
        for name, table in _model_tables(config_path).items():
            if name in MODEL_REGISTRY:
                registry[name] = _build_override(name, table, config_path)
                provenance[name] = OVERRIDE
            else:
                registry[name] = _build_new(name, table, config_path)
                provenance[name] = USER_DEFINED
            logger.info("Model %r %s from %s", name, provenance[name], config_path)

    return registry, provenance
