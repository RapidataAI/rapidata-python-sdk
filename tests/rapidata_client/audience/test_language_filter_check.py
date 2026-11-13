"""Untranslated text needs a LanguageFilter on the labelers' audience.

A job shows untranslated text when it uses OriginalLanguageOnlySetting, or has text
assets without TranslateTextAssetsSetting. Forward: job creation raises before the API
call when the audience (or a filtered audience's filter, or its base) has no
LanguageFilter; unlisted audiences are exempt. Reverse: update_filters raises when new
filters drop language under such an active job. skipLanguageFilterCheck skips both.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.audience_job_state import AudienceJobState
from rapidata.api_client.models.feature_flag import FeatureFlag
from rapidata.api_client.models.i_asset import IAsset
from rapidata.api_client.models.i_asset_file_asset import IAssetFileAsset
from rapidata.api_client.models.i_asset_multi_asset import IAssetMultiAsset
from rapidata.api_client.models.i_asset_text_asset import IAssetTextAsset
from rapidata.rapidata_client.config import rapidata_config
from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
from rapidata.rapidata_client.audience._language_filter_check import (
    ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER,
    TEXT_ASSETS_REQUIRE_LANGUAGE_FILTER,
    asset_has_text,
    dataset_has_text_assets,
    language_requirement,
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
    TranslateTextAssetsSetting,
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


def _definition(settings: list, text: bool = False) -> MagicMock:
    return MagicMock(
        id="jdf-1",
        name="My Job",
        revision=1,
        has_unsaved_changes=False,
        settings=settings,
        _has_text_assets=MagicMock(return_value=text),
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
    assert "skipLanguageFilterCheck" in message
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


def test_assign_job_override_skips_check(monkeypatch):
    service = _service([US])
    audience = RapidataAudienceBase(
        id="global", name="Global", filters=[], openapi_service=service
    )
    monkeypatch.setattr(rapidata_config, "skipLanguageFilterCheck", True)

    audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    service.audience.audience_api.audience_audience_id_get.assert_not_called()
    service.order.job_api.job_post.assert_called_once()


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


def test_assign_job_proceeds_when_lookup_fails():
    service = _service([])
    service.audience.audience_api.audience_audience_id_get.side_effect = RuntimeError
    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=service
    )

    audience.assign_job(_definition([OriginalLanguageOnlySetting()]))

    service.order.job_api.job_post.assert_called_once()


def _text(text: str = "hello") -> IAsset:
    return IAsset(
        actual_instance=IAssetTextAsset(
            _t="TextAsset", text=text, metadata={}, identifier=text
        )
    )


def _file(name: str = "a.png") -> IAsset:
    return IAsset(
        actual_instance=IAssetFileAsset.model_construct(_t="FileAsset", file_name=name)
    )


def _multi(*assets: IAsset) -> IAsset:
    return IAsset(
        actual_instance=IAssetMultiAsset(
            _t="MultiAsset", assets=list(assets), metadata={}, identifier="m"
        )
    )


@pytest.mark.parametrize(
    "asset, expected",
    [
        (_text(), True),
        (_file(), False),
        (_multi(_text("a"), _text("b")), True),
        (_multi(_file(), _file()), False),
        (None, False),
    ],
)
def test_asset_has_text(asset, expected):
    assert asset_has_text(asset) is expected


def _datapoints(*segment_assets) -> MagicMock:
    page = MagicMock()
    page.items = (
        [MagicMock(segments=[MagicMock(asset=a) for a in segment_assets])]
        if segment_assets
        else []
    )
    return page


def test_dataset_has_text_assets_reads_one_datapoint():
    service = MagicMock()
    get = service.dataset.datapoints_api.dataset_dataset_id_datapoints_get
    get.return_value = _datapoints(_file(), _text())  # text context asset

    assert dataset_has_text_assets(service, "ds-1")
    assert get.call_args.kwargs["page_size"] == 1

    get.return_value = _datapoints(_file(), None)
    assert not dataset_has_text_assets(service, "ds-1")
    get.return_value = _datapoints()
    assert not dataset_has_text_assets(service, "ds-1")


@pytest.mark.parametrize(
    "settings, text, expected",
    [
        ([], False, None),
        ([], True, TEXT_ASSETS_REQUIRE_LANGUAGE_FILTER),
        ([TranslateTextAssetsSetting()], True, None),
        (
            [OriginalLanguageOnlySetting()],
            False,
            ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER,
        ),
        (
            [OriginalLanguageOnlySetting(), TranslateTextAssetsSetting()],
            True,
            ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER,
        ),
    ],
    ids=[
        "media",
        "text",
        "text-translated",
        "original",
        "original-overrides-translate",
    ],
)
def test_language_requirement(settings, text, expected):
    assert language_requirement(settings, lambda: text) is expected


def test_language_requirement_skips_text_lookup_when_settings_decide():
    lookup = MagicMock(return_value=True)

    language_requirement([TranslateTextAssetsSetting()], lookup)
    language_requirement([OriginalLanguageOnlySetting()], lookup)

    lookup.assert_not_called()


def test_assign_job_rejects_text_assets_on_audience_without_language():
    service = _service([US])
    audience = RapidataAudienceBase(
        id="global", name="Global", filters=[], openapi_service=service
    )

    with pytest.raises(ValueError) as exc:
        audience.assign_job(_definition([], text=True))

    message = str(exc.value)
    assert "TranslateTextAssetsSetting()" in message
    assert "audience.filter([LanguageFilter" in message
    assert "OriginalLanguageOnlySetting" not in message
    service.order.job_api.job_post.assert_not_called()


@pytest.mark.parametrize(
    "audience_filters, settings",
    [([], [TranslateTextAssetsSetting()]), ([EN], [])],
    ids=["translated", "language-filter"],
)
def test_assign_job_allows_text_assets_when_fixed(audience_filters, settings):
    service = _service(audience_filters)
    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=service
    )

    audience.assign_job(_definition(settings, text=True))

    service.order.job_api.job_post.assert_called_once()


def test_assign_job_text_assets_with_both_settings_reports_original_language_once():
    service = _service([])
    audience = RapidataAudienceBase(
        id="global", name="Global", filters=[], openapi_service=service
    )
    definition = _definition(
        [OriginalLanguageOnlySetting(), TranslateTextAssetsSetting()], text=True
    )

    with pytest.raises(ValueError) as exc:
        audience.assign_job(definition)

    assert ORIGINAL_LANGUAGE_REQUIRES_LANGUAGE_FILTER in str(exc.value)
    assert TEXT_ASSETS_REQUIRE_LANGUAGE_FILTER not in str(exc.value)
    definition._has_text_assets.assert_not_called()


def test_assign_job_unlisted_audience_exempt_from_text_check():
    service = _service([])
    audience = RapidataUnlistedAudience(
        id="ula_1", name="Mine", openapi_service=service
    )
    definition = _definition([], text=True)

    audience.assign_job(definition)

    definition._has_text_assets.assert_not_called()
    service.order.job_api.job_post.assert_called_once()


def test_assign_job_text_assets_override(monkeypatch):
    service = _service([])
    audience = RapidataAudienceBase(
        id="global", name="Global", filters=[], openapi_service=service
    )
    monkeypatch.setattr(rapidata_config, "skipLanguageFilterCheck", True)

    audience.assign_job(_definition([], text=True))

    service.order.job_api.job_post.assert_called_once()


def _job(job_id: str, definition_id: str, revision: int) -> MagicMock:
    return MagicMock(
        job_id=job_id, job_definition_id=definition_id, revision_number=revision
    )


def _revision(flags: list[str], dataset_id: str) -> MagicMock:
    revision = MagicMock()
    revision.dataset_id = dataset_id
    revision.feature_flags = [FeatureFlag(key=key, value="true") for key in flags]
    return revision


def _audience_with_jobs(
    jobs: list,
    flagged_definitions: set[str] = frozenset(),
    text_definitions: set[str] = frozenset(),
    translated_definitions: set[str] = frozenset(),
):
    """Each definition has its own dataset ``ds-<definition>``."""
    service = MagicMock()
    job_api = service.order.job_api
    job_api.jobs_get.return_value.items = jobs

    def revision(definition_id: str, revision_number: int) -> MagicMock:
        flags = []
        if definition_id in flagged_definitions:
            flags.append("force_original_language")
        if definition_id in translated_definitions:
            flags.append("translate_text_assets")
        return _revision(flags, f"ds-{definition_id}")

    job_api.job_definition_definition_id_revision_revision_number_get.side_effect = (
        revision
    )
    service.dataset.datapoints_api.dataset_dataset_id_datapoints_get.side_effect = (
        lambda dataset_id, page, page_size: _datapoints(
            _text() if dataset_id.removeprefix("ds-") in text_definitions else _file()
        )
    )
    audience = RapidataAudience(
        id="aud-1", name="Aud", filters=[EN], openapi_service=service
    )
    return audience, service


def test_update_filters_rejects_dropping_language_under_flagged_job():
    audience, service = _audience_with_jobs(
        [
            _job("job-a", "jdf-1", 1),
            _job("job-b", "jdf-1", 1),
            _job("job-c", "jdf-2", 3),
        ],
        flagged_definitions={"jdf-1"},
    )

    with pytest.raises(ValueError) as exc:
        audience.update_filters([US])

    assert "job-a, job-b use OriginalLanguageOnlySetting" in str(exc.value)
    assert "text assets" not in str(exc.value)
    assert "skipLanguageFilterCheck" in str(exc.value)
    service.audience.audience_api.audience_audience_id_patch.assert_not_called()
    assert audience.filters == [EN]
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


def test_update_filters_rejects_dropping_language_under_text_job():
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1), _job("job-b", "jdf-2", 1)],
        text_definitions={"jdf-2"},
    )

    with pytest.raises(ValueError) as exc:
        audience.update_filters([])

    assert "job-b have text assets without TranslateTextAssetsSetting" in str(exc.value)
    assert "job-a" not in str(exc.value)
    service.audience.audience_api.audience_audience_id_patch.assert_not_called()


def test_update_filters_lists_each_job_under_one_reason():
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1), _job("job-b", "jdf-2", 1)],
        flagged_definitions={"jdf-1"},
        text_definitions={"jdf-1", "jdf-2"},
    )

    with pytest.raises(ValueError) as exc:
        audience.update_filters([])

    message = str(exc.value)
    assert "job-a use OriginalLanguageOnlySetting" in message
    assert "job-b have text assets" in message
    # the flagged revision decides without reading its dataset
    datapoints_get = service.dataset.datapoints_api.dataset_dataset_id_datapoints_get
    assert [c.kwargs["dataset_id"] for c in datapoints_get.call_args_list] == [
        "ds-jdf-2"
    ]


def test_update_filters_allows_translated_text_job():
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1)],
        text_definitions={"jdf-1"},
        translated_definitions={"jdf-1"},
    )

    audience.update_filters([])

    service.dataset.datapoints_api.dataset_dataset_id_datapoints_get.assert_not_called()
    service.audience.audience_api.audience_audience_id_patch.assert_called_once()


def test_update_filters_reads_each_dataset_once():
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1), _job("job-b", "jdf-1", 2)]
    )

    audience.update_filters([])

    datapoints_get = service.dataset.datapoints_api.dataset_dataset_id_datapoints_get
    assert datapoints_get.call_count == 1
    service.audience.audience_api.audience_audience_id_patch.assert_called_once()


def test_update_filters_override_skips_check(monkeypatch):
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1)],
        flagged_definitions={"jdf-1"},
        text_definitions={"jdf-1"},
    )
    monkeypatch.setattr(rapidata_config, "skipLanguageFilterCheck", True)

    audience.update_filters([US])

    service.order.job_api.jobs_get.assert_not_called()
    service.audience.audience_api.audience_audience_id_patch.assert_called_once()


def test_update_filters_keeping_language_makes_no_extra_request():
    audience, service = _audience_with_jobs(
        [_job("job-a", "jdf-1", 1)], flagged_definitions={"jdf-1"}
    )

    audience.update_filters([AndFilter([US, LanguageFilter(["de"])])])

    service.order.job_api.jobs_get.assert_not_called()
    service.audience.audience_api.audience_audience_id_patch.assert_called_once()


def test_update_filters_allowed_without_flagged_jobs():
    audience, service = _audience_with_jobs([_job("job-a", "jdf-1", 1)])

    audience.update_filters([])

    service.audience.audience_api.audience_audience_id_patch.assert_called_once()


def test_update_filters_pages_through_active_jobs():
    audience, service = _audience_with_jobs([])
    full_page = MagicMock(items=[_job(f"job-{i}", "jdf-1", 1) for i in range(100)])
    last_page = MagicMock(items=[_job("job-100", "jdf-2", 1)])
    service.order.job_api.jobs_get.side_effect = [full_page, last_page]

    audience.update_filters([])

    assert service.order.job_api.jobs_get.call_count == 2


def test_update_filters_still_patches_when_job_lookup_fails():
    audience, service = _audience_with_jobs([])
    service.order.job_api.jobs_get.side_effect = RuntimeError

    audience.update_filters([])

    service.audience.audience_api.audience_audience_id_patch.assert_called_once()
