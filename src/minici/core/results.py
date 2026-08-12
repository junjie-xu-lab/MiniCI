"""Execution result objects shared by all adapters."""

from dataclasses import dataclass, field
from datetime import datetime

from minici.core.status import Status


@dataclass(slots=True)
class CommandResult:
    command: str
    status: Status
    exit_code: int | None
    stdout: str
    stderr: str
    duration: float


@dataclass(slots=True)
class AttemptResult:
    number: int
    status: Status
    commands: list[CommandResult] = field(default_factory=list)


@dataclass(slots=True)
class StepResult:
    name: str
    status: Status
    attempts: list[AttemptResult] = field(default_factory=list)


@dataclass(slots=True)
class StageResult:
    name: str
    status: Status
    steps: list[StepResult] = field(default_factory=list)


@dataclass(slots=True)
class PipelineResult:
    project: str
    status: Status
    started_at: datetime
    ended_at: datetime
    stages: list[StageResult] = field(default_factory=list)
    run_id: int | None = None
    run_uid: str | None = None
