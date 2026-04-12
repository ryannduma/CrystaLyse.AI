"""Tests for CrystalyseSettings and load_settings().

Covers all acceptance criteria from spec §4.5:
- Unit test with no .crystalyse/ returns defaults from load_settings()
- Unit test with .crystalyse/config.toml loads the values correctly
- Unit test with both project-level and user-level settings asserts project
  takes precedence
"""

from __future__ import annotations

from pathlib import Path

from crystalyse.config.settings import CrystalyseSettings, load_settings


# ---------------------------------------------------------------------------
# CrystalyseSettings defaults
# ---------------------------------------------------------------------------


class TestCrystalyseSettingsDefaults:
    def test_default_model(self) -> None:
        s = CrystalyseSettings()
        assert s.default_model == "openai_o4_mini"

    def test_default_mode(self) -> None:
        s = CrystalyseSettings()
        assert s.default_mode == "explore"

    def test_default_plan_mode(self) -> None:
        s = CrystalyseSettings()
        assert s.plan_mode == "auto"

    def test_default_plans_directory_is_none(self) -> None:
        s = CrystalyseSettings()
        assert s.plans_directory is None

    def test_default_plans_cleanup_days(self) -> None:
        s = CrystalyseSettings()
        assert s.plans_cleanup_days == 30

    def test_settings_is_frozen(self) -> None:
        """Settings should be immutable once loaded."""
        s = CrystalyseSettings()
        import dataclasses

        assert dataclasses.is_dataclass(s)
        # Frozen dataclass raises FrozenInstanceError on assignment
        try:
            s.default_model = "something"  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass  # Expected: frozen dataclass


# ---------------------------------------------------------------------------
# load_settings — no config files
# ---------------------------------------------------------------------------


class TestLoadSettingsNoConfig:
    def test_returns_defaults_with_no_crystalyse_dir(self, tmp_path: Path) -> None:
        """Acceptance criterion: no .crystalyse/ returns defaults."""
        s = load_settings(
            project_root=tmp_path,  # no .crystalyse/ here
            user_home=tmp_path / "fakehome",  # no ~/.crystalyse/ either
        )
        assert s == CrystalyseSettings()

    def test_returns_defaults_with_empty_config_toml(self, tmp_path: Path) -> None:
        crystalyse_dir = tmp_path / ".crystalyse"
        crystalyse_dir.mkdir()
        (crystalyse_dir / "config.toml").write_text("# empty\n")

        s = load_settings(
            project_root=tmp_path,
            user_home=tmp_path / "fakehome",
        )
        assert s == CrystalyseSettings()


# ---------------------------------------------------------------------------
# load_settings — project-level config
# ---------------------------------------------------------------------------


class TestLoadSettingsProjectConfig:
    def test_loads_values_from_project_config(self, tmp_path: Path) -> None:
        """Acceptance criterion: creates temp project with config.toml,
        calls load_settings(), asserts values are loaded."""
        crystalyse_dir = tmp_path / ".crystalyse"
        crystalyse_dir.mkdir()
        (crystalyse_dir / "config.toml").write_text(
            'default_model = "openai_o3"\n'
            'default_mode = "validate"\n'
            'plan_mode = "off"\n'
            "plans_cleanup_days = 7\n"
        )

        s = load_settings(
            project_root=tmp_path,
            user_home=tmp_path / "fakehome",
        )
        assert s.default_model == "openai_o3"
        assert s.default_mode == "validate"
        assert s.plan_mode == "off"
        assert s.plans_cleanup_days == 7
        # Unset fields keep their defaults
        assert s.plans_directory is None

    def test_ignores_unknown_keys(self, tmp_path: Path) -> None:
        crystalyse_dir = tmp_path / ".crystalyse"
        crystalyse_dir.mkdir()
        (crystalyse_dir / "config.toml").write_text(
            'default_model = "openai_o3"\n'
            'unknown_key = "ignored"\n'
        )

        s = load_settings(
            project_root=tmp_path,
            user_home=tmp_path / "fakehome",
        )
        assert s.default_model == "openai_o3"
        assert not hasattr(s, "unknown_key")


# ---------------------------------------------------------------------------
# load_settings — user-level config
# ---------------------------------------------------------------------------


class TestLoadSettingsUserConfig:
    def test_loads_values_from_user_config(self, tmp_path: Path) -> None:
        user_home = tmp_path / "home"
        user_crystalyse = user_home / ".crystalyse"
        user_crystalyse.mkdir(parents=True)
        (user_crystalyse / "config.toml").write_text(
            'default_model = "user_model"\n'
            "plans_cleanup_days = 14\n"
        )

        s = load_settings(
            project_root=tmp_path / "no_project",  # no project-level config
            user_home=user_home,
        )
        assert s.default_model == "user_model"
        assert s.plans_cleanup_days == 14
        # Other fields keep defaults
        assert s.default_mode == "explore"


# ---------------------------------------------------------------------------
# load_settings — precedence
# ---------------------------------------------------------------------------


class TestLoadSettingsPrecedence:
    def test_project_takes_precedence_over_user(self, tmp_path: Path) -> None:
        """Acceptance criterion: project-level settings override user-level."""
        # User config
        user_home = tmp_path / "home"
        user_crystalyse = user_home / ".crystalyse"
        user_crystalyse.mkdir(parents=True)
        (user_crystalyse / "config.toml").write_text(
            'default_model = "user_model"\n'
            'default_mode = "auto"\n'
            "plans_cleanup_days = 14\n"
        )

        # Project config (overrides user for model and cleanup_days)
        project_crystalyse = tmp_path / "project" / ".crystalyse"
        project_crystalyse.mkdir(parents=True)
        (project_crystalyse / "config.toml").write_text(
            'default_model = "project_model"\n'
            "plans_cleanup_days = 3\n"
        )

        s = load_settings(
            project_root=tmp_path / "project",
            user_home=user_home,
        )
        # Project wins for overlapping keys
        assert s.default_model == "project_model"
        assert s.plans_cleanup_days == 3
        # User wins for keys only set at user level
        assert s.default_mode == "auto"
        # Defaults for unset keys
        assert s.plan_mode == "auto"

    def test_project_overrides_all_user_values(self, tmp_path: Path) -> None:
        """If both set the same key, project always wins."""
        user_home = tmp_path / "home"
        (user_home / ".crystalyse").mkdir(parents=True)
        (user_home / ".crystalyse" / "config.toml").write_text(
            'plan_mode = "off"\n'
        )

        project = tmp_path / "proj"
        (project / ".crystalyse").mkdir(parents=True)
        (project / ".crystalyse" / "config.toml").write_text(
            'plan_mode = "on"\n'
        )

        s = load_settings(project_root=project, user_home=user_home)
        assert s.plan_mode == "on"


# ---------------------------------------------------------------------------
# load_settings — malformed config
# ---------------------------------------------------------------------------


class TestLoadSettingsMalformedConfig:
    def test_malformed_toml_returns_defaults(self, tmp_path: Path) -> None:
        crystalyse_dir = tmp_path / ".crystalyse"
        crystalyse_dir.mkdir()
        (crystalyse_dir / "config.toml").write_text("this is not valid toml {{{\n")

        s = load_settings(
            project_root=tmp_path,
            user_home=tmp_path / "fakehome",
        )
        # Malformed file is skipped; defaults returned
        assert s == CrystalyseSettings()
