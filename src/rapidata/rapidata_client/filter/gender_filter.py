from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.gender_user_filter_model import GenderUserFilterModel
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
        return GenderUserFilterModel(
            _t="GenderFilter",
            genders=[gender._to_backend_model() for gender in self.genders],
        )
