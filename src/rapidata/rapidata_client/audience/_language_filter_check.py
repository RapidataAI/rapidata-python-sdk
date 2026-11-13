from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

from rapidata.rapidata_client.config import logger

if TYPE_CHECKING:
    from rapidata.api_client.models.i_asset import IAsset
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.service.openapi_service import OpenAPIService

FORCE_ORIGINAL_LANGUAGE_KEY = "force_original_language"
TRANSLATE_TEXT_ASSETS_KEY = "translate_text_assets"

ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER = (
    "OriginalLanguageOnlySetting requires every labeler to pass a LanguageFilter, "
    "otherwise non-speakers see untranslated text. Fix it in one of three ways: "
    "run the job on a filtered audience whose filter includes a LanguageFilter "
    "(audience.filter([LanguageFilter([...])])), add a LanguageFilter to the audience "
    "itself (audience.update_filters([...])), or remove OriginalLanguageOnlySetting "
    "from the job definition."
)

TEXT_ASSETS_REQUIRE_LANGUAGE_FILTER = (
    'Text assets (data_type="text" datapoints and text context assets) are shown '
    "exactly as uploaded, so labelers who don't read their language see text they can't "
    "answer. Fix it in one of three ways: add TranslateTextAssetsSetting() to the job "
    "definition (the text is assumed to be English), run the job on a filtered audience "
    "whose filter includes a LanguageFilter (audience.filter([LanguageFilter([...])])), "
    "or add a LanguageFilter to the audience itself (audience.update_filters([...]))."
)

SKIP_HINT = (
    "To override deliberately, set rapidata_config.skipLanguageFilterCheck = True."
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


def _flag_on(flags: Iterable[Any], key: str) -> bool:
    """Accepts settings and wire ``FeatureFlag``s; only rapid-level flags count."""
    return any(
        f.key == key
        and str(f.value).lower() == "true"
        and getattr(f, "target", "rapids") == "rapids"
        for f in flags
    )


def forces_original_language(flags: Iterable[Any]) -> bool:
    return _flag_on(flags, FORCE_ORIGINAL_LANGUAGE_KEY)


def language_requirement(
    flags: Sequence[Any], has_text_assets: Callable[[], bool]
) -> str | None:
    """Why the job needs a LanguageFilter, or None. ``has_text_assets`` runs only when it decides."""
    if forces_original_language(flags):
        return ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER
    if _flag_on(flags, TRANSLATE_TEXT_ASSETS_KEY):
        return None
    if has_text_assets():
        return TEXT_ASSETS_REQUIRE_LANGUAGE_FILTER
    return None


def asset_has_text(asset: IAsset | None) -> bool:
    from rapidata.api_client.models.i_asset_multi_asset import IAssetMultiAsset
    from rapidata.api_client.models.i_asset_text_asset import IAssetTextAsset

    instance = asset.actual_instance if asset is not None else None
    if isinstance(instance, IAssetTextAsset):
        return True
    if isinstance(instance, IAssetMultiAsset):
        return any(asset_has_text(child) for child in instance.assets)
    return False


def dataset_has_text_assets(openapi_service: OpenAPIService, dataset_id: str) -> bool:
    """Samples the first datapoint: the SDK uploads every datapoint of a dataset with one data_type."""
    response = openapi_service.dataset.datapoints_api.dataset_dataset_id_datapoints_get(
        dataset_id=dataset_id, page=1, page_size=1
    )
    return any(
        asset_has_text(segment.asset)
        for datapoint in response.items
        for segment in datapoint.segments
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


@dataclass
class JobsNeedingLanguage:
    original_language: list[str] = field(default_factory=list)
    text_assets: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.original_language or self.text_assets)


def active_jobs_needing_language(
    openapi_service: OpenAPIService, audience_id: str
) -> JobsNeedingLanguage:
    """The audience's non-terminal jobs that need a LanguageFilter, by reason.

    Costs one jobs query per 100 active jobs, one revision read per distinct
    (definition, revision) and one datapoint read per untranslated revision's dataset.
    Jobs on filtered audiences derived from this one are not listed.
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

    result = JobsNeedingLanguage()
    text_by_dataset: dict[str, bool] = {}
    for (definition_id, revision_number), job_ids in jobs_by_revision.items():
        revision = job_api.job_definition_definition_id_revision_revision_number_get(
            definition_id=definition_id, revision_number=revision_number
        )

        def has_text(dataset_id: str = revision.dataset_id) -> bool:
            if dataset_id not in text_by_dataset:
                text_by_dataset[dataset_id] = dataset_has_text_assets(
                    openapi_service, dataset_id
                )
            return text_by_dataset[dataset_id]

        reason = language_requirement(revision.feature_flags, has_text)
        if reason is ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER:
            result.original_language.extend(job_ids)
        elif reason is TEXT_ASSETS_REQUIRE_LANGUAGE_FILTER:
            result.text_assets.extend(job_ids)
    logger.debug(
        "Audience %s: %d active revisions, %d datasets sampled, needing language: %s",
        audience_id,
        len(jobs_by_revision),
        len(text_by_dataset),
        result,
    )
    return result
