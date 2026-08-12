import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from minici.cli.app import app

runner = CliRunner()


def test_run_status_logs_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = f"""version: 1
project: {{name: cli-demo}}
stages:
  - name: build
    steps:
      - name: hello
        commands:
          - argv: ['{sys.executable}', -c, "print('from-cli')"]
"""
    Path("minici.yml").write_text(config, encoding="utf-8")
    run = runner.invoke(app, ["run"])
    assert run.exit_code == 0
    assert "SUCCESS" in run.stdout
    status = runner.invoke(app, ["status"])
    assert status.exit_code == 0
    assert "cli-demo" in status.stdout
    logs = runner.invoke(app, ["logs", "1"])
    assert logs.exit_code == 0
    assert "from-cli" in logs.stdout
    report = runner.invoke(app, ["report", "1"])
    assert report.exit_code == 0
    assert "report.html" in report.stdout


def test_doctor_plugins_and_missing_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    doctor = runner.invoke(app, ["doctor"])
    assert doctor.exit_code == 0
    assert "Docker:" in doctor.stdout
    plugins = runner.invoke(app, ["plugin-list"])
    assert plugins.exit_code == 0
    assert "No plugins" in plugins.stdout
    missing = runner.invoke(app, ["logs", "99"])
    assert missing.exit_code == 2
    assert "Run not found" in missing.stdout
