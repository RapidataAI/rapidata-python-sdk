from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.rapidata_client.filter.models.gender import Gender
from pydantic import BaseModel, ConfigDict


class GenderFilter(RapidataFilter, BaseModel):
    """GenderFilter Class

    Can be used to filter who to target based on their gender.


    Args:
        genders (list[Gender]): List of genders to filter by."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    genders: list[Gender]

    def __init__(self, genders: list[Gender]):
        super().__init__(genders=genders)

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_gender_user_filter_model import (
            IUserFilterModelGenderUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelGenderUserFilterModel(
                _t="GenderFilter",
                genders=[gender._to_backend_model() for gender in self.genders],
            )
        )

    def _to_audience_model(self):
        raise NotImplementedError("GenderFilter is not supported for audiences")
