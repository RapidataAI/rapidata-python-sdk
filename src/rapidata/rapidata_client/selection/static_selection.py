from rapidata.rapidata_client.selection._base_selection import RapidataSelection


class StaticSelection(RapidataSelection):
    """StaticSelection Class

    Given a list of RapidIds, theses specific rapids will be shown in order for every session.

    Args:
        rapid_ids (list[str]): List of rapid ids to show.
    """

    def __init__(self, rapid_ids: list[str]):
        self.rapid_ids = rapid_ids

    def _to_model(self):
        from rapidata.api_client.models.i_selection import ISelection
        from rapidata.api_client.models.i_selection_static_selection import (
            ISelectionStaticSelection,
        )

        return ISelection(
            actual_instance=ISelectionStaticSelection(
                _t="StaticSelection",
                rapidIds=self.rapid_ids,
            )
        )

    def __str__(self) -> str:
        return f"StaticSelection(rapid_ids={self.rapid_ids})"

    def __repr__(self) -> str:
        return self.__str__()
