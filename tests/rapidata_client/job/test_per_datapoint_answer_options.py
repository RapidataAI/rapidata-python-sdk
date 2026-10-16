"""Classification with a different list of answer options per datapoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.datapoints._default_segments import (
    ANSWER_OPTIONS_SEGMENT_KEY,
    build_default_segments,
    build_schema,
)
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager
from rapidata.rapidata_client.workflow import ClassifyWorkflow


def test_map_datapoints_attaches_each_list_to_its_datapoint():
    datapoints = DatapointsValidator.map_datapoints(
        datapoints=["a", "b"],
        answer_options=[["cat", "dog"], ["red", "green", "blue"]],
        data_type="text",
    )

    assert [d.answer_options for d in datapoints] == [
        ["cat", "dog"],
        ["red", "green", "blue"],
    ]


@pytest.mark.parametrize(
    "answer_options",
    [
        [["cat", "dog"]],
        [["cat"], ["red", "green"]],
        [["cat", "cat"], ["red", "green"]],
        [["cat", ""], ["red", "green"]],
    ],
)
def test_map_datapoints_rejects_invalid_lists(answer_options: list[list[str]]):
    with pytest.raises(ValueError):
        DatapointsValidator.map_datapoints(
            datapoints=["a", "b"], answer_options=answer_options
        )


def test_answer_options_go_up_as_an_option_list_segment():
    segments = build_default_segments(answer_options=["cat", "dog"])

    assert len(segments) == 1
    assert segments[0].key == ANSWER_OPTIONS_SEGMENT_KEY
    assert [o.value for o in segments[0].options or []] == ["cat", "dog"]


def test_schema_requires_the_answer_options_segment_only_when_asked():
    assert ANSWER_OPTIONS_SEGMENT_KEY not in [s.key for s in build_schema()]
    options = next(
        s
        for s in build_schema({ANSWER_OPTIONS_SEGMENT_KEY})
        if s.key == ANSWER_OPTIONS_SEGMENT_KEY
    )
    assert options.required is True


def test_classify_sends_a_rapid_with_options_read_per_datapoint():
    workflow = ClassifyWorkflow(instruction="Pick one")
    rapid = workflow._to_model().actual_instance.rapid.actual_instance

    assert workflow._required_segments() == {ANSWER_OPTIONS_SEGMENT_KEY}
    assert rapid.t == "Classify"
    assert rapid.asset.segment == "asset"
    assert rapid.title.literal == "Pick one"
    assert rapid.categories.segment == ANSWER_OPTIONS_SEGMENT_KEY


@pytest.mark.parametrize(
    ("answer_options", "expected"),
    [
        (["cat", "dog"], [["cat", "dog"], ["cat", "dog"]]),
        ([["cat", "dog"], ["red", "green"]], [["cat", "dog"], ["red", "green"]]),
    ],
)
def test_classification_job_puts_options_on_every_datapoint(
    answer_options: list[str] | list[list[str]], expected: list[list[str]]
):
    manager = RapidataJobManager(MagicMock())
    with patch.object(manager, "_create_general_job_definition") as create:
        manager.create_classification_job_definition(
            name="n",
            instruction="Pick one",
            answer_options=answer_options,
            datapoints=["a", "b"],
            data_type="text",
        )

    datapoints = create.call_args.kwargs["datapoints"]
    assert [d.answer_options for d in datapoints] == expected
