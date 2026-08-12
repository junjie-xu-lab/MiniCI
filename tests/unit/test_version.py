from typer.testing import CliRunner

from minici.cli.app import app
from minici.version import __version__

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert f"MiniCI {__version__}" in result.stdout


def test_verbose_version_command() -> None:
    result = runner.invoke(app, ["version", "--verbose"])

    assert result.exit_code == 0
    assert "Python " in result.stdout
    assert "Platform " in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.stdout
