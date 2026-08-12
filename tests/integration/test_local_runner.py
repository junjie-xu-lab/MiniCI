import sys
from threading import Event

from minici.config.models import CommandConfig
from minici.core.status import Status
from minici.runners.local import LocalRunner


def test_runner_success_and_output(tmp_path) -> None:
    result = LocalRunner().execute(
        CommandConfig(argv=[sys.executable, "-c", "print('hello')"]),
        cwd=tmp_path,
        environment={},
        timeout=5,
    )
    assert result.status is Status.SUCCESS
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0


def test_runner_failure(tmp_path) -> None:
    result = LocalRunner().execute(
        CommandConfig(argv=[sys.executable, "-c", "import sys;sys.exit(7)"]),
        cwd=tmp_path,
        environment={},
        timeout=5,
    )
    assert result.status is Status.FAILED
    assert result.exit_code == 7


def test_runner_timeout(tmp_path) -> None:
    result = LocalRunner().execute(
        CommandConfig(argv=[sys.executable, "-c", "import time;time.sleep(2)"]),
        cwd=tmp_path,
        environment={},
        timeout=0.05,
    )
    assert result.status is Status.TIMED_OUT


def test_runner_cancellation(tmp_path) -> None:
    event = Event()
    event.set()
    result = LocalRunner().execute(
        CommandConfig(argv=[sys.executable, "-c", "import time;time.sleep(2)"]),
        cwd=tmp_path,
        environment={},
        timeout=5,
        cancel_event=event,
    )
    assert result.status is Status.CANCELLED
