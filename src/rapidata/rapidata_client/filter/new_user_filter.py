from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter


class NewUserFilter(RapidataFilter):
    """NewUserFilter Class

    Can be used to filter new users.
    """

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_new_user_filter_model import (
            IUserFilterModelNewUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelNewUserFilterModel(_t="NewUserFilter")
        )

    def _to_campaign_model(self):
        from rapidata.api_client.models.i_campaign_filter import ICampaignFilter
        from rapidata.api_client.models.i_campaign_filter_new_user_filter import (
            ICampaignFilterNewUserFilter,
        )

        return ICampaignFilter(
            actual_instance=ICampaignFilterNewUserFilter(_t="NewUserFilter")
        )
