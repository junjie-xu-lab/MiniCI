"""Safe, structured step condition evaluation."""

import fnmatch
import platform

from minici.config.models import WhenConfig


def should_run(
    when: WhenConfig | None,
    *,
    branch: str | None = None,
    changed_paths: tuple[str, ...] = (),
) -> bool:
    if when is None:
        return True
    current_platform = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(
        platform.system(), platform.system().lower()
    )
    if when.platforms and current_platform not in when.platforms:
        return False
    if when.changed_paths and not any(
        fnmatch.fnmatch(path, pattern) for path in changed_paths for pattern in when.changed_paths
    ):
        return False
    return not when.branches or (
        branch is not None and any(fnmatch.fnmatch(branch, item) for item in when.branches)
    )
