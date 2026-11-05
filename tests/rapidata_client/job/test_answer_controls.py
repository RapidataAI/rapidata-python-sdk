from __future__ import annotations

import itertools
import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import Field, StrictBool

from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.lazy_model import LazyValidatedModel
from rapidata.api_client.models.create_job_definition_endpoint_input import (
    CreateJobDefinitionEndpointInput,
)
from rapidata.api_client.models.i_order_workflow_input import IOrderWorkflowInput
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_workflow_config import IWorkflowConfig
from rapidata import AdaptiveStopping
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager
from rapidata.rapidata_client.workflow import CompareWorkflow, ClassifyWorkflow
from rapidata.rapidata_client.workflow._answer_controls import adapt_answer_controls


@pytest.mark.parametrize(
    "good,bad,cs", list(itertools.product([False, True], repeat=3))
)
def test_compare_controls_survive_actual_request_serialization_and_redecode(
    good, bad, cs
):
    workflow = CompareWorkflow(
        "Which?",
        a_b_names=["Model雪", "a.b"],
        allow_both_good=good,
        allow_both_bad=bad,
        allow_cant_solve=cs,
    )
    expected = {"allowBothGood": good, "allowBothBad": bad, "allowCantSolve": cs}
    body = CreateJobDefinitionEndpointInput(
        definitionName="Job",
        datasetId="ds-1",
        workflow=workflow._to_model(),
        referee=AdaptiveStopping()._to_referee()._to_model(),
    )
    with ApiClient() as client:
        wire = client.sanitize_for_serialization(body)
    rapid = wire["workflow"]["rapid"]
    assert {key: rapid[key] for key in expected} == expected
    assert rapid["criteria"] == {"literal": "Which?"}
    assert rapid["indexIdentifiers"] == ["Model雪", "a.b"]
    decoded = IOrderWorkflowInput.from_dict(wire["workflow"]).to_dict()["rapid"]
    assert {key: decoded[key] for key in expected} == expected
    assert json.loads(body.to_json())["workflow"]["rapid"] == rapid
    payload = workflow._to_payload(Datapoint(asset=["a", "b"], data_type="text"))
    assert {key: payload.to_dict()[key] for key in expected} == expected
    assert IRapidPayload.from_json(payload.to_json()).to_dict() == payload.to_dict()


@pytest.mark.parametrize("enabled", [False, True])
def test_classify_controls_preserve_exact_option_values_across_spec_and_payload(
    enabled,
):
    workflow = ClassifyWorkflow("Which?", allow_cant_solve=enabled)
    wire = workflow._to_model().to_dict()
    assert wire["rapid"]["allowCantSolve"] is enabled
    assert (
        IOrderWorkflowInput.from_dict(wire).to_dict()["rapid"]["allowCantSolve"]
        is enabled
    )
    options = ["雪☃", "a.b", "bothBad", "arbitrary/value"]
    payload = workflow._to_payload(
        Datapoint(asset="text", data_type="text", answer_options=options)
    )
    decoded = IRapidPayload.from_json(payload.to_json()).to_dict()
    assert decoded["allowCantSolve"] is enabled
    assert decoded["categories"] == [{"label": v, "value": v} for v in options]


@pytest.mark.parametrize("kind", ["Compare", "Classify"])
def test_saved_workflow_blueprint_preserves_controls_and_referee_together(kind):
    blueprint = {"_t": f"{kind}Blueprint", "allowCantSolve": True}
    if kind == "Compare":
        blueprint.update(
            criteria="Which?",
            indexIdentifiers=["A", "B"],
            allowBothGood=True,
            allowBothBad=False,
        )
    else:
        blueprint.update(
            title="Which?",
            categories=[
                {"label": "Second", "value": "a.b"},
                {"label": "First", "value": "雪"},
            ],
        )
    config = AdaptiveStopping(unsolvable_threshold=0.7)._to_referee()._to_dict()
    wire = {
        "_t": "SimpleWorkflowConfig",
        "blueprint": blueprint,
        "referee": config,
        "featureFlags": [],
    }
    model = IWorkflowConfig.from_dict(wire)
    decoded = model.to_dict()
    assert {key: decoded["blueprint"][key] for key in blueprint} == blueprint
    assert decoded["referee"] == config
    assert {
        key: json.loads(model.to_json())["blueprint"][key] for key in blueprint
    } == blueprint


def test_creation_methods_forward_controls_to_workflows():
    manager = RapidataJobManager(MagicMock())
    with patch.object(manager, "_create_general_job_definition") as create:
        manager.create_compare_job_definition(
            "Job",
            "Which?",
            [["a", "b"]],
            data_type="text",
            allow_both_good=True,
            allow_cant_solve=True,
        )
        rapid = create.call_args.kwargs["workflow"]._to_model().to_dict()["rapid"]
        assert rapid["allowBothGood"] is True
        assert rapid["allowBothBad"] is False
        assert rapid["allowCantSolve"] is True
        manager.create_classification_job_definition(
            "Job",
            "Which?",
            ["a", "b"],
            ["text"],
            data_type="text",
            allow_cant_solve=True,
        )
        assert (
            create.call_args.kwargs["workflow"]
            ._to_model()
            .to_dict()["rapid"]["allowCantSolve"]
            is True
        )


def test_adapter_defers_to_native_controls_after_regeneration():
    class NativeSpec(LazyValidatedModel):
        allow_cant_solve: StrictBool = Field(False, alias="allowCantSolve")

    assert (
        adapt_answer_controls(NativeSpec, {"_t": "Classify", "allowCantSolve": True})
        is None
    )
