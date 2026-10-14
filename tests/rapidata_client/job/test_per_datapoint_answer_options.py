"""Classification with a different list of answer options per datapoint."""

from __future__ import annotations

import pytest

from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.datapoints._default_segments import (
    ANSWER_OPTIONS_SEGMENT_KEY,
    build_default_segments,
    build_schema,
)
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
        s for s in build_schema(answer_options=True) if s.key == ANSWER_OPTIONS_SEGMENT_KEY
    )
    assert options.required is True


def test_per_datapoint_workflow_binds_categories_and_sends_no_fixed_list():
    model = ClassifyWorkflow(instruction="Pick one", answer_options=None)._to_model()
    simple = model.actual_instance

    assert simple.bindings is not None
    assert simple.bindings.payload["categories"].segment == ANSWER_OPTIONS_SEGMENT_KEY
    assert simple.blueprint.actual_instance.categories == []


def test_shared_options_workflow_is_unchanged():
    workflow = ClassifyWorkflow(instruction="Pick one", answer_options=["cat", "dog"])
    simple = workflow._to_model().actual_instance

    assert simple.bindings is None
    assert workflow._needs_answer_options_segment() is False
    assert [c.value for c in simple.blueprint.actual_instance.categories] == [
        "cat",
        "dog",
    ]
