from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.new_user_filter_model import NewUserFilterModel

class NewUserFilter(RapidataFilter):
    """NewUserFilter Class
    
    Can be used to filter new users.
    """

    def _to_model(self):
        return NewUserFilterModel(
            _t="NewUserFilter"
        )
