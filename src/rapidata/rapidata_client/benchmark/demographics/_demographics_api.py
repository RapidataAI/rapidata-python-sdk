from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
    AudienceAudienceIdJobsGetJobIdParameter,
)
from rapidata.rapidata_client.benchmark.demographics.models import (
    BenchmarkDemographics,
    BenchmarkStandingsBreakdown,
)

if TYPE_CHECKING:
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient

# Field filters accepted by both endpoints — the same surface as
# `benchmark/{id}/standings/query`, so the backend parses them identically.
BENCHMARK_FILTER_FIELDS: Tuple[str, ...] = (
    "country",
    "language",
    "gender",
    "age_bucket",
    "occupation",
    "tags",
    "participant_id",
    "leaderboard_id",
    "run_id",
    "prompt_identifier",
    "voted_at",
)

# 2xx bodies are deserialized by hand below; only the error statuses need a
# mapping so `RapidataApiClient` wraps them into `RapidataError`.
_ERROR_RESPONSE_TYPES: Dict[str, Optional[str]] = {
    "400": "ValidationProblemDetails",
    "401": None,
    "403": None,
}


class BenchmarkDemographicsApi:
    """Thin client for the benchmark demographics and standings-breakdown endpoints.

    These endpoints are not part of the checked-in generated OpenAPI client yet.
    This wrapper talks to the same low-level ``RapidataApiClient`` the generated
    APIs use and mirrors their request/response handling; once the backend ships
    and the client is regenerated, the generated methods supersede it.
    """

    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client

    def get_demographics(
        self,
        benchmark_id: str,
        filters: Optional[Dict[str, AudienceAudienceIdJobsGetJobIdParameter]] = None,
    ) -> BenchmarkDemographics:
        raw = self._get(
            resource_path="/benchmark/{benchmarkId}/demographics",
            benchmark_id=benchmark_id,
            filters=filters or {},
        )
        return BenchmarkDemographics.model_validate(raw)

    def get_standings_breakdown(
        self,
        benchmark_id: str,
        dimension: str,
        filters: Optional[Dict[str, AudienceAudienceIdJobsGetJobIdParameter]] = None,
    ) -> BenchmarkStandingsBreakdown:
        raw = self._get(
            resource_path="/benchmark/{benchmarkId}/standings/breakdown",
            benchmark_id=benchmark_id,
            filters=filters or {},
            extra_query=[("dimension", dimension)],
        )
        return BenchmarkStandingsBreakdown.model_validate(raw)

    def _get(
        self,
        resource_path: str,
        benchmark_id: str,
        filters: Dict[str, AudienceAudienceIdJobsGetJobIdParameter],
        extra_query: Optional[List[Tuple[str, object]]] = None,
    ) -> dict:
        query_params: List[Tuple[str, object]] = []
        for field, param in filters.items():
            query_params.extend(self._explode_filter(field, param))
        if extra_query:
            query_params.extend((k, v) for k, v in extra_query if v is not None)

        header_params: Dict[str, Optional[str]] = {
            "Accept": self._api_client.select_header_accept(["application/json"])
        }

        _param = self._api_client.param_serialize(
            method="GET",
            resource_path=resource_path,
            path_params={"benchmarkId": benchmark_id},
            query_params=query_params,
            header_params=header_params,
            auth_settings=["OpenIdConnect"],
        )

        response = self._api_client.call_api(*_param)
        response.read()
        api_response = self._api_client.response_deserialize(
            response_data=response,
            response_types_map=_ERROR_RESPONSE_TYPES,
        )
        return json.loads(api_response.raw_data)

    @staticmethod
    def _explode_filter(
        field: str, param: AudienceAudienceIdJobsGetJobIdParameter
    ) -> List[Tuple[str, object]]:
        """Serialize a filter to repeated ``field[op]=value`` query params.

        Mirrors the generated ``standings/query`` serializer: list operators
        (e.g. ``in``) expand into one param per value.
        """
        exploded: List[Tuple[str, object]] = []
        for op, value in param.to_dict().items():
            if value is None:
                continue
            if isinstance(value, list):
                exploded.extend((f"{field}[{op}]", item) for item in value)
            else:
                exploded.append((f"{field}[{op}]", value))
        return exploded
