"""Safe YAML loading and user-facing validation errors."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from minici.config.models import MiniCIConfig


class ConfigError(ValueError):
    """Raised when a MiniCI configuration cannot be loaded."""


def load_config(path: Path) -> MiniCIConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read configuration: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")
    try:
        return MiniCIConfig.model_validate(raw)
    except ValidationError as exc:
        messages = []
        for error in exc.errors(include_url=False):
            location = ".".join(str(part) for part in error["loc"])
            messages.append(f"{location}: {error['msg']}")
        raise ConfigError("configuration validation failed:\n- " + "\n- ".join(messages)) from exc
