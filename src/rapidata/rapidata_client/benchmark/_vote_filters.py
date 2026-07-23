from __future__ import annotations

from typing import NamedTuple, Optional, TYPE_CHECKING

from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
    AudienceAudienceIdJobsGetJobIdParameter,
)

if TYPE_CHECKING:
    from rapidata.rapidata_client.filter.models.gender import Gender
    from rapidata.rapidata_client.filter.models.age_group import AgeGroup


def in_filter(
    values: Optional[list[str]],
) -> AudienceAudienceIdJobsGetJobIdParameter:
    """Wrap a list of accepted values as an ``in`` filter (a no-op when None)."""
    param = AudienceAudienceIdJobsGetJobIdParameter()
    param.var_in = values
    return param


class DemographicFilters(NamedTuple):
    """The per-vote demographic filters shared by the benchmark and leaderboard
    standings, matrix, demographics and standings-breakdown endpoints.

    Each field is keyed to match the corresponding query-endpoint parameter, so a
    caller passes them straight through (``country=filters.country`` ...).
    """

    country: AudienceAudienceIdJobsGetJobIdParameter
    language: AudienceAudienceIdJobsGetJobIdParameter
    gender: AudienceAudienceIdJobsGetJobIdParameter
    age_bucket: AudienceAudienceIdJobsGetJobIdParameter
    occupation: AudienceAudienceIdJobsGetJobIdParameter
    run_id: AudienceAudienceIdJobsGetJobIdParameter


def demographic_filters(
    country: Optional[list[str]] = None,
    language: Optional[list[str]] = None,
    gender: Optional[list[Gender]] = None,
    age_bucket: Optional[list[AgeGroup]] = None,
    occupation: Optional[list[str]] = None,
    run_id: Optional[str] = None,
) -> DemographicFilters:
    """Build the demographic filters for a standings/matrix/demographics call.

    ``gender`` and ``age_bucket`` take the SDK's :class:`Gender` and :class:`AgeGroup`
    enums and are converted to their backend values; the open-ended dimensions are
    plain values. Unset filters become no-ops.
    """
    return DemographicFilters(
        country=in_filter(country),
        language=in_filter(language),
        gender=in_filter(
            [g._to_backend_model().value for g in gender] if gender else None
        ),
        age_bucket=in_filter(
            [a._to_backend_model().value for a in age_bucket] if age_bucket else None
        ),
        occupation=in_filter(occupation),
        run_id=in_filter([run_id] if run_id is not None else None),
    )
