"""The flat datapoint fields are stripped from the generated client, so the SDK
sends them as segments under the backend's default dataset schema keys."""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.api_client.models.dataset_segment_kind import DatasetSegmentKind
from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_asset_input_existing_asset_input import (
    IAssetInputExistingAssetInput,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.datapoints._datapoint_uploader import (
    DatapointUploader,
)


def _mapped(name: str) -> IAssetInput:
    return IAssetInput(
        actual_instance=IAssetInputExistingAssetInput(
            _t="ExistingAssetInput", name=name
        )
    )


def _upload(datapoint: Datapoint):
    uploader = DatapointUploader(MagicMock())
    uploader.asset_uploader = MagicMock()
    uploader.asset_uploader.build_asset_input.return_value = _mapped("main")
    uploader.asset_uploader.upload_and_map_asset.return_value = _mapped("ctx")

    uploader.upload_datapoint(datapoint, "ds-1", 3)

    post = (
        uploader.openapi_service.dataset.datapoints_api.dataset_dataset_id_datapoint_post
    )
    post.assert_called_once()
    return post.call_args.kwargs["create_datapoint_endpoint_input"]


def test_context_fields_map_to_the_default_segment_keys() -> None:
    payload = _upload(
        Datapoint(
            asset="https://example.com/a.png",
            data_type="media",
            context="which is nicer?",
            media_context=["https://example.com/ref.png"],
        )
    )

    assert [(s.key, s.kind) for s in payload.segments] == [
        ("asset", DatasetSegmentKind.ASSET),
        ("context", DatasetSegmentKind.TEXT),
        ("context_asset", DatasetSegmentKind.ASSET),
    ]
    assert payload.segments[1].text == "which is nicer?"
    assert payload.sort_index == 3


def test_sentence_maps_to_the_transcription_segment() -> None:
    payload = _upload(
        Datapoint(
            asset="https://example.com/a.mp3",
            data_type="media",
            sentence="a red car",
        )
    )

    assert [(s.key, s.kind) for s in payload.segments] == [
        ("asset", DatasetSegmentKind.ASSET),
        ("transcription", DatasetSegmentKind.TEXT),
    ]
    assert payload.segments[1].text == "a red car"


def test_absent_fields_send_no_segment() -> None:
    payload = _upload(Datapoint(asset="https://example.com/a.png", data_type="media"))

    assert [s.key for s in payload.segments] == ["asset"]


def test_grouped_datapoint_leaves_context_to_the_group() -> None:
    payload = _upload(
        Datapoint(
            asset="https://example.com/a.png",
            data_type="media",
            context="shown once per group",
            media_context=["https://example.com/ref.png"],
            group="g1",
        )
    )

    assert [s.key for s in payload.segments] == ["asset"]
    assert payload.group == "g1"
