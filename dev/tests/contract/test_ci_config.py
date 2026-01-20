"""
Contract tests for CI/CD configuration.

These tests validate that required CI configuration files exist and have
the correct structure. This ensures CI infrastructure remains intact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Project root is parent of dev/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestGitHubWorkflows:
    """Tests for GitHub Actions workflow configurations."""

    def test_ci_workflow_exists(self) -> None:
        """Test that main CI workflow file exists."""
        ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists(), f"CI workflow not found at {ci_path}"

    def test_ci_workflow_has_required_jobs(self) -> None:
        """Test that CI workflow contains required jobs."""
        ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        if not ci_path.exists():
            pytest.skip("CI workflow file does not exist yet")

        content = ci_path.read_text()

        # Check for required job names
        required_jobs = ["lint", "test"]
        for job in required_jobs:
            assert f"{job}:" in content, f"CI workflow missing '{job}' job"

    def test_dependabot_config_exists(self) -> None:
        """Test that Dependabot configuration exists."""
        dependabot_path = PROJECT_ROOT / ".github" / "dependabot.yml"
        assert dependabot_path.exists(), f"Dependabot config not found at {dependabot_path}"


class TestPreCommitConfig:
    """Tests for pre-commit configuration."""

    def test_precommit_config_exists(self) -> None:
        """Test that pre-commit config exists."""
        precommit_path = PROJECT_ROOT / "dev" / ".pre-commit-config.yaml"
        assert precommit_path.exists(), f"Pre-commit config not found at {precommit_path}"

    def test_precommit_has_ruff(self) -> None:
        """Test that pre-commit includes ruff hooks."""
        precommit_path = PROJECT_ROOT / "dev" / ".pre-commit-config.yaml"
        if not precommit_path.exists():
            pytest.skip("Pre-commit config does not exist yet")

        content = precommit_path.read_text()
        assert "ruff" in content.lower(), "Pre-commit config missing ruff hooks"

    def test_precommit_has_codespell(self) -> None:
        """Test that pre-commit includes codespell."""
        precommit_path = PROJECT_ROOT / "dev" / ".pre-commit-config.yaml"
        if not precommit_path.exists():
            pytest.skip("Pre-commit config does not exist yet")

        content = precommit_path.read_text()
        assert "codespell" in content.lower(), "Pre-commit config missing codespell"


class TestPyprojectConfig:
    """Tests for pyproject.toml configuration."""

    def test_pyproject_exists(self) -> None:
        """Test that pyproject.toml exists."""
        pyproject_path = PROJECT_ROOT / "dev" / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"

    def test_pyproject_has_pytest_config(self) -> None:
        """Test that pyproject.toml has pytest configuration."""
        pyproject_path = PROJECT_ROOT / "dev" / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml does not exist")

        content = pyproject_path.read_text()
        assert "[tool.pytest" in content, "pyproject.toml missing pytest configuration"

    def test_pyproject_has_coverage_config(self) -> None:
        """Test that pyproject.toml has coverage configuration."""
        pyproject_path = PROJECT_ROOT / "dev" / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml does not exist")

        content = pyproject_path.read_text()
        assert "[tool.coverage" in content, "pyproject.toml missing coverage configuration"

    def test_pyproject_has_ruff_config(self) -> None:
        """Test that pyproject.toml has ruff configuration."""
        pyproject_path = PROJECT_ROOT / "dev" / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml does not exist")

        content = pyproject_path.read_text()
        assert "[tool.ruff" in content, "pyproject.toml missing ruff configuration"

    def test_pyproject_has_dev_dependencies(self) -> None:
        """Test that pyproject.toml has dev dependencies."""
        pyproject_path = PROJECT_ROOT / "dev" / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml does not exist")

        content = pyproject_path.read_text()
        assert "pytest" in content, "pyproject.toml missing pytest in dependencies"
        assert "ruff" in content, "pyproject.toml missing ruff in dependencies"


class TestTestStructure:
    """Tests for test directory structure."""

    def test_tests_directory_exists(self) -> None:
        """Test that tests directory exists."""
        tests_path = PROJECT_ROOT / "dev" / "tests"
        assert tests_path.exists(), f"Tests directory not found at {tests_path}"

    def test_conftest_exists(self) -> None:
        """Test that main conftest.py exists."""
        conftest_path = PROJECT_ROOT / "dev" / "tests" / "conftest.py"
        assert conftest_path.exists(), f"conftest.py not found at {conftest_path}"

    def test_unit_tests_directory_exists(self) -> None:
        """Test that unit tests directory exists."""
        unit_path = PROJECT_ROOT / "dev" / "tests" / "unit"
        assert unit_path.exists(), f"Unit tests directory not found at {unit_path}"

    def test_required_test_subdirectories(self) -> None:
        """Test that required test subdirectories exist."""
        tests_path = PROJECT_ROOT / "dev" / "tests"
        required_dirs = ["unit", "unit/tools", "unit/memory", "unit/provenance"]

        for dir_name in required_dirs:
            dir_path = tests_path / dir_name
            assert dir_path.exists(), f"Test directory not found: {dir_path}"


class TestDocumentation:
    """Tests for documentation configuration."""

    def test_mkdocs_config_exists(self) -> None:
        """Test that mkdocs.yml exists."""
        mkdocs_path = PROJECT_ROOT / "mkdocs.yml"
        assert mkdocs_path.exists(), f"mkdocs.yml not found at {mkdocs_path}"

    def test_readthedocs_config_exists(self) -> None:
        """Test that .readthedocs.yaml exists."""
        rtd_path = PROJECT_ROOT / ".readthedocs.yaml"
        assert rtd_path.exists(), f".readthedocs.yaml not found at {rtd_path}"


class TestGitHubTemplates:
    """Tests for GitHub issue and PR templates."""

    def test_pr_template_exists(self) -> None:
        """Test that PR template exists."""
        pr_template = PROJECT_ROOT / ".github" / "pull_request_template.md"
        assert pr_template.exists(), f"PR template not found at {pr_template}"

    def test_issue_templates_exist(self) -> None:
        """Test that issue templates exist."""
        template_dir = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE"
        assert template_dir.exists(), f"Issue template directory not found at {template_dir}"

        # Check for required templates
        bug_template = template_dir / "1-bug-report.yml"
        feature_template = template_dir / "2-feature-request.yml"
        config = template_dir / "config.yml"

        assert bug_template.exists(), "Bug report template not found"
        assert feature_template.exists(), "Feature request template not found"
        assert config.exists(), "Issue template config not found"


class TestRequiredFiles:
    """Tests for other required files."""

    def test_claude_md_exists(self) -> None:
        """Test that CLAUDE.md exists for Claude Code guidance."""
        claude_path = PROJECT_ROOT / "CLAUDE.md"
        gitignore_path = PROJECT_ROOT / ".gitignore"

        # Skip if CLAUDE.md is gitignored (common for projects that keep it local)
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            if "CLAUDE.md" in gitignore_content:
                pytest.skip("CLAUDE.md is gitignored - skipping check")

        assert claude_path.exists(), f"CLAUDE.md not found at {claude_path}"

    def test_readme_exists(self) -> None:
        """Test that README exists."""
        readme_path = PROJECT_ROOT / "README.md"
        # Could also be in dev/
        dev_readme = PROJECT_ROOT / "dev" / "README.md"
        assert readme_path.exists() or dev_readme.exists(), "README.md not found"
