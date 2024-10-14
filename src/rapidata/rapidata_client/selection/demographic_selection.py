from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.api_client.models.demographic_selection import DemographicSelection as DemographicSelectionModel


class DemographicSelection(Selection):
    """Demographic selection class."""

    def __init__(self, keys: list[str]):
        self.keys = keys

    def to_model(self):
        return DemographicSelectionModel(_t="DemographicSelection", keys=self.keys)
