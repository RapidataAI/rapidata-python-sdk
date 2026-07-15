from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter


class NewUserFilter(RapidataFilter):
    """NewUserFilter Class

    Can be used to filter new users.
    """

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter import IUserFilter
        from rapidata.api_client.models.i_user_filter_new_user_filter import (
            IUserFilterNewUserFilter,
        )

        return IUserFilter(actual_instance=IUserFilterNewUserFilter(_t="NewUserFilter"))

    def _to_audience_model(self):
        raise NotImplementedError("NewUserFilter is not supported for audiences")
