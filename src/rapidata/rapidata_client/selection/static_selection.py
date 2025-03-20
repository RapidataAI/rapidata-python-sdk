
from rapidata.api_client.models.ab_test_selection_a_inner import AbTestSelectionAInner
from rapidata.api_client.models.static_selection import StaticSelection as StaticSelectionModel
from rapidata.rapidata_client.selection._base_selection import RapidataSelection

class StaticSelection(RapidataSelection):
    """StaticSelection Class

    Given a list of RapidIds, will statically show these rapids.
    
    Args:
        selections (list[str]): List of rapid ids to show.
    """

    def __init__(self, rapid_ids: list[str]):
        self.rapid_ids = rapid_ids

    def _to_model(self) -> StaticSelectionModel:
        return StaticSelectionModel(
            _t="StaticSelection",
            rapidIds=self.rapid_ids
        )
    