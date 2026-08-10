"""Tests for the server-diff recovery path on a benchmark participant.

`retry_missing` exists so a partially-failed upload can be finished without
re-sending samples the server already has: a request can time out *after* the
sample was persisted, and a blind retry would give that identifier a second
sample and over-weight the prompt in matchup sampling.
"""

from __future__ import annotations

from collections import Counter
from unittest.mock import MagicMock

from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.benchmark.participant.sample_upload import SampleUpload


def _participant() -> BenchmarkParticipant:
    return BenchmarkParticipant(
        name="model",
        id="participant-1",
        openapi_service=MagicMock(),
        benchmark_id="benchmark-1",
    )


def test_select_missing_returns_only_absent_pairs():
    participant = _participant()
    participant.uploaded_identifier_counts = MagicMock(return_value=Counter(["a", "c"]))

    missing = participant._select_missing(["a.jpg", "b.jpg", "c.jpg"], ["a", "b", "c"])

    assert missing == [SampleUpload(media="b.jpg", identifier="b")]


def test_select_missing_counts_repeated_identifiers_individually():
    # The same prompt may legitimately be supplied several times, so a set-based
    # diff would wrongly treat one uploaded sample as satisfying both.
    participant = _participant()
    participant.uploaded_identifier_counts = MagicMock(return_value=Counter(["a"]))

    missing = participant._select_missing(["a1.jpg", "a2.jpg"], ["a", "a"])

    assert missing == [SampleUpload(media="a2.jpg", identifier="a")]


def test_select_missing_empty_when_server_has_everything():
    participant = _participant()
    participant.uploaded_identifier_counts = MagicMock(
        return_value=Counter(["a", "a", "b"])
    )

    assert (
        participant._select_missing(["1.jpg", "2.jpg", "3.jpg"], ["a", "a", "b"]) == []
    )


def test_retry_missing_skips_upload_when_nothing_is_missing():
    participant = _participant()
    participant.uploaded_identifier_counts = MagicMock(return_value=Counter(["a"]))
    participant.upload_media = MagicMock()

    successful, failed = participant.retry_missing(["a.jpg"], ["a"])

    participant.upload_media.assert_not_called()
    assert successful == []
    assert failed == []


def test_retry_missing_reuploads_only_the_difference():
    participant = _participant()
    participant.uploaded_identifier_counts = MagicMock(return_value=Counter(["a"]))
    participant.upload_media = MagicMock(return_value=(["b"], []))

    participant.retry_missing(["a.jpg", "b.jpg"], ["a", "b"])

    args, _ = participant.upload_media.call_args
    assert args[0] == ["b.jpg"]
    assert args[1] == ["b"]


def test_retry_missing_rejects_mismatched_lengths():
    participant = _participant()
    participant.uploaded_identifier_counts = MagicMock(return_value=Counter())

    try:
        participant.retry_missing(["a.jpg", "b.jpg"], ["a"])
    except ValueError as e:
        assert "same length" in str(e)
    else:
        raise AssertionError("expected a ValueError for mismatched lengths")
