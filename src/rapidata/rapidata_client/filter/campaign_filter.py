from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.campaign_user_filter_model import (
    CampaignUserFilterModel,
)


class CampaignFilter(Filter):

    def __init__(self, campaign_ids: list[str]):
        self.campaign_ids = campaign_ids

    def to_model(self):
        return CampaignUserFilterModel(
            _t="CampaignFilter",
            campaignIds=self.campaign_ids,
        )
