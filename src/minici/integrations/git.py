"""Read-only Git metadata discovery."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitInfo:
    available: bool
    branch: str | None = None
    commit: str | None = None
    dirty: bool = False
    changed_paths: tuple[str, ...] = ()


def inspect_git(root: Path) -> GitInfo:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        status = run("status", "--porcelain")
        paths = tuple(line[3:].strip().replace("\\", "/") for line in status.splitlines())
        return GitInfo(
            True,
            run("branch", "--show-current") or None,
            run("rev-parse", "HEAD"),
            bool(status),
            paths,
        )
    except (OSError, subprocess.SubprocessError):
        return GitInfo(False)
