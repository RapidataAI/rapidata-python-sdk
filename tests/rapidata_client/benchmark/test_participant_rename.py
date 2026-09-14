from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.api_client.api.participant_api import ParticipantApi
from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)


def test_rename_patches_only_name() -> None:
    service = MagicMock()
    service.leaderboard.participant_api = MagicMock(spec=ParticipantApi)
    participant = BenchmarkParticipant(
        name="original",
        id="participant-1",
        openapi_service=service,
        benchmark_id="benchmark-1",
        price=0.04,
        price_unit="image",
    )

    participant.rename("renamed")

    update = service.leaderboard.participant_api.participant_participant_id_patch
    update.assert_called_once()
    assert update.call_args.kwargs["participant_id"] == "participant-1"
    payload = update.call_args.kwargs["update_participant_endpoint_input"]
    assert payload.to_dict() == {"name": "renamed"}
    assert participant.name == "renamed"
    assert participant.price == 0.04
    assert participant.price_unit == "image"


def test_failed_rename_preserves_local_name() -> None:
    service = MagicMock()
    service.leaderboard.participant_api = MagicMock(spec=ParticipantApi)
    service.leaderboard.participant_api.participant_participant_id_patch.side_effect = (
        RuntimeError("request failed")
    )
    participant = BenchmarkParticipant(
        name="original",
        id="participant-1",
        openapi_service=service,
        benchmark_id="benchmark-1",
    )

    with pytest.raises(RuntimeError, match="request failed"):
        participant.rename("renamed")

    assert participant.name == "original"
