"""Docker CLI runner with conservative defaults."""

import shutil
from pathlib import Path
from threading import Event

from minici.config.models import CommandConfig, DockerRunnerConfig
from minici.core.results import CommandResult
from minici.core.status import Status
from minici.runners.local import LocalRunner


class DockerRunner:
    @staticmethod
    def available() -> bool:
        return shutil.which("docker") is not None

    def execute(
        self,
        command: CommandConfig,
        config: DockerRunnerConfig,
        *,
        project_root: Path,
        environment: dict[str, str],
        timeout: float,
        cancel_event: Event | None = None,
    ) -> CommandResult:
        if not self.available():
            return CommandResult(
                command.display(), Status.FAILED, None, "", "Docker is not installed", 0
            )
        if config.pull == "always":
            LocalRunner().execute(
                CommandConfig(argv=["docker", "pull", config.image]),
                cwd=project_root,
                environment={},
                timeout=timeout,
            )
        argv = ["docker", "run", "--rm", "-v", f"{project_root}:/workspace", "-w", "/workspace"]
        if config.network:
            argv += ["--network", config.network]
        for key, value in environment.items():
            argv += ["-e", f"{key}={value}"]
        argv += [config.image]
        argv += command.argv or ["sh", "-c", command.run or ""]
        return LocalRunner().execute(
            CommandConfig(argv=argv),
            cwd=project_root,
            environment={},
            timeout=timeout,
            cancel_event=cancel_event,
        )
