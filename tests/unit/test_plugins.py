from minici.plugins import call_hook, discover_plugins


def test_no_plugins_by_default() -> None:
    assert discover_plugins() == []


def test_plugin_hook() -> None:
    calls = []

    class Plugin:
        name = "test"

        def before_run(self, project: str) -> None:
            calls.append(project)

    call_hook([Plugin()], "before_run", "demo")
    call_hook([Plugin()], "missing", "demo")
    assert calls == ["demo"]


def test_plugin_error_is_bounded() -> None:
    import pytest

    class Plugin:
        name = "broken"

        def before_run(self, project: str) -> None:
            raise ValueError("boom")

    with pytest.raises(RuntimeError, match="plugin broken"):
        call_hook([Plugin()], "before_run", "demo")
