import pytest

from minici.core.status import Status, validate_transition


def test_valid_transition() -> None:
    validate_transition(Status.PENDING, Status.RUNNING)
    validate_transition(Status.RUNNING, Status.SUCCESS)


def test_invalid_transition() -> None:
    with pytest.raises(ValueError, match="illegal"):
        validate_transition(Status.SUCCESS, Status.RUNNING)
