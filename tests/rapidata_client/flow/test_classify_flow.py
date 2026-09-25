from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rapidata.api_client.models.flow_item_state import FlowItemState
from rapidata.rapidata_client.flow._flow_type import flow_type_from_api
from rapidata.rapidata_client.flow.classify_flow_item_result import (
    ClassifyDatapointResult,
    ClassifyFlowItemResult,
)
from rapidata import RapidataFlow, RapidataRankingFlow, RapidataClassifyFlow
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem
from rapidata.rapidata_client.flow.rapidata_flow_manager import RapidataFlowManager

FLOW_MODULE = "rapidata.rapidata_client.flow.rapidata_flow"
SIMPLE_FLOW_API = "rapidata.api_client.api.simple_flow_api"
SIMPLE_FLOW_RESULTS_MODEL = "rapidata.api_client.models.get_results_endpoint_output"
SIMPLE_FLOW_MODEL = "rapidata.api_client.models.i_flow_simple_flow"

# Recorded shape of GET /flow/simple/item/{flowItemId}/results.
CLASSIFY_RESULTS_RESPONSE = {
    "datapoints": [
        {
            "datapointId": "dp-1",
            "asset": {
                "_t": "FileAsset",
                "fileName": "a.jpg",
                "identifier": "asset-1",
                "metadata": {
                    "sourceUrl": {
                        "_t": "SourceUrlMetadataModel",
                        "url": "https://example.com/a.jpg",
                    }
                },
            },
            "majorityValue": "yes",
            "distribution": [{"value": "yes", "count": 4}, {"value": "no", "count": 1}],
            "responseCount": 5,
        },
        {
            "datapointId": "dp-2",
            "asset": {
                "_t": "FileAsset",
                "fileName": "b.jpg",
                "identifier": "asset-2",
                "metadata": {
                    "originalFilename": {
                        "_t": "OriginalFilenameMetadata",
                        "originalFilename": "b.jpg",
                    }
                },
            },
            "majorityValue": None,
            "distribution": [{"value": "yes", "count": 2}, {"value": "no", "count": 2}],
            "responseCount": 4,
        },
    ],
    "totalResponses": 9,
}

EXPECTED_CLASSIFY_RESULT = ClassifyFlowItemResult(
    datapoints={
        "https://example.com/a.jpg": ClassifyDatapointResult(
            majority_value="yes", distribution={"yes": 4, "no": 1}, response_count=5
        ),
        "b.jpg": ClassifyDatapointResult(
            majority_value=None, distribution={"yes": 2, "no": 2}, response_count=4
        ),
    },
    total_responses=9,
)


def _openapi_service() -> MagicMock:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    svc.dataset.dataset_api.dataset_post.return_value = MagicMock(dataset_id="ds-1")
    svc.flow.ranking_flow_item_api.flow_ranking_flow_id_item_post.return_value = (
        MagicMock(flow_item_id="fli-ranking")
    )
    svc.flow.simple_flow_item_api.flow_simple_flow_id_item_post.return_value = (
        MagicMock(flow_item_id="fli-simple")
    )
    svc.flow.ranking_flow_item_api.flow_ranking_item_flow_item_id_get.return_value.state = (
        FlowItemState.COMPLETED
    )
    return svc


def _without_none(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


def _create_batch(
    flow: RapidataRankingFlow | RapidataClassifyFlow, **kwargs
) -> tuple[RapidataFlowItem, MagicMock]:
    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = lambda datapoints: (datapoints, [])
    with patch(f"{FLOW_MODULE}.RapidataDataset", return_value=dataset):
        return flow.create_new_flow_batch(**kwargs), dataset


class TestFlowType:
    @pytest.mark.parametrize(
        ("api_value", "expected"),
        [
            ("Ranking", "ranking"),
            ("RankingFlow", "ranking"),
            ("Simple", "simple"),
            ("SimpleFlow", "simple"),
        ],
    )
    def test_maps_enum_values_and_discriminators(self, api_value, expected):
        assert flow_type_from_api(api_value) == expected

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError, match="Unknown flow type 'Compare'"):
            flow_type_from_api("Compare")

    @pytest.mark.parametrize(
        ("discriminator", "expected"),
        [("RankingFlow", "ranking"), ("SimpleFlow", "simple")],
    )
    def test_get_flow_by_id_carries_type_from_discriminator(
        self, discriminator, expected
    ):
        svc = _openapi_service()
        svc.flow.flow_api.flow_flow_id_get.return_value.to_dict.return_value = {
            "_t": discriminator,
            "id": "flw-1",
            "name": "My Flow",
        }

        flow = RapidataFlowManager(svc).get_flow_by_id("flw-1")

        expected_class = (
            RapidataRankingFlow if expected == "ranking" else RapidataClassifyFlow
        )
        assert isinstance(flow, expected_class)
        assert isinstance(flow, RapidataFlow)
        assert (flow.id, flow.name, flow._flow_type) == ("flw-1", "My Flow", expected)

    def test_find_flows_carries_type_from_enum(self):
        svc = _openapi_service()
        ranking = MagicMock(id="flw-r")
        ranking.name = "Ranking"
        ranking.type.value = "Ranking"
        simple = MagicMock(id="flw-s")
        simple.name = "Simple"
        simple.type.value = "Simple"
        svc.flow.flow_api.flow_get.return_value.items = [ranking, simple]

        flows = RapidataFlowManager(svc).find_flows()

        assert isinstance(flows[0], RapidataRankingFlow)
        assert isinstance(flows[1], RapidataClassifyFlow)
        assert [(flow.id, flow._flow_type) for flow in flows] == [
            ("flw-r", "ranking"),
            ("flw-s", "simple"),
        ]


class TestCreateClassifyFlow:
    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"categories": ["only"]}, "between 2 and 8"),
            ({"categories": [str(i) for i in range(9)]}, "between 2 and 8"),
            ({"categories": [("A", "x"), ("B", "x")]}, "unique"),
            (
                {"categories": ["a", "b"], "min_responses_per_datapoint": 0},
                "at least 1",
            ),
            (
                {
                    "categories": ["a", "b"],
                    "max_responses_per_datapoint": 2,
                    "min_responses_per_datapoint": 3,
                },
                "at least min",
            ),
        ],
    )
    def test_rejects_invalid_input_before_calling_the_api(self, kwargs, message):
        svc = _openapi_service()

        with pytest.raises(ValueError, match=message):
            RapidataFlowManager(svc).create_classify_flow(
                name="Text Detection",
                instruction="Does this image contain text?",
                **kwargs,
            )

        svc.flow.simple_flow_api.flow_simple_post.assert_not_called()

    def test_payload_matches_generated_model(self):
        pytest.importorskip(SIMPLE_FLOW_API)
        svc = _openapi_service()
        svc.flow.simple_flow_api.flow_simple_post.return_value = MagicMock(
            flow_id="flw-1"
        )

        flow = RapidataFlowManager(svc).create_classify_flow(
            name="Text Detection",
            instruction="Does this image contain text?",
            categories=[("Yes, clearly readable", "yes"), ("No", "no")],
        )

        svc.flow.simple_flow_api.flow_simple_post.assert_called_once()
        payload = svc.flow.simple_flow_api.flow_simple_post.call_args.kwargs[
            "create_simple_flow_endpoint_input"
        ].to_dict()
        assert _without_none(payload) == {
            "name": "Text Detection",
            "blueprint": {
                "_t": "ClassifyBlueprint",
                "title": "Does this image contain text?",
                "categories": [
                    {"label": "Yes, clearly readable", "value": "yes"},
                    {"label": "No", "value": "no"},
                ],
            },
            "maxResponses": 15,
            "minResponses": 10,
        }
        assert isinstance(flow, RapidataClassifyFlow)
        assert (flow.id, flow._flow_type) == ("flw-1", "simple")

    def test_max_and_min_responses_per_datapoint_are_sent(self):
        pytest.importorskip(SIMPLE_FLOW_API)
        svc = _openapi_service()
        svc.flow.simple_flow_api.flow_simple_post.return_value = MagicMock(
            flow_id="flw-1"
        )

        RapidataFlowManager(svc).create_classify_flow(
            name="Text Detection",
            instruction="Does this image contain text?",
            categories=["Yes", "No"],
            max_responses_per_datapoint=8,
            min_responses_per_datapoint=4,
        )

        payload = svc.flow.simple_flow_api.flow_simple_post.call_args.kwargs[
            "create_simple_flow_endpoint_input"
        ].to_dict()
        assert payload["maxResponses"] == 8
        assert payload["minResponses"] == 4

    def test_string_categories_use_the_label_as_value(self):
        pytest.importorskip(SIMPLE_FLOW_API)
        svc = _openapi_service()
        svc.flow.simple_flow_api.flow_simple_post.return_value = MagicMock(
            flow_id="flw-1"
        )

        RapidataFlowManager(svc).create_classify_flow(
            name="Text Detection",
            instruction="Does this image contain text?",
            categories=["Yes", "No"],
        )

        payload = svc.flow.simple_flow_api.flow_simple_post.call_args.kwargs[
            "create_simple_flow_endpoint_input"
        ].to_dict()
        assert payload["blueprint"]["categories"] == [
            {"label": "Yes", "value": "Yes"},
            {"label": "No", "value": "No"},
        ]
        assert "defaultTimeToLiveSeconds" not in _without_none(payload)


class TestCreateNewFlowBatch:
    def test_ranking_flow_still_posts_to_the_ranking_item_route(self):
        svc = _openapi_service()
        flow = RapidataRankingFlow("flw-1", "Ranking", svc)

        item, _ = _create_batch(
            flow,
            datapoints=["https://example.com/a.jpg"],
            context="Model X",
            time_to_live=60,
        )

        call = svc.flow.ranking_flow_item_api.flow_ranking_flow_id_item_post.call_args
        assert call.kwargs["flow_id"] == "flw-1"
        payload = call.kwargs["create_flow_item_endpoint_input"].to_dict()
        assert _without_none(payload) == {
            "datasetId": "ds-1",
            "context": "Model X",
            "timeToLiveInSeconds": 60,
        }
        svc.flow.simple_flow_item_api.flow_simple_flow_id_item_post.assert_not_called()
        assert (item.id, item._flow_type) == ("fli-ranking", "ranking")

    def test_classify_flow_posts_only_the_dataset_to_the_simple_item_route(self):
        pytest.importorskip(SIMPLE_FLOW_API)
        svc = _openapi_service()
        flow = RapidataClassifyFlow("flw-1", "Classify", svc)

        item, dataset = _create_batch(
            flow,
            datapoints=["https://example.com/a.jpg", "https://example.com/b.jpg"],
            contexts=["first", "second"],
            context_assets=[
                ["https://example.com/ctx.jpg", "https://example.com/extra.jpg"],
                ["https://example.com/ctx2.jpg"],
            ],
        )

        call = svc.flow.simple_flow_item_api.flow_simple_flow_id_item_post.call_args
        assert call.kwargs["flow_id"] == "flw-1"
        payload = call.kwargs["create_simple_flow_item_endpoint_input"].to_dict()
        assert _without_none(payload) == {"datasetId": "ds-1"}
        svc.flow.ranking_flow_item_api.flow_ranking_flow_id_item_post.assert_not_called()

        uploaded = dataset.add_datapoints.call_args.args[0]
        assert [dp.context for dp in uploaded] == ["first", "second"]
        assert [dp.media_context for dp in uploaded] == [
            ["https://example.com/ctx.jpg", "https://example.com/extra.jpg"],
            ["https://example.com/ctx2.jpg"],
        ]
        assert (item.id, item.flow_id, item._flow_type) == (
            "fli-simple",
            "flw-1",
            "simple",
        )

    @pytest.mark.parametrize("flow_type", ["ranking", "simple"])
    @pytest.mark.parametrize("time_to_live", [19, 3601])
    def test_rejects_time_to_live_outside_bounds_before_uploading(
        self, flow_type, time_to_live
    ):
        svc = _openapi_service()
        flow_class = (
            RapidataRankingFlow if flow_type == "ranking" else RapidataClassifyFlow
        )
        flow = flow_class("flw-1", "Flow", svc)

        with pytest.raises(ValueError, match="between 20 seconds and 1 hour"):
            flow.create_new_flow_batch(
                datapoints=["https://example.com/a.jpg"], time_to_live=time_to_live
            )

        svc.dataset.dataset_api.dataset_post.assert_not_called()

    def test_classify_flow_rejects_batch_level_context(self):
        svc = _openapi_service()
        flow = RapidataClassifyFlow("flw-1", "Classify", svc)

        with pytest.raises(ValueError, match="Contexts must be a list of strings"):
            flow.create_new_flow_batch(
                datapoints=["https://example.com/a.jpg"], contexts="x"
            )

        svc.dataset.dataset_api.dataset_post.assert_not_called()

    def test_flow_items_inherit_the_flow_type(self):
        svc = _openapi_service()
        svc.flow.ranking_flow_item_api.flow_ranking_flow_id_item_get.return_value.items = [
            MagicMock(id="fli-1")
        ]
        flow = RapidataClassifyFlow("flw-1", "Classify", svc)

        items = flow.get_flow_items()

        assert [(item.id, item._flow_type) for item in items] == [("fli-1", "simple")]

    def test_update_config_sends_only_the_drain_duration(self):
        svc = _openapi_service()
        flow = RapidataClassifyFlow("flw-1", "Classify", svc)

        flow.update_config(drain_duration=20)

        call = svc.flow.simple_flow_api.flow_simple_flow_id_patch.call_args
        assert call.kwargs["flow_id"] == "flw-1"
        assert call.kwargs["update_simple_flow_config_endpoint_input"].to_dict() == {
            "drainDurationSeconds": 20
        }
        assert not hasattr(RapidataFlow, "update_config")
        assert not hasattr(RapidataFlow, "create_new_flow_batch")
        svc.flow.ranking_flow_api.flow_ranking_flow_id_patch.assert_not_called()

    def test_update_config_without_a_drain_leaves_it_unchanged(self):
        svc = _openapi_service()
        flow = RapidataRankingFlow("flw-1", "Ranking", svc)

        flow.update_config(instruction="Which is better?")

        call = svc.flow.ranking_flow_api.flow_ranking_flow_id_patch.call_args
        assert "drainDurationSeconds" not in call.kwargs[
            "update_config_endpoint_input"
        ].to_dict()


class TestClassifyResults:
    def _results_stub(self) -> MagicMock:
        results = MagicMock()
        results.datapoints = [
            MagicMock(**{"to_dict.return_value": datapoint})
            for datapoint in CLASSIFY_RESULTS_RESPONSE["datapoints"]
        ]
        results.total_responses = CLASSIFY_RESULTS_RESPONSE["totalResponses"]
        return results

    def test_distribution_includes_every_blueprint_category(self):
        model_module = pytest.importorskip(SIMPLE_FLOW_MODEL)
        svc = _openapi_service()
        flow_response = model_module.IFlowSimpleFlow.model_construct(
            blueprint=MagicMock(
                categories=[
                    MagicMock(value="yes"),
                    MagicMock(value="no"),
                    MagicMock(value="maybe"),
                ]
            )
        )
        svc.flow.flow_api.flow_flow_id_get.return_value = flow_response
        results = MagicMock()
        results.datapoints = [
            MagicMock(
                **{
                    "to_dict.return_value": {
                        "datapointId": "dp-1",
                        "asset": {"identifier": "asset-1", "metadata": {}},
                        "majorityValue": "yes",
                        "distribution": [
                            {"value": "yes", "count": 5},
                            {"value": "unexpected", "count": 2},
                        ],
                        "responseCount": 7,
                    }
                }
            )
        ]
        results.total_responses = 7
        svc.flow.simple_flow_item_api.flow_simple_item_flow_item_id_results_get.return_value = (
            results
        )
        item = RapidataFlowItem("fli-1", "flw-1", svc, flow_type="simple")

        result = item.get_results()

        assert result.datapoints["asset-1"].distribution == {  # type: ignore[union-attr]
            "yes": 5,
            "no": 0,
            "maybe": 0,
            "unexpected": 2,
        }
        svc.flow.flow_api.flow_flow_id_get.assert_called_once_with(flow_id="flw-1")

    def test_get_results_returns_classify_result_for_classify_items(self):
        svc = _openapi_service()
        svc.flow.simple_flow_item_api.flow_simple_item_flow_item_id_results_get.return_value = (
            self._results_stub()
        )
        item = RapidataFlowItem("fli-1", "flw-1", svc, flow_type="simple")

        assert item.get_results() == EXPECTED_CLASSIFY_RESULT
        svc.flow.simple_flow_item_api.flow_simple_item_flow_item_id_results_get.assert_called_once_with(
            flow_item_id="fli-1"
        )
        svc.flow.ranking_flow_item_api.flow_ranking_item_flow_item_id_results_get.assert_not_called()

    def test_recorded_response_parses_through_the_generated_model(self):
        model_module = pytest.importorskip(SIMPLE_FLOW_RESULTS_MODEL)
        output = model_module.GetResultsEndpointOutput.from_dict(
            CLASSIFY_RESULTS_RESPONSE
        )
        svc = _openapi_service()
        svc.flow.simple_flow_item_api.flow_simple_item_flow_item_id_results_get.return_value = (
            output
        )
        item = RapidataFlowItem("fli-1", "flw-1", svc, flow_type="simple")

        assert item.get_results() == EXPECTED_CLASSIFY_RESULT

    def test_response_count_comes_from_the_results(self):
        svc = _openapi_service()
        svc.flow.simple_flow_item_api.flow_simple_item_flow_item_id_results_get.return_value = (
            self._results_stub()
        )
        item = RapidataFlowItem("fli-1", "flw-1", svc, flow_type="simple")

        assert item.get_response_count() == 9
        svc.flow.ranking_flow_item_api.flow_ranking_item_flow_item_id_vote_matrix_get.assert_not_called()

    def test_win_loss_matrix_is_ranking_only(self):
        item = RapidataFlowItem(
            "fli-1", "flw-1", _openapi_service(), flow_type="simple"
        )

        with pytest.raises(ValueError, match="only available for ranking flow items"):
            item.get_win_loss_matrix()

    def test_ranking_items_keep_returning_elo_results(self):
        svc = _openapi_service()
        ranking_results = MagicMock(total_votes=12)
        ranking_results.datapoints = [
            MagicMock(
                **{
                    "to_dict.return_value": {
                        "id": "dp-1",
                        "asset": {"identifier": "asset-1", "metadata": {}},
                        "elo": 1234,
                    }
                }
            )
        ]
        svc.flow.ranking_flow_item_api.flow_ranking_item_flow_item_id_results_get.return_value = (
            ranking_results
        )
        item = RapidataFlowItem("fli-1", "flw-1", svc)

        result = item.get_results()

        assert (result.datapoints, result.total_votes) == ({"asset-1": 1234}, 12)  # type: ignore[union-attr]
        svc.flow.simple_flow_item_api.flow_simple_item_flow_item_id_results_get.assert_not_called()


class TestSeparatedFlows:
    def test_create_ranking_flow_returns_ranking_class(self):
        svc = _openapi_service()
        svc.flow.ranking_flow_api.flow_ranking_post.return_value.flow_id = "flw-r"
        flow = RapidataFlowManager(svc).create_ranking_flow("Ranking", "Choose one")
        assert isinstance(flow, RapidataRankingFlow)
        assert isinstance(flow, RapidataFlow)
        flow.update_config(instruction="Choose the best", min_responses=5)
        request = svc.flow.ranking_flow_api.flow_ranking_flow_id_patch.call_args.kwargs
        assert request["flow_id"] == "flw-r"
        assert _without_none(request["update_config_endpoint_input"].to_dict()) == {
            "criteria": "Choose the best",
            "minResponses": 5,
        }

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({"contexts": []}, "Number of contexts"),
            ({"contexts": ["one", "two"]}, "Number of contexts"),
            ({"contexts": [1]}, "list of strings"),
            ({"context_assets": ["https://example.com/a.jpg"]}, "list of lists"),
            ({"context_assets": [[1]]}, "list of lists"),
            ({"context_assets": "x"}, "list of lists"),
            ({"context_assets": []}, "Number of context assets"),
            ({"context_assets": [["a"], ["b"]]}, "Number of context assets"),
        ],
    )
    def test_classify_rejects_invalid_context_before_upload(self, kwargs, message):
        svc = _openapi_service()
        flow = RapidataClassifyFlow("flw-c", "Classify", svc)
        with pytest.raises(ValueError, match=message):
            flow.create_new_flow_batch(datapoints=["hello"], data_type="text", **kwargs)
        svc.dataset.dataset_api.dataset_post.assert_not_called()
        svc.flow.simple_flow_item_api.flow_simple_flow_id_item_post.assert_not_called()

    @pytest.mark.parametrize("flow_class", [RapidataRankingFlow, RapidataClassifyFlow])
    @pytest.mark.parametrize("accept_failed_uploads", [False, True])
    def test_failed_uploads_require_opt_in(self, flow_class, accept_failed_uploads):
        svc = _openapi_service()
        flow = flow_class("flw-1", "Flow", svc)
        dataset = MagicMock(id="ds-1")
        dataset.add_datapoints.return_value = ([], [MagicMock()])
        with patch(f"{FLOW_MODULE}.RapidataDataset", return_value=dataset):
            if accept_failed_uploads:
                item = flow.create_new_flow_batch(
                    ["hello"],
                    data_type="text",
                    accept_failed_uploads=True,
                    time_to_live=45,
                )
                assert item.flow_id == flow.id
            else:
                with pytest.raises(FailedUploadException):
                    flow.create_new_flow_batch(["hello"], data_type="text")
                svc.flow.simple_flow_item_api.flow_simple_flow_id_item_post.assert_not_called()
                svc.flow.ranking_flow_item_api.flow_ranking_flow_id_item_post.assert_not_called()

    def test_ranking_context_assets_are_uploaded_once_for_the_batch(self):
        svc = _openapi_service()
        flow = RapidataRankingFlow("flw-r", "Ranking", svc)
        module = "rapidata.rapidata_client.flow.rapidata_ranking_flow"
        with patch(f"{module}.AssetUploader") as uploader:
            uploader.return_value.upload_and_map_asset.return_value = None
            _, dataset = _create_batch(
                flow,
                datapoints=["hello", "world"],
                data_type="text",
                context="shared",
                context_assets=["a.jpg", "b.jpg"],
                private_metadata=[{"id": "a"}, {"id": "b"}],
            )
        uploader.return_value.upload_and_map_asset.assert_called_once_with(
            ["a.jpg", "b.jpg"]
        )
        uploaded = dataset.add_datapoints.call_args.args[0]
        assert [dp.context for dp in uploaded] == [None, None]
        assert [dp.private_metadata for dp in uploaded] == [{"id": "a"}, {"id": "b"}]

    @pytest.mark.parametrize("flow_class", [RapidataRankingFlow, RapidataClassifyFlow])
    def test_delete_uses_shared_route(self, flow_class):
        svc = _openapi_service()
        flow_class("flw-1", "Flow", svc).delete()
        svc.flow.flow_api.flow_flow_id_delete.assert_called_once_with(flow_id="flw-1")


@pytest.mark.parametrize(
    "flow_class, kwargs",
    [
        (RapidataRankingFlow, {"contexts": ["per item"]}),
        (RapidataRankingFlow, {"media_contexts": [["reference.jpg"]]}),
        (RapidataClassifyFlow, {"context": "shared"}),
    ],
)
def test_batch_rejects_context_arguments_for_other_flow_types(flow_class, kwargs):
    svc = _openapi_service()
    flow = flow_class("flw-1", "Flow", svc)
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        flow.create_new_flow_batch(["hello"], data_type="text", **kwargs)
    svc.dataset.dataset_api.dataset_post.assert_not_called()
