"""Tests for the recovery path on a benchmark participant.

Deduplication lives in the backend: it rejects a sample the participant already
holds for an identifier and asset. That lets the client stay simple — ask which
identifiers are short, re-send everything belonging to them, and let the server
turn away the ones that already landed. The client never has to work out *which*
asset of an identifier is the missing one.
"""

from __future__ import annotations

from collections import Counter
from unittest.mock import MagicMock

from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.benchmark.participant.sample_upload import SampleUpload
from rapidata.rapidata_client.datapoints._asset_mapper import AssetMapper
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError


def _participant() -> BenchmarkParticipant:
    return BenchmarkParticipant(
        name="model",
        id="participant-1",
        openapi_service=MagicMock(),
        benchmark_id="benchmark-1",
    )


def _page(identifiers: list[str], total_pages: int | None) -> MagicMock:
    page = MagicMock()
    page.total_pages = total_pages
    page.items = [
        MagicMock(actual_instance=MagicMock(identifier=i)) for i in identifiers
    ]
    return page


def _serve(participant: BenchmarkParticipant, pages: list[MagicMock]) -> MagicMock:
    samples_get = (
        participant._openapi_service.leaderboard.sample_api.participant_participant_id_samples_get
    )
    samples_get.side_effect = pages
    return samples_get


def test_pages_within_the_server_page_limit():
    # The backend rejects a page_size above its MaxPageSize (100) instead of
    # clamping it, so every page request must stay at or below that.
    participant = _participant()
    samples_get = _serve(participant, [_page(["a", "b"], 2), _page(["b"], 2)])

    counts = participant._uploaded_identifier_counts()

    assert counts == Counter({"a": 1, "b": 2})
    assert [c.kwargs["page"] for c in samples_get.call_args_list] == [1, 2]
    for call in samples_get.call_args_list:
        assert call.kwargs["page_size"] <= 100


def test_raises_when_total_pages_missing():
    participant = _participant()
    _serve(participant, [_page(["a"], None)])

    try:
        participant._uploaded_identifier_counts()
    except ValueError as e:
        assert "total_pages" in str(e)
    else:
        raise AssertionError("expected a ValueError when total_pages is None")


def test_missing_counts_reports_the_shortfall_per_identifier():
    participant = _participant()
    participant._uploaded_identifier_counts = MagicMock(
        return_value=Counter({"a": 1, "b": 2})
    )

    # Three samples intended for "a", two for "b", one for "c".
    missing = participant.missing_counts(["a", "a", "a", "b", "b", "c"])

    assert missing == Counter({"a": 2, "c": 1})


def test_missing_counts_is_empty_when_everything_is_present():
    participant = _participant()
    participant._uploaded_identifier_counts = MagicMock(
        return_value=Counter({"a": 2, "b": 1})
    )

    assert participant.missing_counts(["a", "a", "b"]) == Counter()


def test_missing_counts_ignores_extra_server_samples():
    participant = _participant()
    participant._uploaded_identifier_counts = MagicMock(return_value=Counter({"a": 5}))

    assert participant.missing_counts(["a"]) == Counter()


def test_already_present_sample_counts_as_uploaded():
    # The backend's 409 is the success case for a retry, not a failure — and it
    # must not be retried, since re-sending would only be rejected again.
    participant = _participant()
    participant._asset_uploader = MagicMock()
    participant._asset_uploader.build_asset_input.return_value = (
        AssetMapper.create_text_input("content")
    )
    sample_post = (
        participant._openapi_service.leaderboard.participant_api.participant_participant_id_sample_post
    )
    sample_post.side_effect = RapidataError(status_code=409, message="already exists")

    failure = participant._process_single_sample_upload("a.jpg", "a")

    assert failure is None
    assert sample_post.call_count == 1


def test_other_errors_still_fail_after_retries():
    participant = _participant()
    participant._asset_uploader = MagicMock()
    participant._asset_uploader.build_asset_input.return_value = (
        AssetMapper.create_text_input("content")
    )
    sample_post = (
        participant._openapi_service.leaderboard.participant_api.participant_participant_id_sample_post
    )
    sample_post.side_effect = RapidataError(status_code=500, message="boom")

    failure = participant._process_single_sample_upload("a.jpg", "a")

    assert failure is not None
    assert failure.item == SampleUpload(media="a.jpg", identifier="a")
    assert sample_post.call_count > 1


def test_retry_missing_resends_every_asset_of_a_short_identifier():
    # The client cannot tell which of an identifier's assets is missing, so it
    # sends them all and lets the backend reject the ones already there.
    participant = _participant()
    participant.missing_counts = MagicMock(
        side_effect=[Counter({"a": 1}), Counter(), Counter()]
    )
    participant.upload_media = MagicMock(return_value=(["a", "a"], []))

    successful, failed = participant.retry_missing(
        ["a1.jpg", "a2.jpg", "b1.jpg"], ["a", "a", "b"]
    )

    args, _ = participant.upload_media.call_args
    assert args[0] == ["a1.jpg", "a2.jpg"]
    assert args[1] == ["a", "a"]
    assert successful == ["a", "a"]
    assert failed == []


def test_retry_missing_skips_upload_when_nothing_is_short():
    participant = _participant()
    participant.missing_counts = MagicMock(return_value=Counter())
    participant.upload_media = MagicMock()

    successful, failed = participant.retry_missing(["a.jpg"], ["a"])

    participant.upload_media.assert_not_called()
    assert successful == []
    assert failed == []


def test_retry_missing_stops_when_a_round_makes_no_progress():
    # A sample the server keeps refusing must not spin here.
    participant = _participant()
    participant.missing_counts = MagicMock(return_value=Counter({"a": 1}))
    participant.upload_media = MagicMock(return_value=([], []))

    participant.retry_missing(["a.jpg"], ["a"])

    assert participant.upload_media.call_count == 1


def test_retry_missing_rejects_mismatched_lengths():
    participant = _participant()

    try:
        participant.retry_missing(["a.jpg", "b.jpg"], ["a"])
    except ValueError as e:
        assert "same length" in str(e)
    else:
        raise AssertionError("expected a ValueError for mismatched lengths")
