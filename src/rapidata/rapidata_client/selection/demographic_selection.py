from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.api_client.models.demographic_selection import DemographicSelection as DemographicSelectionModel


class DemographicSelection(RapidataSelection):
    """Demographic selection class.
    
    This is used to ask demographic questions in an order.    

    The keys will select the rapids based on the confidence we already saved for each user.

    If the confidence is high, the users will be selected to solve the rapids with lower probability.

    Args:
        keys (list[str]): List of keys for the demographic rapids to be shown. As an example: "age"
        max_rapids (int): The maximum number of rapids to run.\n
            Allows to provide more keys, in case some of the earlier ones are not selected because of high confidence."""

    def __init__(self, keys: list[str], max_rapids: int):
        self.keys = keys
        self.max_rapids = max_rapids

    def _to_model(self):
        return DemographicSelectionModel(_t="DemographicSelection", keys=self.keys, maxRapids=self.max_rapids)
