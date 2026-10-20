from __future__ import annotations

import json

import pytest

from rapidata.api_client.models.comparison_operator import ComparisonOperator
from rapidata.api_client.models.i_campaign_filter import ICampaignFilter
from rapidata.api_client.models.i_campaign_filter_campaign_participant_count_filter import (
    ICampaignFilterCampaignParticipantCountFilter,
)
from rapidata.rapidata_client.filter import ParticipantCountFilter


def test_serializes_to_campaign_filter() -> None:
    model = ParticipantCountFilter(500, ComparisonOperator.LESSTHAN)

    assert json.loads(model._to_campaign_model().to_json()) == {
        "_t": "CampaignParticipantCountFilter",
        "participantCount": 500,
        "operator": "LessThan",
    }


def test_campaign_model_round_trips() -> None:
    model = ParticipantCountFilter(10, ComparisonOperator.GREATERTHANOREQUAL)

    parsed = ICampaignFilter.from_json(model._to_campaign_model().to_json())

    assert isinstance(
        parsed.actual_instance, ICampaignFilterCampaignParticipantCountFilter
    )
    assert parsed.actual_instance.participant_count == 10
    assert parsed.actual_instance.operator == ComparisonOperator.GREATERTHANOREQUAL


@pytest.mark.parametrize("count", [0, -1])
def test_rejects_non_positive_count(count: int) -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        ParticipantCountFilter(count, ComparisonOperator.LESSTHAN)


def test_is_not_supported_on_audiences() -> None:
    model = ParticipantCountFilter(500, ComparisonOperator.LESSTHAN)

    with pytest.raises(NotImplementedError):
        model._to_audience_model()
