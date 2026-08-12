from pathlib import Path

from minici.triggers.watch import changes


def test_watch_filters_generated_paths(tmp_path, monkeypatch) -> None:
    batches = [
        {
            (1, str(tmp_path / ".minici" / "run.log")),
            (1, str(tmp_path / "src" / "app.py")),
        }
    ]
    monkeypatch.setattr("minici.triggers.watch.watch", lambda *args, **kwargs: iter(batches))
    result = next(changes(tmp_path, include=["src/**"], exclude=["**/*.txt"]))
    assert result == [Path(tmp_path / "src" / "app.py")]
