"""Tests for ``BenchmarkParticipant.run``.

``run`` submits the participant through the batch endpoint as a batch of one —
the only submit response that carries the min-assets-per-prompt warning — and
logs that warning when the benchmark's gate fires.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from rapidata.api_client.models.participant_status import ParticipantStatus
from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)


def _make_participant() -> BenchmarkParticipant:
    svc = MagicMock()
    svc.leaderboard.participant_api.participants_submit_post.return_value.min_assets_per_prompt_warning = (
        None
    )
    return BenchmarkParticipant(
        name="model-a",
        id="p-0",
        openapi_service=svc,
        benchmark_id="bm-1",
    )


def test_run_submits_as_a_batch_of_one_and_marks_submitted() -> None:
    participant = _make_participant()

    participant.run()

    submit = (
        participant._openapi_service.leaderboard.participant_api.participants_submit_post
    )
    submit.assert_called_once()
    payload = submit.call_args.args[0]
    assert payload.participant_ids == ["p-0"]
    assert participant.status == ParticipantStatus.SUBMITTED


def test_run_logs_warning_for_underfilled_prompts() -> None:
    from rapidata.api_client.models.submit_participants_endpoint_batch_min_assets_per_prompt_warning import (
        SubmitParticipantsEndpointBatchMinAssetsPerPromptWarning,
    )
    from rapidata.api_client.models.submit_participants_endpoint_participant_underfilled_prompts import (
        SubmitParticipantsEndpointParticipantUnderfilledPrompts,
    )
    from rapidata.api_client.models.submit_participants_endpoint_underfilled_prompt import (
        SubmitParticipantsEndpointUnderfilledPrompt,
    )

    participant = _make_participant()
    participant._openapi_service.leaderboard.participant_api.participants_submit_post.return_value.min_assets_per_prompt_warning = SubmitParticipantsEndpointBatchMinAssetsPerPromptWarning(
        minAssetsPerPrompt=4,
        underfilledParticipants=[
            SubmitParticipantsEndpointParticipantUnderfilledPrompts(
                participantId="p-0",
                underfilledPrompts=[
                    SubmitParticipantsEndpointUnderfilledPrompt(
                        identifier="cat", assetCount=2
                    )
                ],
            )
        ],
    )

    with patch(
        "rapidata.rapidata_client.benchmark.participant.participant.logger"
    ) as mock_logger:
        participant.run()

    mock_logger.warning.assert_called_once()
    formatted = (
        mock_logger.warning.call_args.args[0] % mock_logger.warning.call_args.args[1:]
    )
    assert "model-a" in formatted
    assert "'cat' (2/4)" in formatted
