from minici.config.models import CommandConfig, DockerRunnerConfig
from minici.core.status import Status
from minici.runners.docker import DockerRunner


def test_missing_docker_has_clear_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("minici.runners.docker.shutil.which", lambda _: None)
    result = DockerRunner().execute(
        CommandConfig(argv=["python", "--version"]),
        DockerRunnerConfig(type="docker", image="python:3.12-slim"),
        project_root=tmp_path,
        environment={},
        timeout=5,
    )
    assert result.status is Status.FAILED
    assert "not installed" in result.stderr
