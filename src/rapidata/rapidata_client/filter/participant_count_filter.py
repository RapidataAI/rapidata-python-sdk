from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.comparison_operator import ComparisonOperator
from pydantic import BaseModel, field_validator


class ParticipantCountFilter(RapidataFilter, BaseModel):
    """ParticipantCountFilter Class

    Can be used to limit a campaign by how many users have already started a session in it.
    Only supported on campaigns, not on audiences.

    Args:
        participant_count (int): The participant count to compare against. Must be greater than 0.
        operator (ComparisonOperator): How the campaign's current participant count is compared to `participant_count`.

    Raises:
        ValueError: If `participant_count` is not greater than 0.

    Example:
        ```python
        from rapidata.api_client.models.comparison_operator import ComparisonOperator
        from rapidata.types import ParticipantCountFilter

        filter = ParticipantCountFilter(participant_count=500, operator=ComparisonOperator.LESSTHAN)
        ```
        This stops the campaign from matching any user once 500 users have started a session in it.
    """

    participant_count: int
    operator: ComparisonOperator

    def __init__(self, participant_count: int, operator: ComparisonOperator):
        super().__init__(participant_count=participant_count, operator=operator)

    @field_validator("participant_count")
    @classmethod
    def validate_participant_count(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("participant_count must be greater than 0")
        return v

    def _to_model(self):
        raise NotImplementedError(
            "ParticipantCountFilter is only supported for campaigns"
        )

    def _to_campaign_model(self):
        from rapidata.api_client.models.i_campaign_filter import ICampaignFilter
        from rapidata.api_client.models.i_campaign_filter_campaign_participant_count_filter import (
            ICampaignFilterCampaignParticipantCountFilter,
        )

        return ICampaignFilter(
            actual_instance=ICampaignFilterCampaignParticipantCountFilter(
                _t="CampaignParticipantCountFilter",
                participantCount=self.participant_count,
                operator=self.operator,
            )
        )
