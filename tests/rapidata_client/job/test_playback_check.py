"""Job definition creation warns when a task needs more than 15 s of media playback.

Audio clips play one after the other, so they add up; videos count by the longest.
The check reads one page of datapoints back and never fails the creation.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.query_datapoints_by_dataset_id_endpoint_paged_result_of_output import (
    QueryDatapointsByDatasetIdEndpointPagedResultOfOutput,
)
from rapidata.rapidata_client.job._playback_check import (
    _parse_duration,
    playback_seconds,
    warn_long_playback,
)
from rapidata.api_client.models.i_asset import IAsset


def _file(seconds: str, video: bool) -> dict:
    return {
        "_t": "FileAsset",
        "fileName": "f.mp4" if video else "f.mp3",
        "identifier": "f",
        "metadata": {
            "streams": {
                "_t": "StreamsMetadata",
                "hasVideo": video,
                "hasAudio": True,
                "hasSubtitles": False,
            },
            "duration": {"_t": "VideoDurationMetadata", "duration": seconds},
        },
    }


def _multi(*files: dict) -> dict:
    return {
        "_t": "MultiAsset",
        "assets": list(files),
        "metadata": {},
        "identifier": "m",
    }


def _image() -> dict:
    return {"_t": "FileAsset", "fileName": "i.png", "identifier": "i", "metadata": {}}


def _page(*assets: dict) -> QueryDatapointsByDatasetIdEndpointPagedResultOfOutput:
    return QueryDatapointsByDatasetIdEndpointPagedResultOfOutput.from_dict(
        {
            "total": len(assets),
            "page": 1,
            "pageSize": 100,
            "items": [
                {
                    "id": f"dpt_{i}",
                    "datasetId": "dst_1",
                    "segments": [{"key": "asset", "kind": "Asset", "asset": a}],
                }
                for i, a in enumerate(assets)
            ],
        }
    )


def _service(page) -> MagicMock:
    svc = MagicMock()
    svc.dataset.datapoints_api.dataset_dataset_id_datapoints_get.return_value = page
    return svc


@pytest.mark.parametrize(
    "value, expected",
    [
        ("00:00:10", 10.0),
        ("00:00:10.2000000", 10.2),
        ("00:01:05.5", 65.5),
        ("1.00:00:00", 86400.0),
        ("garbage", None),
    ],
)
def test_parse_duration(value, expected):
    assert _parse_duration(value) == expected


@pytest.mark.parametrize(
    "asset, expected",
    [
        (_multi(_file("00:00:10", False), _file("00:00:10", False)), 20.0),
        (_multi(_file("00:00:05", True), _file("00:00:08", True)), 8.0),
        (_file("00:00:14", True), 14.0),
        (_image(), 0.0),
    ],
    ids=["audio pair adds up", "video pair counts longest", "single video", "image"],
)
def test_playback_seconds(asset, expected):
    assert playback_seconds([IAsset.from_dict(asset)]) == pytest.approx(expected)


def test_warns_on_audio_pair_over_budget(caplog):
    svc = _service(
        _page(
            _multi(_file("00:00:10", False), _file("00:00:10.2", False)),
            _multi(_file("00:00:04", False), _file("00:00:04", False)),
        )
    )

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        warn_long_playback(svc, "dst_1")

    assert "1 of 2 checked datapoint(s)" in caplog.text
    assert "20.2 s" in caplog.text


def test_silent_for_short_media(caplog):
    svc = _service(_page(_multi(_file("00:00:05", True), _file("00:00:05", True))))

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        warn_long_playback(svc, "dst_1")

    assert caplog.text == ""


def test_never_raises_when_the_read_fails(caplog):
    svc = MagicMock()
    svc.dataset.datapoints_api.dataset_dataset_id_datapoints_get.side_effect = (
        RuntimeError("boom")
    )

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        warn_long_playback(svc, "dst_1")

    assert caplog.text == ""
