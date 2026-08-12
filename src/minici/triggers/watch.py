"""File watch trigger with debounce and safe exclusions."""

import fnmatch
from pathlib import Path

from watchfiles import watch

DEFAULT_IGNORED = {".git", ".minici", ".venv", "__pycache__", "node_modules", "build", "dist"}


def changes(
    root: Path,
    debounce_ms: int = 800,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
):
    include = include or ["**/*"]
    exclude = exclude or []
    for batch in watch(root, debounce=debounce_ms, recursive=True):
        paths = [Path(path) for _, path in batch]
        filtered = []
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if DEFAULT_IGNORED.intersection(path.parts):
                continue
            if not any(fnmatch.fnmatch(relative, pattern) for pattern in include):
                continue
            if any(fnmatch.fnmatch(relative, pattern) for pattern in exclude):
                continue
            filtered.append(path)
        if filtered:
            yield filtered
