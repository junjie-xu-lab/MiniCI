"""Pipeline orchestration shared by CLI and dashboard."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

from filelock import FileLock, Timeout

from minici.config.models import MiniCIConfig, StageConfig, StepConfig
from minici.core.conditions import should_run
from minici.core.results import AttemptResult, PipelineResult, StageResult, StepResult
from minici.core.status import Status
from minici.database.repository import RunRepository
from minici.integrations.git import inspect_git
from minici.logging.run_log import RunLog
from minici.plugins import call_hook, discover_plugins
from minici.reports.html import generate_report
from minici.runners.docker import DockerRunner
from minici.runners.local import LocalRunner


class PipelineService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.data_root = self.project_root / ".minici"
        self.repository = RunRepository(self.data_root / "minici.db")
        self.runner = LocalRunner()
        self.docker_runner = DockerRunner()
        self.git_info = inspect_git(self.project_root)
        self.plugins = discover_plugins()
        self.cancel_event = Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def execute(self, config: MiniCIConfig) -> PipelineResult:
        self.cancel_event.clear()
        self.data_root.mkdir(parents=True, exist_ok=True)
        lock = FileLock(self.data_root / "run.lock", timeout=0)
        try:
            with lock:
                return self._execute_locked(config)
        except Timeout as exc:
            raise RuntimeError("another MiniCI run is already active") from exc

    def _execute_locked(self, config: MiniCIConfig) -> PipelineResult:
        call_hook(self.plugins, "before_run", config.project.name)
        started = datetime.now(timezone.utc)
        run_id, run_uid, run_directory = self.repository.start_run(
            config.project.name, self.data_root / "runs"
        )
        try:
            result = self._run_pipeline(config, started, run_id, run_uid, run_directory)
            call_hook(self.plugins, "after_run", config.project.name, result.status.value)
            return result
        except BaseException:
            self.repository.fail_run(run_id)
            raise

    def _run_pipeline(
        self,
        config: MiniCIConfig,
        started: datetime,
        run_id: int,
        run_uid: str,
        run_directory: Path,
    ) -> PipelineResult:
        secrets = [
            os.environ[name] for name in config.secrets.from_environment if name in os.environ
        ]
        run_log = RunLog(run_directory / "run.log", secrets)
        stages: list[StageResult] = []
        pipeline_failed = False
        for stage in config.stages:
            if pipeline_failed:
                stages.append(self._skipped_stage(stage))
                continue
            stage_result = self._execute_stage(config, stage, run_log)
            stages.append(stage_result)
            pipeline_failed = stage_result.status is not Status.SUCCESS
            final_status = Status.SUCCESS
            for stage in stages:
                if stage.status not in {Status.SUCCESS, Status.SKIPPED}:
                    final_status = stage.status
                    break
            result = PipelineResult(
                project=config.project.name,
                status=final_status,
                started_at=started,
                ended_at=datetime.now(timezone.utc),
                stages=stages,
                run_id=run_id,
                run_uid=run_uid,
            )
        self.repository.finish_run(result)
        generate_report(result, run_directory / "report.html")
        return result

    def _execute_stage(
        self, config: MiniCIConfig, stage: StageConfig, run_log: RunLog
    ) -> StageResult:
        if stage.parallel and len(stage.steps) > 1:
            with ThreadPoolExecutor(max_workers=len(stage.steps)) as pool:
                futures = [
                    pool.submit(self._execute_step, config, stage, step, run_log)
                    for step in stage.steps
                ]
                steps = [future.result() for future in futures]
        else:
            steps = []
            failed = False
            for step in stage.steps:
                if failed and stage.fail_fast:
                    steps.append(StepResult(step.name, Status.SKIPPED))
                    continue
                result = self._execute_step(config, stage, step, run_log)
                steps.append(result)
                failed = result.status is not Status.SUCCESS and not step.continue_on_error
        status = Status.SUCCESS
        for index, step_result in enumerate(steps):
            if (
                step_result.status not in {Status.SUCCESS, Status.SKIPPED}
                and not stage.steps[index].continue_on_error
            ):
                status = step_result.status
                break
        return StageResult(stage.name, status, steps)

    def _execute_step(
        self, config: MiniCIConfig, stage: StageConfig, step: StepConfig, run_log: RunLog
    ) -> StepResult:
        if not should_run(
            step.when,
            branch=self.git_info.branch,
            changed_paths=self.git_info.changed_paths,
        ):
            return StepResult(step.name, Status.SKIPPED)
        runner_config = step.runner or config.defaults.runner
        retry = step.retry or config.defaults.retry
        attempts: list[AttemptResult] = []
        for number in range(1, retry.max_attempts + 1):
            commands = []
            status = Status.SUCCESS
            for command in step.commands:
                environment = config.environment | config.defaults.environment
                environment |= stage.environment | step.environment | command.environment
                workdir = step.working_directory or stage.working_directory
                workdir = workdir or config.defaults.working_directory
                if runner_config.type == "docker":
                    result = self.docker_runner.execute(
                        command,
                        runner_config,
                        project_root=self.project_root,
                        environment=environment,
                        timeout=step.timeout or config.defaults.timeout,
                        cancel_event=self.cancel_event,
                    )
                else:
                    result = self.runner.execute(
                        command,
                        cwd=(self.project_root / workdir).resolve(),
                        environment=environment,
                        timeout=step.timeout or config.defaults.timeout,
                        cancel_event=self.cancel_event,
                    )
                commands.append(result)
                run_log.write_command(stage.name, step.name, result)
                if result.status is not Status.SUCCESS:
                    status = result.status
                    break
            attempts.append(AttemptResult(number, status, commands))
            if status is Status.SUCCESS:
                return StepResult(step.name, Status.SUCCESS, attempts)
            if status is Status.CANCELLED:
                return StepResult(step.name, Status.CANCELLED, attempts)
            if number < retry.max_attempts and retry.delay_seconds:
                time.sleep(retry.delay_seconds)
        return StepResult(step.name, attempts[-1].status, attempts)

    @staticmethod
    def _skipped_stage(stage: StageConfig) -> StageResult:
        return StageResult(
            stage.name,
            Status.SKIPPED,
            [StepResult(step.name, Status.SKIPPED) for step in stage.steps],
        )