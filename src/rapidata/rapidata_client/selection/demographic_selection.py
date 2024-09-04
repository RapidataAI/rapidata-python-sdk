

from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.api_client.models.demographic_selection import DemographicSelection as DemographicSelectionModel


class DemographicSelection(Selection):
    """Demographic selection class."""

    def __init__(self, rapid_id: str):
        self.rapid_id = rapid_id

    def to_model(self):
        return DemographicSelectionModel(_t="DemographicSelection", rapidId=self.rapid_id)