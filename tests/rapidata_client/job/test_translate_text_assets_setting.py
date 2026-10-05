from __future__ import annotations

from unittest.mock import MagicMock, patch

from rapidata import RapidataSettings
from rapidata.api_client.models.feature_flag import FeatureFlag
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager

MODULE = "rapidata.rapidata_client.job.rapidata_job_manager"


def _create_text_compare(settings):
    manager = RapidataJobManager(MagicMock())
    with patch(f"{MODULE}.JobDefinitionCreationMachine") as machine:
        manager.create_compare_job_definition(
            name="Text compare",
            instruction="Which response is more helpful?",
            datapoints=[["Response A", "Response B"]],
            data_type="text",
            settings=settings,
        )
    return machine.call_args.kwargs["rapid_feature_flags"]


def test_translate_text_assets_sent_as_rapid_feature_flag():
    flags = _create_text_compare([RapidataSettings.TranslateTextAssets()])

    assert flags == [FeatureFlag(key="translate_text_assets", value="True")]


def test_translate_text_assets_absent_by_default():
    assert not _create_text_compare(None)
