from pathlib import Path

import pytest
from typer.testing import CliRunner

from minici.cli.app import app

runner = CliRunner()


def test_init_validate_and_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    init_result = runner.invoke(app, ["init"])
    assert init_result.exit_code == 0
    assert Path("minici.yml").exists()

    duplicate = runner.invoke(app, ["init"])
    assert duplicate.exit_code == 2

    validate_result = runner.invoke(app, ["validate", "--resolved"])
    assert validate_result.exit_code == 0
    assert "quality / test" in validate_result.stdout

    dry_result = runner.invoke(app, ["run", "--dry-run"])
    assert dry_result.exit_code == 0
    assert "echo MiniCI pipeline ready" in dry_result.stdout


def test_validate_reports_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
    assert "Configuration error" in result.stdout
