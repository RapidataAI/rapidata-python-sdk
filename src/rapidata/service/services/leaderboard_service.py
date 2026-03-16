from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.leaderboard_api import LeaderboardApi
    from rapidata.api_client.api.benchmark_api import BenchmarkApi
    from rapidata.api_client.api.participant_api import ParticipantApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class LeaderboardService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._leaderboard_api: LeaderboardApi | None = None
        self._benchmark_api: BenchmarkApi | None = None
        self._participant_api: ParticipantApi | None = None

    @property
    def leaderboard_api(self) -> LeaderboardApi:
        if self._leaderboard_api is None:
            from rapidata.api_client.api.leaderboard_api import LeaderboardApi
            self._leaderboard_api = LeaderboardApi(self._api_client)
        return self._leaderboard_api

    @property
    def benchmark_api(self) -> BenchmarkApi:
        if self._benchmark_api is None:
            from rapidata.api_client.api.benchmark_api import BenchmarkApi
            self._benchmark_api = BenchmarkApi(self._api_client)
        return self._benchmark_api

    @property
    def participant_api(self) -> ParticipantApi:
        if self._participant_api is None:
            from rapidata.api_client.api.participant_api import ParticipantApi
            self._participant_api = ParticipantApi(self._api_client)
        return self._participant_api
