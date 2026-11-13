"""RapidataJobDefinition._has_text_assets: local for a dataset it uploaded, one read otherwise."""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.rapidata_client.job.rapidata_job_definition import (
    RapidataJobDefinition,
)


def _definition(
    dataset_id: str = "ds-remote",
) -> tuple[RapidataJobDefinition, MagicMock]:
    service = MagicMock()
    service.environment = "rapidata.ai"
    service.order.job_api.job_definition_definition_id_revision_revision_number_get.return_value = MagicMock(
        dataset_id=dataset_id, revision_number=3
    )
    return (
        RapidataJobDefinition(
            id="jdf-1", name="Job", openapi_service=service, revision=3
        ),
        service,
    )


def _datapoint_with(text: bool) -> MagicMock:
    from rapidata.api_client.models.i_asset import IAsset
    from rapidata.api_client.models.i_asset_text_asset import IAssetTextAsset

    asset = (
        IAsset(
            actual_instance=IAssetTextAsset(
                _t="TextAsset", text="hi", metadata={}, identifier="hi"
            )
        )
        if text
        else None
    )
    return MagicMock(items=[MagicMock(segments=[MagicMock(asset=asset)])])


def test_loaded_definition_reads_one_datapoint_once():
    definition, service = _definition()
    get = service.dataset.datapoints_api.dataset_dataset_id_datapoints_get
    get.return_value = _datapoint_with(text=True)

    assert definition._has_text_assets()
    assert definition._has_text_assets()

    get.assert_called_once_with(dataset_id="ds-remote", page=1, page_size=1)


def test_local_knowledge_only_applies_to_its_dataset():
    definition, service = _definition()
    get = service.dataset.datapoints_api.dataset_dataset_id_datapoints_get
    get.return_value = _datapoint_with(text=False)
    definition._text_assets = ("ds-other", True)

    assert not definition._has_text_assets()
    get.assert_called_once()


def test_local_knowledge_skips_the_request():
    definition, service = _definition()
    definition._text_assets = ("ds-remote", True)

    assert definition._has_text_assets()
    service.dataset.datapoints_api.dataset_dataset_id_datapoints_get.assert_not_called()


def test_set_datapoints_records_text_for_the_new_dataset(monkeypatch):
    definition, service = _definition()
    service.dataset.dataset_api.dataset_post.return_value = MagicMock(
        dataset_id="ds-new"
    )
    dataset = MagicMock(id="ds-new")
    dataset.add_datapoints.return_value = ([], [])
    monkeypatch.setattr(
        "rapidata.rapidata_client.dataset._rapidata_dataset.RapidataDataset",
        MagicMock(return_value=dataset),
    )
    monkeypatch.setattr(
        "rapidata.rapidata_client.job._revision_body._required_segments",
        MagicMock(return_value=set()),
    )

    definition.set_datapoints(["first text", "second text"], data_type="text")

    assert definition._has_text_assets()
    service.dataset.datapoints_api.dataset_dataset_id_datapoints_get.assert_not_called()
