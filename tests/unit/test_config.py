from pathlib import Path

import pytest

from minici.config.loader import ConfigError, load_config

VALID = """version: 1
project: {name: demo}
stages:
  - name: quality
    steps:
      - name: test
        commands:
          - argv: [python, -m, pytest]
"""


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "minici.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_config(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, VALID))
    assert config.project.name == "demo"
    assert config.stages[0].steps[0].commands[0].argv == ["python", "-m", "pytest"]


@pytest.mark.parametrize(
    "content, message",
    [
        ("- not-a-map", "root must be a mapping"),
        ("version: 2\nproject: {name: x}\nstages: []", "version"),
        (VALID + "unknown: true\n", "unknown"),
        (VALID.replace("argv: [python, -m, pytest]", "run: ''"), "must not be empty"),
        (VALID.replace("name: quality", "name: quality\n    unknown: true"), "unknown"),
        ("version: [", "invalid YAML"),
        (
            VALID.replace("argv: [python, -m, pytest]", "argv: [python]\n            shell: bash"),
            "shell",
        ),
    ],
)
def test_invalid_config(tmp_path: Path, content: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, content))


def test_missing_config(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.yml")


def test_resolved_values(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, VALID))
    resolved = config.resolved_steps(tmp_path)
    assert resolved[0]["runner"] == "local"
    assert resolved[0]["max_attempts"] == 1
    assert resolved[0]["working_directory"] == str(tmp_path.resolve())


def test_duplicate_names_are_rejected(tmp_path: Path) -> None:
    duplicate = VALID.replace(
        "  - name: quality",
        "  - name: quality\n    steps:\n      - name: one\n        commands:\n"
        "          - argv: [python]\n  - name: quality",
    )
    with pytest.raises(ConfigError, match="stage names must be unique"):
        load_config(write(tmp_path, duplicate))
