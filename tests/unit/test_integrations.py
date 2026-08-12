from minici.config.models import CommandConfig, Shell
from minici.integrations.git import inspect_git
from minici.runners.docker import DockerRunner
from minici.runners.local import LocalRunner


def test_git_outside_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert inspect_git(tmp_path).available is False


def test_docker_availability_is_boolean() -> None:
    assert isinstance(DockerRunner.available(), bool)


def test_explicit_shell_arguments() -> None:
    args, shell = LocalRunner._arguments(CommandConfig(run="echo ok", shell=Shell.CMD))
    assert args[:4] == ["cmd", "/d", "/s", "/c"]
    assert shell is False
    args, shell = LocalRunner._arguments(CommandConfig(run="echo ok", shell=Shell.BASH))
    assert args[:2] == ["bash", "-c"]
    assert shell is False
