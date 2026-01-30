"""Tests for TOML-based user preferences."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestUserPreferences:
    """Test UserPreferences dataclass."""

    def test_default_preferences(self):
        """Test default values for UserPreferences."""
        from crystalyse.user_config.preferences import UserPreferences

        prefs = UserPreferences()

        # Analysis defaults
        assert prefs.analysis.default_mode == "creative"
        assert prefs.analysis.parallel_batch_size == 10
        assert prefs.analysis.max_candidates == 100

        # Display defaults
        assert prefs.display.verbosity == "normal"
        assert prefs.display.enable_html_viz is False

        # Database defaults
        assert prefs.databases.preferred_providers == ["mp", "aflow", "oqmd"]
        assert prefs.databases.max_results_per_query == 50

        # Cache defaults
        assert prefs.cache.max_discoveries == 10000
        assert prefs.cache.auto_cleanup_days == 90

        # Skills defaults
        assert prefs.skills.script_timeout_secs == 300
        assert prefs.skills.enable_sandboxing is True


class TestLoadPreferences:
    """Test loading preferences from TOML file."""

    def test_load_missing_file_returns_defaults(self):
        """Test that loading from non-existent file returns defaults."""
        from crystalyse.user_config.preferences import load_preferences

        prefs = load_preferences(Path("/nonexistent/path/config.toml"))
        assert prefs.analysis.default_mode == "creative"

    def test_load_valid_toml(self, tmp_path):
        """Test loading a valid TOML config file."""
        from crystalyse.user_config.preferences import load_preferences

        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[analysis]
default_mode = "rigorous"
parallel_batch_size = 20

[display]
verbosity = "verbose"
enable_html_viz = true

[databases]
preferred_providers = ["mp", "oqmd"]
max_results_per_query = 100

[skills]
script_timeout_secs = 600
""")

        prefs = load_preferences(config_file)

        assert prefs.analysis.default_mode == "rigorous"
        assert prefs.analysis.parallel_batch_size == 20
        assert prefs.display.verbosity == "verbose"
        assert prefs.display.enable_html_viz is True
        assert prefs.databases.preferred_providers == ["mp", "oqmd"]
        assert prefs.databases.max_results_per_query == 100
        assert prefs.skills.script_timeout_secs == 600

    def test_load_partial_toml(self, tmp_path):
        """Test loading TOML with only some sections."""
        from crystalyse.user_config.preferences import load_preferences

        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[analysis]
default_mode = "rigorous"
""")

        prefs = load_preferences(config_file)

        # Specified value
        assert prefs.analysis.default_mode == "rigorous"

        # Default values for unspecified
        assert prefs.analysis.parallel_batch_size == 10
        assert prefs.display.verbosity == "normal"

    def test_load_invalid_toml_returns_defaults(self, tmp_path):
        """Test that invalid TOML returns defaults."""
        from crystalyse.user_config.preferences import load_preferences

        config_file = tmp_path / "config.toml"
        config_file.write_text("this is not valid [toml")

        prefs = load_preferences(config_file)
        assert prefs.analysis.default_mode == "creative"


class TestSavePreferences:
    """Test saving preferences to TOML file."""

    def test_save_creates_parent_dirs(self, tmp_path):
        """Test that save creates parent directories."""
        from crystalyse.user_config.preferences import UserPreferences, save_preferences

        config_file = tmp_path / "subdir" / "config.toml"
        prefs = UserPreferences()

        save_preferences(prefs, config_file)

        assert config_file.exists()
        assert config_file.parent.exists()

    def test_save_preserves_values(self, tmp_path):
        """Test that saved values can be loaded back."""
        from crystalyse.user_config.preferences import (
            AnalysisPrefs,
            UserPreferences,
            load_preferences,
            save_preferences,
        )

        config_file = tmp_path / "config.toml"

        # Create custom preferences
        prefs = UserPreferences()
        prefs.analysis.default_mode = "rigorous"
        prefs.analysis.parallel_batch_size = 25
        prefs.display.enable_html_viz = True
        prefs.skills.script_timeout_secs = 120

        # Save
        save_preferences(prefs, config_file)

        # Load back
        loaded = load_preferences(config_file)

        assert loaded.analysis.default_mode == "rigorous"
        assert loaded.analysis.parallel_batch_size == 25
        assert loaded.display.enable_html_viz is True
        assert loaded.skills.script_timeout_secs == 120


class TestGetDefaultConfigTemplate:
    """Test default config template generation."""

    def test_template_is_valid_toml(self, tmp_path):
        """Test that the default template is valid TOML."""
        import tomllib

        from crystalyse.user_config.preferences import get_default_config_template

        template = get_default_config_template()

        # Should be parseable as TOML
        data = tomllib.loads(template)

        assert "analysis" in data
        assert "display" in data
        assert "databases" in data
        assert "cache" in data
        assert "skills" in data

    def test_template_has_all_sections(self):
        """Test that template includes all configuration sections."""
        from crystalyse.user_config.preferences import get_default_config_template

        template = get_default_config_template()

        assert "[analysis]" in template
        assert "[display]" in template
        assert "[databases]" in template
        assert "[cache]" in template
        assert "[skills]" in template
        assert "default_mode" in template
        assert "verbosity" in template
