"""Tests for benchmark participant states: deprecated, not public, candidate.

Deprecating, restoring and promoting go through the participant's own endpoints,
the visibility and candidate flags are set once on ``add_model``, and the score
reads leave deprecated models out unless ``include_deprecated`` asks for them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from rapidata.api_client.api.participant_api import ParticipantApi
from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.models.participant_status import ParticipantStatus
from rapidata.api_client.models.standing_status import StandingStatus
from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
    RapidataLeaderboard,
)
from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


# Prod GET /benchmark/bmk_1Tv91mr3qi4xPE/standings/query?include_deprecated_participants[eq]=true
# on 2026-11-06, two rows; the deprecated row's status is set to a value no release knows.
_RECORDED_STANDINGS = """
{"totalResponses": 461689, "items": [
  {"id": "par_1Tv9LemOK2VZzK", "name": "Wan 3.0", "family": null, "lab": "Alibaba Cloud",
   "proprietaryName": null, "licenseType": null, "cost": 0.2, "costUnit": "UsdPerVideoSecond",
   "logo": "https://assets.rapidata.ai/4e833ae2-cc7a-4d25-a3ba-580fcbc4e3bd.png",
   "status": "Idle", "score": 1247.9522034109998, "wins": 7402, "totalMatches": 11439,
   "responseCount": 57196, "isEvaluating": false, "isDeprecated": false, "isDisabled": false,
   "isPublic": true, "isCandidate": false,
   "confidenceInterval": {"lowerOffset": 14.920247415750055, "upperOffset": 14.920247415750055},
   "isPartiallyEvaluated": false},
  {"id": "par_1U5lzm2ROCDLaZ", "name": "Yume 1.5 (text only)", "family": null,
   "lab": "Shanghai AI Laboratory", "proprietaryName": null, "licenseType": null, "cost": null,
   "costUnit": null, "logo": "https://assets.rapidata.ai/2e748b54-6f54-41d2-9c7b-07ed2d6f85d1.png",
   "status": "Retired", "score": 806.7912576998004, "wins": 2496, "totalMatches": 6433,
   "responseCount": 32166, "isEvaluating": false, "isDeprecated": true, "isDisabled": true,
   "isPublic": true, "isCandidate": false,
   "confidenceInterval": {"lowerOffset": 19.566399827755504, "upperOffset": 19.56639982775539},
   "isPartiallyEvaluated": false}
]}
"""

# Prod GET /benchmark/bmk_1Tv91mr3qi4xPE/participants on 2026-11-06, the deprecated row, with
# "Disabled" swapped for the value the wire carries once released SDKs age out.
_RECORDED_PARTICIPANTS = """
{"total": 20, "page": 1, "pageSize": 50, "totalPages": 1, "items": [
  {"id": "par_1U5lzm2ROCDLaZ", "name": "Yume 1.5 (text only)", "benchmarkId": "bmk_1Tv91mr3qi4xPE",
   "family": null, "lab": "Shanghai AI Laboratory", "proprietaryName": null, "licenseType": null,
   "cost": null, "costUnit": null,
   "logo": "https://assets.rapidata.ai/2e748b54-6f54-41d2-9c7b-07ed2d6f85d1.png",
   "status": "Deprecated", "isDeprecated": true, "votesExcluded": true, "isPublic": true,
   "isCandidate": false, "coveredPromptCount": 600, "isEvaluating": false,
   "createdAt": "2026-09-03T11:59:01.102261+00:00"}
]}
"""


def test_standings_with_an_unknown_status_parse(caplog) -> None:
    result = ApiClient().deserialize(
        _RECORDED_STANDINGS,
        "QueryStandingsByBenchmarkEndpointOutput",
        "application/json",
    )

    assert [item.status for item in result.items] == [StandingStatus.IDLE, "Retired"]
    unknown = result.items[1].status
    assert isinstance(unknown, StandingStatus)
    assert unknown.value == "Retired"
    assert result.items[1].is_deprecated is True
    assert json.loads(result.to_json())["items"][1]["status"] == "Retired"
    assert "Validation failed" not in caplog.text


def test_participants_with_an_unknown_status_parse(caplog) -> None:
    result = ApiClient().deserialize(
        _RECORDED_PARTICIPANTS,
        "QueryParticipantsByBenchmarkEndpointPagedResultOfOutput",
        "application/json",
    )

    status = result.items[0].status
    assert isinstance(status, ParticipantStatus)
    assert status == "Deprecated"
    assert status is ParticipantStatus("Deprecated")
    assert status not in (ParticipantStatus.CREATED, ParticipantStatus.SUBMITTABLE)
    assert "Validation failed" not in caplog.text


def test_unknown_status_parses_when_the_generated_client_is_imported_first() -> None:
    code = (
        "from rapidata.api_client.api_client import ApiClient\n"
        "import sys\n"
        "result = ApiClient().deserialize(sys.stdin.read(), "
        "'QueryStandingsByBenchmarkEndpointOutput', 'application/json')\n"
        "assert result.items[1].status.value == 'Retired', result.items[1].status\n"
    )

    subprocess.run(
        [sys.executable, "-c", code],
        input=_RECORDED_STANDINGS,
        text=True,
        check=True,
        capture_output=True,
    )


def test_known_values_and_non_strings_stay_strict() -> None:
    assert ParticipantStatus("Disabled") is ParticipantStatus.DISABLED
    assert StandingStatus("Idle") is StandingStatus.IDLE
    assert "Deprecated" not in [member.value for member in ParticipantStatus]
    with pytest.raises(ValueError):
        ParticipantStatus(3)  # type: ignore[arg-type]


def _make_participant(
    status: ParticipantStatus = ParticipantStatus.SUBMITTED,
) -> BenchmarkParticipant:
    service = MagicMock()
    service.leaderboard.participant_api = MagicMock(spec=ParticipantApi)
    return BenchmarkParticipant(
        name="model-a",
        id="p-0",
        openapi_service=service,
        benchmark_id="bm-1",
        status=status,
    )


def _participant_api(participant: BenchmarkParticipant) -> MagicMock:
    return participant._openapi_service.leaderboard.participant_api


def test_deprecate_posts_disable_and_marks_disabled() -> None:
    participant = _make_participant()

    participant.deprecate()

    api = _participant_api(participant)
    api.participant_participant_id_disable_post.assert_called_once_with(
        participant_id="p-0"
    )
    assert participant.status == ParticipantStatus.DISABLED


def test_restore_posts_enable_and_marks_submitted() -> None:
    participant = _make_participant(ParticipantStatus.DISABLED)

    participant.restore()

    api = _participant_api(participant)
    api.participant_participant_id_enable_post.assert_called_once_with(
        participant_id="p-0"
    )
    assert participant.status == ParticipantStatus.SUBMITTED


@pytest.mark.parametrize(
    ("old", "new", "endpoint", "status"),
    [
        (
            "disable",
            "deprecate",
            "participant_participant_id_disable_post",
            ParticipantStatus.DISABLED,
        ),
        (
            "enable",
            "restore",
            "participant_participant_id_enable_post",
            ParticipantStatus.SUBMITTED,
        ),
    ],
)
def test_old_names_warn_and_still_work(old, new, endpoint, status) -> None:
    participant = _make_participant()

    with pytest.warns(DeprecationWarning, match=f"call {new}\\(\\) instead"):
        getattr(participant, old)()

    getattr(_participant_api(participant), endpoint).assert_called_once_with(
        participant_id="p-0"
    )
    assert participant.status == status


def test_failed_deprecate_keeps_local_status() -> None:
    participant = _make_participant()
    _participant_api(
        participant
    ).participant_participant_id_disable_post.side_effect = RuntimeError(
        "request failed"
    )

    with pytest.raises(RuntimeError, match="request failed"):
        participant.deprecate()

    assert participant.status == ParticipantStatus.SUBMITTED


def test_promote_posts_promote_and_keeps_status() -> None:
    participant = _make_participant()

    participant.promote()

    api = _participant_api(participant)
    api.participant_participant_id_promote_post.assert_called_once_with(
        participant_id="p-0"
    )
    assert participant.status == ParticipantStatus.SUBMITTED


def test_promote_propagates_the_server_rejection() -> None:
    participant = _make_participant()
    _participant_api(
        participant
    ).participant_participant_id_promote_post.side_effect = RuntimeError(
        "400: not a candidate"
    )

    with pytest.raises(RuntimeError, match="not a candidate"):
        participant.promote()


def _make_benchmark() -> RapidataBenchmark:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    svc.leaderboard.benchmark_api.benchmark_benchmark_id_participants_post.return_value.participant_id = (
        "p-new"
    )
    benchmark = RapidataBenchmark("bm", "bm-1", svc)
    setattr(benchmark, "_RapidataBenchmark__identifiers", ["scene_1"])
    return benchmark


def _create_payload(benchmark: RapidataBenchmark):
    create = (
        benchmark._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_participants_post
    )
    create.assert_called_once()
    return create.call_args.kwargs["create_benchmark_participant_endpoint_input"]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, {"isPublic": True, "isCandidate": False}),
        ({"is_public": False}, {"isPublic": False, "isCandidate": False}),
        ({"is_candidate": True}, {"isPublic": True, "isCandidate": True}),
    ],
)
def test_add_model_sends_visibility_and_candidate(kwargs, expected) -> None:
    benchmark = _make_benchmark()

    with patch.object(
        BenchmarkParticipant, "upload_media", return_value=(["scene_1"], [])
    ):
        participant = benchmark.add_model(
            name="model-new",
            media=["https://example.com/a.png"],
            identifiers=["scene_1"],
            **kwargs,
        )

    payload = _create_payload(benchmark).to_dict()
    assert {key: payload[key] for key in expected} == expected
    assert participant.id == "p-new"


def _sent_include_deprecated(call) -> str | None:
    return call.call_args.kwargs["include_deprecated_participants"].eq


def _make_leaderboard() -> RapidataLeaderboard:
    return RapidataLeaderboard(
        "lb",
        "Which is better?",
        False,
        False,
        False,
        2000,
        3,
        "bm-1",
        "lb-1",
        MagicMock(),
    )


def _leaderboard_api(leaderboard: RapidataLeaderboard) -> MagicMock:
    return leaderboard._RapidataLeaderboard__openapi_service.leaderboard.leaderboard_api  # type: ignore[attr-defined]


@pytest.mark.parametrize(("include", "sent"), [(False, None), (True, "true")])
def test_benchmark_reads_send_include_deprecated(include: bool, sent) -> None:
    benchmark = _make_benchmark()
    api = benchmark._openapi_service.leaderboard.benchmark_api
    api.benchmark_benchmark_id_standings_query_get.return_value.items = []
    api.benchmark_benchmark_id_matrix_query_get.return_value.data = []
    api.benchmark_benchmark_id_matrix_query_get.return_value.index = []
    api.benchmark_benchmark_id_matrix_query_get.return_value.columns = []

    benchmark.get_overall_standings(include_deprecated=include)
    benchmark.get_win_loss_matrix(include_deprecated=include)

    assert (
        _sent_include_deprecated(api.benchmark_benchmark_id_standings_query_get) == sent
    )
    assert _sent_include_deprecated(api.benchmark_benchmark_id_matrix_query_get) == sent


@pytest.mark.parametrize(("include", "sent"), [(False, None), (True, "true")])
def test_leaderboard_reads_send_include_deprecated(include: bool, sent) -> None:
    leaderboard = _make_leaderboard()
    api = _leaderboard_api(leaderboard)
    api.leaderboard_leaderboard_id_standings_query_get.return_value.items = []
    api.leaderboard_leaderboard_id_matrix_query_get.return_value.data = []
    api.leaderboard_leaderboard_id_matrix_query_get.return_value.index = []
    api.leaderboard_leaderboard_id_matrix_query_get.return_value.columns = []

    leaderboard.get_standings(include_deprecated=include)
    leaderboard.get_win_loss_matrix(include_deprecated=include)

    assert (
        _sent_include_deprecated(api.leaderboard_leaderboard_id_standings_query_get)
        == sent
    )
    assert (
        _sent_include_deprecated(api.leaderboard_leaderboard_id_matrix_query_get)
        == sent
    )
