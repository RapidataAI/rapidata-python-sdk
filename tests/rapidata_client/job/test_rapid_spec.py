"""Every simple workflow sends a typed rapid, never the deprecated blueprint."""

from __future__ import annotations

from rapidata.rapidata_client.datapoints._default_segments import (
    TRANSCRIPTION_SEGMENT_KEY,
)
from rapidata.rapidata_client.workflow import (
    ClassifyWorkflow,
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


def test_classify_sends_its_options_as_a_literal():
    rapid = _rapid(
        ClassifyWorkflow(instruction="Pick one", answer_options=["cat", "dog"])
    )

    assert rapid.t == "Classify"
    assert rapid.title.literal == "Pick one"
    assert [o.value for o in rapid.categories.literal] == ["cat", "dog"]
    assert rapid.categories.segment is None
