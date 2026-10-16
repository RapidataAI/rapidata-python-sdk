"""Every simple workflow sends a typed rapid, never the deprecated blueprint."""

from __future__ import annotations

from rapidata.rapidata_client.datapoints._default_segments import (
    TRANSCRIPTION_SEGMENT_KEY,
    build_schema,
)
from rapidata.rapidata_client.workflow import (
    CompareWorkflow,
    FreeTextWorkflow,
    LocateWorkflow,
    SelectWordsWorkflow,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow


def _rapid(workflow: Workflow):
    return workflow._to_model().actual_instance.rapid.actual_instance


def test_locate_sends_the_target_as_a_literal():
    rapid = _rapid(LocateWorkflow(target="the cat"))

    assert rapid.t == "Locate"
    assert rapid.asset.segment == "asset"
    assert rapid.target.literal == "the cat"


def test_compare_keeps_its_index_identifiers():
    rapid = _rapid(
        CompareWorkflow(instruction="Which is better?", a_b_names=["A", "B"])
    )

    assert rapid.t == "Compare"
    assert rapid.criteria.literal == "Which is better?"
    assert rapid.index_identifiers == ["A", "B"]


def test_free_text_sends_the_question_as_a_literal():
    rapid = _rapid(FreeTextWorkflow(instruction="Describe it"))

    assert rapid.t == "FreeText"
    assert rapid.question.literal == "Describe it"


def test_select_words_reads_the_text_from_a_required_segment():
    workflow = SelectWordsWorkflow(instruction="Select the wrong words")
    rapid = _rapid(workflow)

    assert rapid.t == "Transcription"
    assert rapid.transcription.segment == TRANSCRIPTION_SEGMENT_KEY
    transcription = next(
        s
        for s in build_schema(workflow._required_segments())
        if s.key == TRANSCRIPTION_SEGMENT_KEY
    )
    assert transcription.required is True
