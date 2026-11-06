from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from rapidata import AdaptiveStopping
from rapidata.api_client.models.get_job_cost_estimate_endpoint_output import (
    GetJobCostEstimateEndpointOutput,
)
from rapidata.api_client.models.get_job_definition_cost_estimate_endpoint_output import (
    GetJobDefinitionCostEstimateEndpointOutput,
)
from rapidata.rapidata_client.job.rapidata_job import RapidataJob
from rapidata.rapidata_client.job.rapidata_job_definition import RapidataJobDefinition
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager


@pytest.mark.parametrize("kind", ["definition", "job"])
def test_cost_estimate_uses_endpoint_expected_responses_without_fixed_cap_arithmetic(
    kind,
):
    service = MagicMock()
    service.environment = "rapidata.ai"
    job_api = service.order.job_api
    if kind == "definition":
        target = RapidataJobDefinition("definition-1", "Job", service)
        endpoint = job_api.job_definition_definition_id_cost_estimate_get
        model = GetJobDefinitionCostEstimateEndpointOutput
        identifier = "definition-1"
    else:
        target = RapidataJob(
            "job-1", "Job", "global", MagicMock(), "definition-1", service
        )
        endpoint = job_api.job_job_id_cost_estimate_get
        model = GetJobCostEstimateEndpointOutput
        identifier = "job-1"
    endpoint.return_value = model(
        estimatedCost=12.34,
        costPerResponse=12.34 / 47,
        datapointCount=3,
        requiredResponses=47,
    )

    estimate = target.estimated_cost

    assert estimate.estimated_cost == 12.34
    assert estimate.datapoint_count == 3
    assert estimate.required_responses == 47
    assert not hasattr(estimate, "max_cost")
    assert target.estimated_cost is estimate
    endpoint.assert_called_once_with(identifier)


def test_compare_and_classification_keep_their_agreed_defaults():
    compare = inspect.signature(RapidataJobManager.create_compare_job_definition)
    classify = inspect.signature(
        RapidataJobManager.create_classification_job_definition
    )
    assert isinstance(
        compare.parameters["responses_per_datapoint"].default, AdaptiveStopping
    )
    assert classify.parameters["responses_per_datapoint"].default == 10
