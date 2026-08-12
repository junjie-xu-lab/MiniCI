"""Versioned plugin discovery through Python entry points."""

from importlib.metadata import entry_points
from typing import Protocol

PLUGIN_API_VERSION = 1


class MiniCIPlugin(Protocol):
    name: str
    api_version: int

    def before_run(self, project: str) -> None: ...

    def after_run(self, project: str, status: str) -> None: ...


def discover_plugins() -> list[MiniCIPlugin]:
    plugins = []
    for entry in entry_points(group="minici.plugins"):
        plugin = entry.load()()
        if plugin.api_version != PLUGIN_API_VERSION:
            raise RuntimeError(f"incompatible plugin API: {entry.name}")
        plugins.append(plugin)
    return plugins


def call_hook(plugins: list[MiniCIPlugin], hook: str, *args: str) -> None:
    for plugin in plugins:
        callback = getattr(plugin, hook, None)
        if callback is not None:
            try:
                callback(*args)
            except Exception as exc:
                raise RuntimeError(f"plugin {plugin.name} failed during {hook}: {exc}") from exc
