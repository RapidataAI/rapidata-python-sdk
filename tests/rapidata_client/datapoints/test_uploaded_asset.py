"""An ``UploadedAsset`` is sent as an ``ExistingAssetInput`` by its name and never uploaded again."""

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.asset_type import AssetType
from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_asset_input_existing_asset_input import (
    IAssetInputExistingAssetInput,
)
from rapidata.api_client.models.i_asset_input_multi_asset_input import (
    IAssetInputMultiAssetInput,
)
from rapidata.api_client.models.i_validation_truth import IValidationTruth
from rapidata.api_client.models.i_validation_truth_compare_truth import (
    IValidationTruthCompareTruth,
)
from rapidata.rapidata_client.datapoints._asset_upload_orchestrator import (
    extract_assets_from_datapoint,
)
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._datapoint import (
    Datapoint,
    coerce_media_context,
)
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.datapoints._truth_translator import (
    translate_compare_truth,
)
from rapidata.rapidata_client.datapoints.assets.uploaded_asset import UploadedAsset
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset

A = UploadedAsset("0b4a1f8e-a.png")
B = UploadedAsset("5c2d9e7f-b.png")


def _service() -> MagicMock:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    return openapi_service


def _names(asset_input: IAssetInput) -> list[str]:
    instance = asset_input.actual_instance
    if isinstance(instance, IAssetInputMultiAssetInput):
        return [_names(asset)[0] for asset in instance.assets]
    assert isinstance(instance, IAssetInputExistingAssetInput)
    return [instance.name]


def _assert_nothing_uploaded(openapi_service: MagicMock) -> None:
    asset_api = openapi_service.asset.asset_api
    asset_api.asset_file_post.assert_not_called()
    asset_api.asset_url_post.assert_not_called()
    openapi_service.asset.batch_upload_api.asset_batch_upload_post.assert_not_called()


def test_uploaded_asset_is_an_immutable_value() -> None:
    assert UploadedAsset("x.png") == UploadedAsset(name="x.png")
    assert len({UploadedAsset("x.png"), UploadedAsset("x.png")}) == 1
    assert repr(UploadedAsset("x.png")) == "UploadedAsset(name='x.png')"
    with pytest.raises(dataclasses.FrozenInstanceError):
        A.name = "other.png"  # type: ignore[misc]


@pytest.mark.parametrize("name", ["", "https://example.com/a.png"])
def test_uploaded_asset_rejects_names_that_are_not_references(name: str) -> None:
    with pytest.raises(ValueError):
        UploadedAsset(name)


def test_upload_asset_returns_the_name_without_calling_the_api() -> None:
    openapi_service = _service()

    assert AssetUploader(openapi_service).upload_asset(A) == A.name
    _assert_nothing_uploaded(openapi_service)


def test_upload_and_map_asset_bundles_references_without_uploading() -> None:
    openapi_service = _service()

    asset_input = AssetUploader(openapi_service).upload_and_map_asset([A, B])

    assert _names(asset_input) == [A.name, B.name]
    _assert_nothing_uploaded(openapi_service)


def test_mixed_list_uploads_only_the_string_entries() -> None:
    uploader = AssetUploader(_service())
    uploader._upload_url_asset = MagicMock(return_value="uploaded-b.png")  # type: ignore[method-assign]

    asset_input, asset_to_uploaded = uploader.build_asset_input_with_names(
        [A, "https://host/b.png"], "media"
    )

    uploader._upload_url_asset.assert_called_once_with("https://host/b.png")
    assert _names(asset_input) == [A.name, "uploaded-b.png"]
    assert asset_to_uploaded == {A.name: A.name, "https://host/b.png": "uploaded-b.png"}


def test_compare_truth_can_name_an_uploaded_asset_as_winner() -> None:
    _, asset_to_uploaded = AssetUploader(_service()).build_asset_input_with_names(
        [A, B], "media"
    )
    truth = IValidationTruth(
        actual_instance=IValidationTruthCompareTruth(_t="CompareTruth", winnerId=B.name)
    )

    translated = translate_compare_truth(truth, asset_to_uploaded)

    assert translated is not None
    assert isinstance(translated.actual_instance, IValidationTruthCompareTruth)
    assert translated.actual_instance.winner_id == B.name


def test_uploaded_asset_cannot_be_sent_as_text() -> None:
    with pytest.raises(TypeError):
        AssetUploader(_service()).build_asset_input([A, "some text"], "text")


@pytest.mark.parametrize(
    ("asset", "expected"),
    [
        (UploadedAsset("0b4a1f8e.webp"), AssetType.IMAGE),
        (UploadedAsset("0b4a1f8e.MP4"), AssetType.VIDEO),
        (UploadedAsset("0b4a1f8e.mp3"), AssetType.AUDIO),
        (UploadedAsset("0b4a1f8e"), AssetType.NONE),
        ([UploadedAsset("0b4a1f8e.mp4"), "https://host/b.png"], AssetType.VIDEO),
        (["https://host/b.png", UploadedAsset("0b4a1f8e.mp4")], AssetType.IMAGE),
    ],
)
def test_asset_type_comes_from_the_uploaded_name(
    asset: UploadedAsset | list[str | UploadedAsset], expected: AssetType
) -> None:
    assert Datapoint(asset=asset, data_type="media").get_asset_type() == expected


def test_datapoint_keeps_the_reference_object() -> None:
    datapoint = Datapoint(asset=[A, "b.png"], data_type="media", media_context=[B])

    assert isinstance(datapoint.asset, list)
    assert datapoint.asset[0] is A
    assert datapoint.media_context == [B]


def test_text_datapoint_rejects_an_uploaded_asset() -> None:
    with pytest.raises(ValueError, match="UploadedAsset is media"):
        Datapoint(asset=A, data_type="text")


def test_path_only_media_context_rejects_an_uploaded_asset() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        coerce_media_context([A])


def test_validator_accepts_references_in_flat_and_nested_datapoints() -> None:
    flat = DatapointsValidator.map_datapoints(datapoints=[A, "b.png"])
    nested = DatapointsValidator.map_datapoints(
        datapoints=[[A, B], ["a.png", B]],
        media_contexts=[[A], ["c.png"]],
        multi_asset=True,
    )

    assert [d.asset for d in flat] == [A, "b.png"]
    assert [d.asset for d in nested] == [[A, B], ["a.png", B]]
    assert [d.media_context for d in nested] == [[A], ["c.png"]]


def test_validator_rejects_a_flat_list_of_references_for_multi_asset() -> None:
    with pytest.raises(ValueError, match="list of lists"):
        DatapointsValidator.map_datapoints(datapoints=[A, B], multi_asset=True)


def test_extract_assets_skips_uploaded_assets() -> None:
    datapoint = Datapoint(
        asset=[A, "https://host/b.png"],
        data_type="media",
        media_context=[B, "ctx.png"],
    )

    assert extract_assets_from_datapoint(datapoint) == {"https://host/b.png", "ctx.png"}


def test_dataset_creates_datapoints_from_references_without_uploading() -> None:
    openapi_service = _service()
    dataset = RapidataDataset("ds-1", openapi_service)
    datapoints = [
        Datapoint(asset=[A, B], data_type="media", media_context=[A]),
        Datapoint(asset=[B, A], data_type="media"),
    ]

    successful, failed = dataset.add_datapoints(datapoints)

    assert (len(successful), failed) == (2, [])
    _assert_nothing_uploaded(openapi_service)
    post = openapi_service.dataset.datapoints_api.dataset_dataset_id_datapoint_post
    payloads = sorted(
        (c.kwargs["create_datapoint_endpoint_input"] for c in post.call_args_list),
        key=lambda payload: payload.sort_index,
    )
    assert [[_names(s.asset) for s in p.segments] for p in payloads] == [
        [[A.name, B.name], [A.name]],
        [[B.name, A.name]],
    ]
