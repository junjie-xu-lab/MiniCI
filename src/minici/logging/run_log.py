"""Plain-text, append-only run log."""

from pathlib import Path
from threading import Lock

from minici.core.results import CommandResult


class RunLog:
    def __init__(self, path: Path, secrets: list[str] | None = None) -> None:
        self.path = path
        self.secrets = [value for value in (secrets or []) if len(value) >= 4]
        self._lock = Lock()

    def write_command(self, stage: str, step: str, result: CommandResult) -> None:
        parts = [
            f"[{stage} / {step}] $ {self.redact(result.command)}\n",
            self.redact(result.stdout),
            self.redact(result.stderr),
            f"\n[{result.status.value}] exit={result.exit_code} duration={result.duration:.3f}s\n",
        ]
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.writelines(parts)

    def redact(self, value: str) -> str:
        for secret in self.secrets:
            value = value.replace(secret, "***")
        return value
