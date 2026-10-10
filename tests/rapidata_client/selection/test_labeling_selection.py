from __future__ import annotations

import pytest

from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.rapidata_client.selection.rapidata_retrieval_modes import (
    RapidataRetrievalMode,
)


@pytest.mark.parametrize(
    "mode", [RapidataRetrievalMode.Shuffled, RapidataRetrievalMode.Sequential]
)
def test_advance_on_view_is_sent(mode: RapidataRetrievalMode) -> None:
    model = LabelingSelection(amount=3, retrieval_mode=mode, advance_on_view=True)

    assert model._to_model().to_dict()["advanceOnView"] is True


def test_advance_on_view_defaults_to_false() -> None:
    model = LabelingSelection(amount=3)

    assert model._to_model().to_dict()["advanceOnView"] is False


def test_advance_on_view_rejects_random() -> None:
    with pytest.raises(ValueError, match="Shuffled"):
        LabelingSelection(
            amount=3,
            retrieval_mode=RapidataRetrievalMode.Random,
            advance_on_view=True,
        )
