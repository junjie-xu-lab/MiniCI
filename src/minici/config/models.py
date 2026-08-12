"""Strict version 1 configuration models."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Shell(str, Enum):
    AUTO = "auto"
    CMD = "cmd"
    POWERSHELL = "powershell"
    SH = "sh"
    BASH = "bash"


class RetryConfig(StrictModel):
    max_attempts: Annotated[int, Field(ge=1, le=20)] = 1
    delay_seconds: Annotated[float, Field(ge=0, le=3600)] = 0


class LocalRunnerConfig(StrictModel):
    type: Literal["local"] = "local"


class DockerRunnerConfig(StrictModel):
    type: Literal["docker"]
    image: Annotated[str, Field(min_length=1)]
    pull: Literal["never", "if_missing", "always"] = "if_missing"
    network: str | None = None


RunnerConfig = Annotated[LocalRunnerConfig | DockerRunnerConfig, Field(discriminator="type")]


class WhenConfig(StrictModel):
    platforms: list[Literal["windows", "linux", "macos"]] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)


class CommandConfig(StrictModel):
    run: str | None = None
    argv: list[str] | None = None
    shell: Shell = Shell.AUTO
    timeout: Annotated[float | None, Field(gt=0, le=86400)] = None
    environment: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def exactly_one_command_form(self) -> CommandConfig:
        if (self.run is None) == (self.argv is None):
            raise ValueError("exactly one of 'run' or 'argv' is required")
        if self.run is not None and not self.run.strip():
            raise ValueError("'run' must not be empty")
        if self.argv is not None and (not self.argv or any(not item for item in self.argv)):
            raise ValueError("'argv' must contain non-empty arguments")
        if self.argv is not None and self.shell is not Shell.AUTO:
            raise ValueError("'shell' can only be used with 'run'")
        return self

    def display(self) -> str:
        return self.run if self.run is not None else " ".join(self.argv or [])


class ExecutionDefaults(StrictModel):
    runner: RunnerConfig = Field(default_factory=LocalRunnerConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    timeout: Annotated[float, Field(gt=0, le=86400)] = 600
    environment: dict[str, str] = Field(default_factory=dict)
    working_directory: str = "."


class StepConfig(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    commands: Annotated[list[CommandConfig], Field(min_length=1)]
    runner: RunnerConfig | None = None
    retry: RetryConfig | None = None
    timeout: Annotated[float | None, Field(gt=0, le=86400)] = None
    environment: dict[str, str] = Field(default_factory=dict)
    working_directory: str | None = None
    continue_on_error: bool = False
    when: WhenConfig | None = None


class StageConfig(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    steps: Annotated[list[StepConfig], Field(min_length=1)]
    parallel: bool = False
    fail_fast: bool = True
    environment: dict[str, str] = Field(default_factory=dict)
    working_directory: str | None = None

    @model_validator(mode="after")
    def unique_step_names(self) -> StageConfig:
        names = [step.name for step in self.steps]
        if len(names) != len(set(names)):
            raise ValueError("step names must be unique within a stage")
        return self


class ProjectConfig(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]


class SecretsConfig(StrictModel):
    from_environment: list[str] = Field(default_factory=list)


class WatchConfig(StrictModel):
    include: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude: list[str] = Field(default_factory=list)
    debounce_ms: Annotated[int, Field(ge=100, le=60000)] = 800


class TriggersConfig(StrictModel):
    watch: WatchConfig | None = None


class MiniCIConfig(StrictModel):
    version: Literal[1]
    project: ProjectConfig
    defaults: ExecutionDefaults = Field(default_factory=ExecutionDefaults)
    environment: dict[str, str] = Field(default_factory=dict)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    triggers: TriggersConfig = Field(default_factory=TriggersConfig)
    stages: Annotated[list[StageConfig], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_stage_names(self) -> MiniCIConfig:
        names = [stage.name for stage in self.stages]
        if len(names) != len(set(names)):
            raise ValueError("stage names must be unique")
        return self

    def resolved_steps(self, project_root: Path) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for stage in self.stages:
            for step in stage.steps:
                runner = step.runner or self.defaults.runner
                retry = step.retry or self.defaults.retry
                workdir = step.working_directory or stage.working_directory
                workdir = workdir or self.defaults.working_directory
                result.append(
                    {
                        "stage": stage.name,
                        "step": step.name,
                        "parallel": stage.parallel,
                        "runner": runner.type,
                        "working_directory": str((project_root / workdir).resolve()),
                        "timeout": step.timeout or self.defaults.timeout,
                        "max_attempts": retry.max_attempts,
                        "commands": [command.display() for command in step.commands],
                    }
                )
        return result
