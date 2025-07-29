"""
Tests for the CrystaLyse CLI.
"""
from typer.testing import CliRunner

from crystalyse.cli import app

runner = CliRunner()

def test_app_help():
    """
    Tests that the CLI runs and responds with a help message.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: crystalyse [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "CrystaLyse.AI 2.0 - A Gemini-like CLI for Materials Informatics." in result.stdout

def test_discover_help():
    """
    Tests the help message for the 'discover' command.
    """
    result = runner.invoke(app, ["discover", "--help"])
    assert result.exit_code == 0
    assert "Usage: crystalyse discover [OPTIONS] QUERY" in result.stdout

def test_chat_help():
    """
    Tests the help message for the 'chat' command.
    """
    result = runner.invoke(app, ["chat", "--help"])
    assert result.exit_code == 0
    assert "Usage: crystalyse chat [OPTIONS]" in result.stdout
