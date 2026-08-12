"""Execution states and legal transitions."""

from enum import Enum


class Status(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    INTERRUPTED = "INTERRUPTED"


TERMINAL_STATUSES = {
    Status.SUCCESS,
    Status.FAILED,
    Status.SKIPPED,
    Status.CANCELLED,
    Status.TIMED_OUT,
    Status.INTERRUPTED,
}


def validate_transition(current: Status, target: Status) -> None:
    allowed = {
        Status.PENDING: {Status.RUNNING, Status.SKIPPED, Status.CANCELLED},
        Status.RUNNING: TERMINAL_STATUSES - {Status.SKIPPED},
    }
    if target not in allowed.get(current, set()):
        raise ValueError(f"illegal status transition: {current.value} -> {target.value}")
