from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.campaign_user_filter_model import (
    CampaignUserFilterModel,
)
from pydantic import BaseModel


class CampaignFilter(RapidataFilter, BaseModel):
    """CampaignFilter Class

    Can be used to filter who to target based on campaign IDs.

    This filter can only be used when directly in contact with Rapidata.

    Args:
        campaign_ids (list[str]): List of campaign IDs to filter by.
    """

    campaign_ids: list[str]

    def __init__(self, campaign_ids: list[str]):
        super().__init__(campaign_ids=campaign_ids)

    def _to_model(self):
        return CampaignUserFilterModel(
            _t="CampaignFilter",
            campaignIds=self.campaign_ids,
        )
