import json
import sys
from pathlib import Path

from minici.application.pipeline import PipelineService
from minici.config.models import MiniCIConfig
from minici.core.status import Status


def config(tmp_path: Path, *, fail: bool = False, retry: int = 1) -> MiniCIConfig:
    code = "import sys; print('<output>'); sys.exit(4)" if fail else "print('ok')"
    return MiniCIConfig.model_validate(
        {
            "version": 1,
            "project": {"name": "demo<script>"},
            "environment": {"DEMO_ENV": "yes"},
            "stages": [
                {
                    "name": "quality",
                    "steps": [
                        {
                            "name": "test",
                            "retry": {"max_attempts": retry, "delay_seconds": 0},
                            "commands": [{"argv": [sys.executable, "-c", code]}],
                        },
                        {
                            "name": "after",
                            "commands": [{"argv": [sys.executable, "-c", "print('after')"]}],
                        },
                    ],
                }
            ],
        }
    )


def test_success_pipeline_creates_artifacts(tmp_path: Path) -> None:
    service = PipelineService(tmp_path)
    result = service.execute(config(tmp_path))
    assert result.status is Status.SUCCESS
    row = service.repository.recent(1)[0]
    run_dir = Path(row["run_directory"])
    assert row["status"] == "SUCCESS"
    assert "ok" in (run_dir / "run.log").read_text(encoding="utf-8")
    html = (run_dir / "report.html").read_text(encoding="utf-8")
    assert "demo&lt;script&gt;" in html
    assert json.loads(row["summary_json"])["stages"][0]["status"] == "SUCCESS"
    details = service.repository.details(result.run_id or 0)
    assert details is not None
    assert details["stages"][0]["name"] == "quality"


def test_failure_retries_and_skips(tmp_path: Path) -> None:
    result = PipelineService(tmp_path).execute(config(tmp_path, fail=True, retry=2))
    assert result.status is Status.FAILED
    assert len(result.stages[0].steps[0].attempts) == 2
    assert result.stages[0].steps[1].status is Status.SKIPPED
    assert PipelineService(tmp_path).repository.details(9999) is None


def test_secret_is_redacted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MY_SECRET", "hidden-value")
    cfg = config(tmp_path)
    cfg.secrets.from_environment = ["MY_SECRET"]
    cfg.stages[0].steps[0].commands[0].argv = [
        sys.executable,
        "-c",
        "print('hidden-value')",
    ]
    result = PipelineService(tmp_path).execute(cfg)
    row = PipelineService(tmp_path).repository.recent(1)[0]
    log = (Path(row["run_directory"]) / "run.log").read_text(encoding="utf-8")
    assert result.status is Status.SUCCESS
    assert "hidden-value" not in log
    assert "***" in log
