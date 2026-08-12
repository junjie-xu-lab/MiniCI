from minici.config.models import WhenConfig
from minici.core.conditions import should_run


def test_platform_and_branch_conditions(monkeypatch) -> None:
    monkeypatch.setattr("minici.core.conditions.platform.system", lambda: "Windows")
    assert should_run(None)
    assert should_run(WhenConfig(platforms=["windows"], branches=["main"]), branch="main")
    assert not should_run(WhenConfig(platforms=["linux"]), branch="main")
    assert not should_run(WhenConfig(branches=["feature/*"]), branch="main")
    assert not should_run(WhenConfig(branches=["main"]), branch=None)
    assert should_run(WhenConfig(changed_paths=["src/**"]), changed_paths=("src/app.py",))
    assert not should_run(WhenConfig(changed_paths=["src/**"]), changed_paths=("README.md",))
