"""Cross-platform local subprocess runner."""

import os
import signal
import subprocess
import time
from pathlib import Path
from threading import Event

from minici.config.models import CommandConfig, Shell
from minici.core.results import CommandResult
from minici.core.status import Status


class LocalRunner:
    def execute(
        self,
        command: CommandConfig,
        *,
        cwd: Path,
        environment: dict[str, str],
        timeout: float,
        cancel_event: Event | None = None,
    ) -> CommandResult:
        started = time.monotonic()
        args, use_shell = self._arguments(command)
        env = os.environ.copy()
        env.update(environment)
        try:
            process = subprocess.Popen(
                args,
                cwd=cwd,
                env=env,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
                start_new_session=os.name != "nt",
            )
            limit = command.timeout or timeout
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=min(0.1, limit))
                    break
                except subprocess.TimeoutExpired:
                    limit -= 0.1
                    if cancel_event is not None and cancel_event.is_set():
                        self._terminate_tree(process)
                        stdout, stderr = process.communicate()
                        return CommandResult(
                            command.display(),
                            Status.CANCELLED,
                            None,
                            stdout,
                            stderr,
                            time.monotonic() - started,
                        )
                    if limit <= 0:
                        raise
            status = Status.SUCCESS if process.returncode == 0 else Status.FAILED
            return CommandResult(
                command.display(),
                status,
                process.returncode,
                stdout,
                stderr,
                time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as exc:
            self._terminate_tree(process)
            stdout, stderr = process.communicate()
            return CommandResult(
                command.display(),
                Status.TIMED_OUT,
                None,
                self._text(exc.stdout) or stdout,
                self._text(exc.stderr) or stderr,
                time.monotonic() - started,
            )
        except OSError as exc:
            return CommandResult(
                command.display(),
                Status.FAILED,
                None,
                "",
                str(exc),
                time.monotonic() - started,
            )

    @staticmethod
    def _terminate_tree(process: subprocess.Popen[str]) -> None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)

    @staticmethod
    def _text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value

    @staticmethod
    def _arguments(command: CommandConfig) -> tuple[str | list[str], bool]:
        if command.argv is not None:
            return command.argv, False
        if command.shell is Shell.POWERSHELL:
            return ["powershell", "-NoProfile", "-Command", command.run or ""], False
        if command.shell is Shell.CMD:
            return ["cmd", "/d", "/s", "/c", command.run or ""], False
        if command.shell in {Shell.SH, Shell.BASH}:
            return [command.shell.value, "-c", command.run or ""], False
        return command.run or "", True
