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


def test_select_words_reads_the_text_from_a_segment():
    rapid = _rapid(SelectWordsWorkflow(instruction="Select the wrong words"))

    assert rapid.t == "Transcription"
    assert rapid.title.literal == "Select the wrong words"
    assert rapid.transcription.segment == TRANSCRIPTION_SEGMENT_KEY


def test_select_words_requires_the_transcription_segment():
    workflow = SelectWordsWorkflow(instruction="Select the wrong words")
    transcription = next(
        s
        for s in build_schema(workflow._required_segments())
        if s.key == TRANSCRIPTION_SEGMENT_KEY
    )

    assert transcription.required is True


def test_schema_only_lists_the_workflow_segments_asked_for():
    keys = [s.key for s in build_schema(set())]

    assert TRANSCRIPTION_SEGMENT_KEY not in keys
    assert keys == ["asset", "context", "context_asset"]


def test_workflows_without_required_segments_keep_the_default_schema():
    assert LocateWorkflow(target="the cat")._required_segments() == set()
