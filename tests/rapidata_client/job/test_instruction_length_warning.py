from __future__ import annotations

import logging

import pytest

from rapidata.rapidata_client.workflow._base_workflow import (
    MAX_INSTRUCTION_LENGTH,
    RECOMMENDED_INSTRUCTION_LENGTH,
    validate_instruction_length,
)
from rapidata.rapidata_client.workflow._classify_workflow import ClassifyWorkflow
from rapidata.rapidata_client.workflow._compare_workflow import CompareWorkflow


def _warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_instruction_at_recommended_length_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING):
        CompareWorkflow(instruction="a" * RECOMMENDED_INSTRUCTION_LENGTH)

    assert _warnings(caplog) == []


def test_instruction_over_recommended_length_warns(caplog):
    instruction = "Imagine each voice is a tutor. Which one would you rather listen to for a whole lesson?"

    with caplog.at_level(logging.WARNING):
        ClassifyWorkflow(instruction=instruction)

    [message] = _warnings(caplog)
    assert f"is {len(instruction)} characters; keep it under 80" in message
    assert "one criterion" in message
    assert instruction in message


def test_instruction_over_maximum_raises_without_warning(caplog):
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError):
        validate_instruction_length("a" * (MAX_INSTRUCTION_LENGTH + 1))

    assert _warnings(caplog) == []
