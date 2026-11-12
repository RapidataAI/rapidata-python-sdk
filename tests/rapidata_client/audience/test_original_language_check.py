"""OriginalLanguageOnlySetting needs a LanguageFilter on the labelers' audience.

Forward: job creation raises before the API call when the audience (or a filtered
audience's filter, or its base) has no LanguageFilter. Unlisted audiences are exempt.
Reverse: update_filters warns when new filters drop language while an active job
on the audience uses the setting.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import rapidata.rapidata_client.audience.rapidata_audience as audience_module
from rapidata.api_client.models.audience_job_state import AudienceJobState
from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
from rapidata.rapidata_client.audience._original_language_check import (
    filters_require_language,
    forces_original_language,
    requires_language,
)
from rapidata.rapidata_client.audience._rapidata_unlisted_audience import (
    RapidataUnlistedAudience,
)
from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
from rapidata.rapidata_client.audience.rapidata_filtered_audience import (
    RapidataFilteredAudience,
)
from rapidata.rapidata_client.filter import (
    AndFilter,
    CountryFilter,
    LanguageFilter,
    NotFilter,
    OrFilter,
)
from rapidata.rapidata_client.settings import (
    CustomSetting,
    NoShuffleSetting,
    OriginalLanguageOnlySetting,
)

EN = LanguageFilter(["en"])
US = CountryFilter(["US"])


@pytest.mark.parametrize(
    "filter_, expected",
    [
        (EN, True),
        (US, False),
        (AndFilter([US, EN]), True),
        (AndFilter([US]), False),
        (OrFilter([EN, LanguageFilter(["de"])]), True),
        (OrFilter([EN, US]), False),
        (OrFilter([]), False),
        (NotFilter(EN), False),
    ],
)
def test_requires_language(filter_, expected):
    assert requires_language(filter_) is expected


def test_filters_require_language_any_top_level():
    assert filters_require_language([US, EN])
    assert not filters_require_language([US])
    assert not filters_require_language([])


def test_forces_original_language_reads_loaded_revision_flags():
    assert forces_original_language([OriginalLanguageOnlySetting()])
    # job_definition.settings returns flags from the server as CustomSetting
    assert forces_original_language([CustomSetting("force_original_language", "true")])
    assert not forces_original_language(
        [CustomSetting("force_original_language", "false")]
    )
    assert not forces_original_language(
        [CustomSetting("force_original_language", "true", target="campaign")]
    )
    assert not forces_original_language([NoShuffleSetting()])


def _audience_response(filters: list, filter_=None) -> MagicMock:
    response = MagicMock()
    response.filters = [f._to_audience_model() for f in filters]
    response.filter = filter_._to_audience_model() if filter_ is not None else None
    return response


def _service(audience_filters: list, filtered=None) -> MagicMock:
    service = MagicMock()
    service.environment = "rapidata.ai"
    service.audience.audience_api.audience_audience_id_get.return_value = (
        _audience_response(audience_filters, filtered)
    )
    response = service.order.job_api.job_post.return_value
    response.job_id = "job-1"
    response.cost_warning = None
    response.content_check_skip_denied = None
    return service


def _definition(settings: list) -> MagicMock:
    return MagicMock(
        id="jdf-1",
        name="My Job",
        revision=1,
        has_unsaved_changes=False,
        settings=settings,
    )


def test_assign_job_rejects_flag_on_audience_without_language():
    service = _service([US])
    audience = RapidataAudienceBase(
        id="global", name="Global", filters=[], openapi_service=service
    )

    with pytest.raises(ValueError) as exc:
        audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    message = str(exc.value)
    assert "audience.filter([LanguageFilter" in message
    assert "update_filters" in message
    assert "remove OriginalLanguageOnlySetting" in message
    service.order.job_api.job_post.assert_not_called()


def test_assign_job_allows_flag_on_audience_with_language():
    service = _service([EN])
    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=service
    )

    audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    service.order.job_api.job_post.assert_called_once()


@pytest.mark.parametrize(
    "base_filters, fau_filter",
    [([], AndFilter([US, EN])), ([EN], US)],
    ids=["language-on-filter", "language-on-base"],
)
def test_assign_job_allows_flag_on_filtered_audience(base_filters, fau_filter):
    service = _service(base_filters, fau_filter)
    audience = RapidataFilteredAudience(
        id="fau_1", name="Global", filters=[fau_filter], openapi_service=service
    )

    audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    service.order.job_api.job_post.assert_called_once()


def test_assign_job_rejects_flag_on_filtered_audience_without_language():
    service = _service([], US)
    audience = RapidataFilteredAudience(
        id="fau_1", name="Global", filters=[US], openapi_service=service
    )

    with pytest.raises(ValueError):
        audience.assign_job(_definition([OriginalLanguageOnlySetting()]))
    service.order.job_api.job_post.assert_not_called()


def test_assign_job_without_flag_skips_audience_lookup():
    service = _service([])
    audience = RapidataAudienceBase(
        id="global", name="Global", filters=[], openapi_service=service
    )

    audience.assign_job(_definition([NoShuffleSetting()]))

    service.audience.audience_api.audience_audience_id_get.assert_not_called()
    service.order.job_api.job_post.assert_called_once()


def test_assign_job_unlisted_audience_is_exempt():
    service = _service([])
    audience = RapidataUnlistedAudience(
        id="ula_1", name="Mine", openapi_service=service
    )

    audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    service.audience.audience_api.audience_audience_id_get.assert_not_called()
    service.order.job_api.job_post.assert_called_once()


def test_assign_job_defers_to_backend_when_lookup_fails():
    service = _service([])
    service.audience.audience_api.audience_audience_id_get.side_effect = RuntimeError
    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=service
    )

    audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    service.order.job_api.job_post.assert_called_once()


def _job(job_id: str, definition_id: str, revision: int) -> MagicMock:
    return MagicMock(
        job_id=job_id, job_definition_id=definition_id, revision_number=revision
    )


def _flags(force: bool) -> MagicMock:
    revision = MagicMock()
    revision.feature_flags = (
        [MagicMock(key="force_original_language", value="true")] if force else []
    )
    return revision


def _audience_with_jobs(jobs: list, flagged_definitions: set[str]):
    service = MagicMock()
    job_api = service.order.job_api
    job_api.jobs_get.return_value.items = jobs
    job_api.job_definition_definition_id_revision_revision_number_get.side_effect = (
        lambda definition_id, revision_number: _flags(
            definition_id in flagged_definitions
        )
    )
    audience = RapidataAudience(
        id="aud-1", name="Aud", filters=[EN], openapi_service=service
    )
    return audience, service


def test_update_filters_warns_when_dropping_language_under_flagged_job(monkeypatch):
    audience, service = _audience_with_jobs(
        [
            _job("job-a", "jdf-1", 1),
            _job("job-b", "jdf-1", 1),
            _job("job-c", "jdf-2", 3),
        ],
        flagged_definitions={"jdf-1"},
    )
    warn = MagicMock()
    monkeypatch.setattr(audience_module.logger, "warning", warn)

    audience.update_filters([US])

    warn.assert_called_once()
    assert "job-a, job-b" in warn.call_args.args
    query = service.order.job_api.jobs_get.call_args.kwargs
    assert query["audience_id"].eq == "aud-1"
    assert set(query["state"].var_in) == {
        s.value
        for s in AudienceJobState
        if s.value not in {"Completed", "Failed", "StaleResults"}
    }
    # one revision read per distinct (definition, revision), not per job
    revision_get = (
        service.order.job_api.job_definition_definition_id_revision_revision_number_get
    )
    assert revision_get.call_count == 2
    service.audience.audience_api.audience_audience_id_patch.assert_called_once()


def test_update_filters_keeping_language_makes_no_extra_request(monkeypatch):
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1)], flagged_definitions={"jdf-1"}
    )
    warn = MagicMock()
    monkeypatch.setattr(audience_module.logger, "warning", warn)

    audience.update_filters([AndFilter([US, LanguageFilter(["de"])])])

    warn.assert_not_called()
    service.order.job_api.jobs_get.assert_not_called()


def test_update_filters_no_warning_without_flagged_jobs(monkeypatch):
    audience, _ = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1)], flagged_definitions=set()
    )
    warn = MagicMock()
    monkeypatch.setattr(audience_module.logger, "warning", warn)

    audience.update_filters([])

    warn.assert_not_called()


def test_update_filters_pages_through_active_jobs():
    audience, service = _audience_with_jobs([], flagged_definitions=set())
    full_page = MagicMock(items=[_job(f"job-{i}", "jdf-1", 1) for i in range(100)])
    last_page = MagicMock(items=[_job("job-100", "jdf-2", 1)])
    service.order.job_api.jobs_get.side_effect = [full_page, last_page]

    audience.update_filters([])

    assert service.order.job_api.jobs_get.call_count == 2


def test_update_filters_still_patches_when_job_lookup_fails():
    audience, service = _audience_with_jobs([], flagged_definitions=set())
    service.order.job_api.jobs_get.side_effect = RuntimeError

    audience.update_filters([])

    service.audience.audience_api.audience_audience_id_patch.assert_called_once()
