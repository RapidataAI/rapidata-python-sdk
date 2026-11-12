from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Sequence

from rapidata.rapidata_client.config import logger

if TYPE_CHECKING:
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.rapidata_client.settings import RapidataSetting
    from rapidata.service.openapi_service import OpenAPIService

FORCE_ORIGINAL_LANGUAGE_KEY = "force_original_language"

ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER = (
    "OriginalLanguageOnlySetting requires every labeler to pass a LanguageFilter, "
    "otherwise non-speakers see untranslated text. Fix it in one of three ways: "
    "run the job on a filtered audience whose filter includes a LanguageFilter "
    "(audience.filter([LanguageFilter([...])])), add a LanguageFilter to the audience "
    "itself (audience.update_filters([...])), or remove OriginalLanguageOnlySetting "
    "from the job definition."
)

_TERMINAL_JOB_STATES = {"Completed", "Failed", "StaleResults"}
_JOB_PAGE_SIZE = 100


def requires_language(filter: RapidataFilter) -> bool:
    """Whether every user matching ``filter`` matched a LanguageFilter. ``NotFilter`` never counts."""
    from rapidata.rapidata_client.filter.and_filter import AndFilter
    from rapidata.rapidata_client.filter.language_filter import LanguageFilter
    from rapidata.rapidata_client.filter.or_filter import OrFilter

    if isinstance(filter, LanguageFilter):
        return True
    if isinstance(filter, AndFilter):
        return any(requires_language(child) for child in filter.filters)
    if isinstance(filter, OrFilter):
        return len(filter.filters) > 0 and all(
            requires_language(child) for child in filter.filters
        )
    return False


def filters_require_language(filters: Iterable[RapidataFilter]) -> bool:
    return any(requires_language(f) for f in filters)


def forces_original_language(settings: Sequence[RapidataSetting]) -> bool:
    return any(
        s.key == FORCE_ORIGINAL_LANGUAGE_KEY
        and str(s.value).lower() == "true"
        and s.target == "rapids"
        for s in settings
    )


def audience_requires_language(
    openapi_service: OpenAPIService, audience_id: str
) -> bool:
    """One GET: a filtered audience returns its own filter plus its base audience's filters."""
    from rapidata.rapidata_client.filter._backend_filter_mapper import (
        BackendFilterMapper,
    )

    response = openapi_service.audience.audience_api.audience_audience_id_get(
        audience_id=audience_id
    )
    backend_filters = list(response.filters)
    if response.filter is not None:
        backend_filters.append(response.filter)
    return filters_require_language(
        BackendFilterMapper.backend_filter_from_rapidata_filter(f)
        for f in backend_filters
    )


def active_jobs_forcing_original_language(
    openapi_service: OpenAPIService, audience_id: str
) -> list[str]:
    """Ids of the audience's non-terminal jobs whose revision sets the flag.

    Costs one jobs query per 100 active jobs plus one revision read per distinct
    (definition, revision). Jobs on filtered audiences derived from this one are not listed.
    """
    from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
        AudienceAudienceIdJobsGetJobIdParameter,
    )
    from rapidata.api_client.models.audience_job_state import AudienceJobState

    job_api = openapi_service.order.job_api
    active_states = [
        s.value for s in AudienceJobState if s.value not in _TERMINAL_JOB_STATES
    ]
    jobs_by_revision: dict[tuple[str, int], list[str]] = {}
    page = 1
    while True:
        response = job_api.jobs_get(
            page=page,
            page_size=_JOB_PAGE_SIZE,
            audience_id=AudienceAudienceIdJobsGetJobIdParameter(eq=audience_id),
            state=AudienceAudienceIdJobsGetJobIdParameter.model_validate(
                {"in": active_states}
            ),
        )
        for job in response.items:
            key = (job.job_definition_id, job.revision_number)
            jobs_by_revision.setdefault(key, []).append(job.job_id)
        if len(response.items) < _JOB_PAGE_SIZE:
            break
        page += 1

    flagged: list[str] = []
    for (definition_id, revision_number), job_ids in jobs_by_revision.items():
        revision = job_api.job_definition_definition_id_revision_revision_number_get(
            definition_id=definition_id, revision_number=revision_number
        )
        if any(
            flag.key == FORCE_ORIGINAL_LANGUAGE_KEY
            and str(flag.value).lower() == "true"
            for flag in revision.feature_flags
        ):
            flagged.extend(job_ids)
    logger.debug(
        "Audience %s: %d active revisions checked, %d jobs force the original language",
        audience_id,
        len(jobs_by_revision),
        len(flagged),
    )
    return flagged
