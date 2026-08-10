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


def _file_sample(identifier: str, original_filename: str) -> MagicMock:
    """A server sample for an uploaded local file."""
    metadata = {
        "originalFilename": MagicMock(
            actual_instance=MagicMock(original_filename=original_filename)
        )
    }
    asset = MagicMock(actual_instance=MagicMock(text=None, metadata=metadata))
    return MagicMock(actual_instance=MagicMock(identifier=identifier, asset=asset))


def _url_sample(identifier: str, url: str) -> MagicMock:
    """A server sample for an asset ingested from a remote URL."""
    metadata = {"sourceUrl": MagicMock(actual_instance=MagicMock(url=url))}
    asset = MagicMock(actual_instance=MagicMock(text=None, metadata=metadata))
    return MagicMock(actual_instance=MagicMock(identifier=identifier, asset=asset))


def _unreadable_sample(identifier: str) -> MagicMock:
    """A server sample whose asset shape yields no comparable key."""
    asset = MagicMock(actual_instance=MagicMock(text=None, metadata=None))
    return MagicMock(actual_instance=MagicMock(identifier=identifier, asset=asset))


def _page(samples: list[MagicMock], total_pages: int) -> MagicMock:
    page = MagicMock()
    page.total_pages = total_pages
    page.items = samples
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
    samples_get = _serve(
        participant,
        [
            _page([_file_sample("a", "a.jpg"), _file_sample("b", "b.jpg")], 2),
            _page([_file_sample("b", "b2.jpg")], 2),
        ],
    )

    counts = participant._uploaded_sample_keys()

    assert counts == Counter({("a", "a.jpg"): 1, ("b", "b.jpg"): 1, ("b", "b2.jpg"): 1})
    assert [c.kwargs["page"] for c in samples_get.call_args_list] == [1, 2]
    for call in samples_get.call_args_list:
        assert call.kwargs["page_size"] <= 100


def test_raises_when_total_pages_missing():
    participant = _participant()
    _serve(participant, [_page([_file_sample("a", "a.jpg")], None)])

    try:
        participant._uploaded_sample_keys()
    except ValueError as e:
        assert "total_pages" in str(e)
    else:
        raise AssertionError("expected a ValueError when total_pages is None")


def test_missing_samples_returns_only_absent_pairs():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "a.jpg"): 1, ("c", "c.jpg"): 1})
    )

    missing = participant.missing_samples(["a.jpg", "b.jpg", "c.jpg"], ["a", "b", "c"])

    assert missing == [SampleUpload(media="b.jpg", identifier="b")]


def test_missing_samples_identifies_which_asset_is_absent():
    # The regression this guards: with several distinct assets under one
    # identifier, counting samples per identifier says only "one of three
    # landed" — not which. Matching on the asset re-uploads the right one.
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "a2.jpg"): 1})
    )

    missing = participant.missing_samples(
        ["a1.jpg", "a2.jpg", "a3.jpg"], ["a", "a", "a"]
    )

    assert missing == [
        SampleUpload(media="a1.jpg", identifier="a"),
        SampleUpload(media="a3.jpg", identifier="a"),
    ]


def test_missing_samples_matches_local_files_by_basename():
    # The server reports a local upload as its bare originalFilename, so the
    # caller's directory prefix must not defeat the match.
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "1.png"): 1})
    )

    assert participant.missing_samples(["run/a/1.png"], ["a"]) == []


def test_missing_samples_matches_urls_verbatim():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "https://host/1.png"): 1})
    )

    assert participant.missing_samples(["https://host/1.png"], ["a"]) == []


def test_missing_samples_matches_text_by_content():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "some text"): 1})
    )

    assert participant.missing_samples(["some text"], ["a"], data_type="text") == []


def test_missing_samples_counts_a_repeated_asset_individually():
    # The same media supplied twice for one identifier needs two samples.
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "a1.jpg"): 1})
    )

    missing = participant.missing_samples(["a1.jpg", "a1.jpg"], ["a", "a"])

    assert missing == [SampleUpload(media="a1.jpg", identifier="a")]


def test_missing_samples_treats_unreadable_server_assets_as_present():
    # Better to leave a sample unsent and report it than to duplicate one: a
    # duplicate silently over-weights the prompt in matchup sampling.
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", None): 1})
    )

    assert participant.missing_samples(["a1.jpg"], ["a"]) == []


def test_missing_samples_empty_when_server_has_everything():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "1.jpg"): 1, ("a", "2.jpg"): 1, ("b", "3.jpg"): 1})
    )

    assert (
        participant.missing_samples(["1.jpg", "2.jpg", "3.jpg"], ["a", "a", "b"]) == []
    )


def test_server_asset_key_reads_each_asset_shape():
    key = BenchmarkParticipant._server_asset_key
    assert key(_file_sample("a", "a.jpg").actual_instance.asset) == "a.jpg"
    assert key(_url_sample("a", "https://h/a.jpg").actual_instance.asset) == (
        "https://h/a.jpg"
    )
    assert key(_unreadable_sample("a").actual_instance.asset) is None
    assert key(None) is None


def test_retry_missing_skips_upload_when_nothing_is_missing():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "a.jpg"): 1})
    )
    participant.upload_media = MagicMock()

    successful, failed = participant.retry_missing(["a.jpg"], ["a"])

    participant.upload_media.assert_not_called()
    assert successful == []
    assert failed == []


def test_retry_missing_reuploads_only_the_difference():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(
        return_value=Counter({("a", "a.jpg"): 1})
    )
    participant.upload_media = MagicMock(return_value=(["b"], []))

    participant.retry_missing(["a.jpg", "b.jpg"], ["a", "b"])

    args, _ = participant.upload_media.call_args
    assert args[0] == ["b.jpg"]
    assert args[1] == ["b"]


def test_retry_missing_rejects_mismatched_lengths():
    participant = _participant()
    participant._uploaded_sample_keys = MagicMock(return_value=Counter())

    try:
        participant.retry_missing(["a.jpg", "b.jpg"], ["a"])
    except ValueError as e:
        assert "same length" in str(e)
    else:
        raise AssertionError("expected a ValueError for mismatched lengths")
