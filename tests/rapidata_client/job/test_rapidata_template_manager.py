"""client.job.template: check every pair, upload into one dataset, then one POST …/run."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx2
import pytest

from rapidata.api_client import rest
from rapidata.api_client.api.job_api import JobApi
from rapidata.api_client.configuration import Configuration
from rapidata.api_client.exceptions import ApiException
from rapidata.api_client.models.get_job_revision_endpoint_output import (
    GetJobRevisionEndpointOutput,
)
from rapidata.rapidata_client.config import rapidata_config
from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError
from rapidata.rapidata_client.job._template_ids import TEMPLATE_IDS, template_id
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager
from rapidata.rapidata_client.job.rapidata_template_manager import (
    RUN_REQUEST_TIMEOUT,
    RapidataTemplateManager,
    TemplateUploadException,
)

QUESTION = "Which image matches the description better?"
IMAGE_PAIRS = [["mine/cat.png", "flux/cat.png"], ["mine/dog.png", "flux/dog.png"]]
VIDEO_PAIRS = [["mine/cat.mp4", "flux/cat.mp4"], ["mine/dog.mp4", "flux/dog.mp4"]]
PROMPTS = ["A cat wearing a red scarf", "A dog surfing at sunset"]
METHODS = ["alignment", "preference", "coherence"]
STARTED = datetime(2026, 11, 11, 10, 14, 3, tzinfo=timezone.utc)
NO_ANSWER_MESSAGE = (
    "No answer from Rapidata, so a job may have started. Look for it with "
    "client.job.find_jobs(name) before calling again. This call's job would be named "
    "exactly 'my-model vs flux-2' and created after 2026-11-11 10:14:03 UTC."
)


def _revision(
    votes: int = 11,
    question: str = QUESTION,
    state: str = "Completed",
    number: int = 1,
) -> GetJobRevisionEndpointOutput:
    model = GetJobRevisionEndpointOutput.from_dict(
        {
            "definitionId": "jdf_template",
            "revisionNumber": number,
            "state": state,
            "pipelineId": "pip-1",
            "datasetId": "dst_sample",
            "workflow": {
                "_t": "SimpleWorkflow",
                "rapid": {
                    "_t": "Compare",
                    "asset": {"segment": "asset"},
                    "context": {"segment": "context"},
                    "criteria": {"literal": question},
                },
            },
            "referee": {"_t": "NaiveReferee", "totalVotes": votes},
            "featureFlags": [],
            "campaignFeatureFlags": [],
            "audienceId": "aud_MU1GZYoESyO",
            "createdAt": "2026-11-10T12:00:00Z",
            "createdById": "00000000-0000-0000-0000-000000000001",
            "createdByMail": "admin@rapidata.ai",
        }
    )
    assert model is not None
    return model


def _service(environment: str = "rapidata.ai") -> MagicMock:
    service = MagicMock()
    service.environment = environment
    job_api = service.order.job_api
    job_api.job_definition_definition_id_revision_get.return_value = _revision()
    job_api.job_definition_definition_id_run_post.return_value = MagicMock(
        job_id="job_1", definition_id="jdf_copy", cost_warning=None
    )
    job_api.job_job_id_get.return_value = MagicMock(
        job_id="job_1",
        audience_id="aud_MU1GZYoESyO",
        created_at=datetime(2026, 11, 10),
        definition_id="jdf_copy",
        pipeline_id="pip_1",
    )
    job_api.job_job_id_get.return_value.name = "my-model vs flux-2"
    service.dataset.dataset_api.dataset_post.return_value = MagicMock(
        dataset_id="dst_1"
    )
    return service


@pytest.fixture(autouse=True)
def _no_id_override(monkeypatch):
    monkeypatch.delenv("RAPIDATA_TEMPLATE_IDS", raising=False)


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return STARTED

    monkeypatch.setattr(
        "rapidata.rapidata_client.job.rapidata_template_manager.datetime", Clock
    )


@pytest.fixture
def dataset(monkeypatch) -> MagicMock:
    uploaded = MagicMock()
    uploaded.id = "dst_1"
    uploaded.add_datapoints.side_effect = lambda points: (points, [])
    monkeypatch.setattr(
        "rapidata.rapidata_client.dataset._rapidata_dataset.RapidataDataset",
        MagicMock(return_value=uploaded),
    )
    return uploaded


def _call(manager: RapidataTemplateManager, kind: str, datapoints, **kwargs):
    if kind == "alignment":
        kwargs.setdefault("contexts", PROMPTS[: len(datapoints)])
    return getattr(manager, f"run_{kind}")(
        name="my-model vs flux-2", datapoints=datapoints, **kwargs
    )


def _run_body(service: MagicMock) -> dict:
    call = service.order.job_api.job_definition_definition_id_run_post.call_args
    return call.kwargs["run_job_definition_endpoint_input"].to_dict()


def _dataset_body(service: MagicMock) -> dict:
    call = service.dataset.dataset_api.dataset_post.call_args
    return call.kwargs["create_dataset_endpoint_input"].to_dict()


def _assert_nothing_sent(service: MagicMock) -> None:
    service.order.job_api.job_definition_definition_id_revision_get.assert_not_called()
    service.dataset.dataset_api.dataset_post.assert_not_called()
    service.order.job_api.job_definition_definition_id_run_post.assert_not_called()


def test_alignment_uploads_into_a_dataset_with_the_question_then_runs_once(
    dataset, capsys
):
    service = _service()

    job = _call(RapidataTemplateManager(service), "alignment", IMAGE_PAIRS)

    assert _dataset_body(service) == {
        "name": "my-model vs flux-2",
        "contextShortening": {"question": QUESTION},
    }
    points = dataset.add_datapoints.call_args.args[0]
    assert [(p.asset, p.context) for p in points] == list(zip(IMAGE_PAIRS, PROMPTS))
    run = service.order.job_api.job_definition_definition_id_run_post
    run.assert_called_once()
    assert (
        run.call_args.kwargs["definition_id"]
        == TEMPLATE_IDS["rapidata.ai"]["alignment/image"]
    )
    assert run.call_args.kwargs["_request_timeout"] == RUN_REQUEST_TIMEOUT == (15, 130)
    assert _run_body(service) == {"name": "my-model vs flux-2", "datasetId": "dst_1"}
    assert (job.id, job.audience_id, job.definition_id) == (
        "job_1",
        "aud_MU1GZYoESyO",
        "jdf_copy",
    )
    assert capsys.readouterr().out == (
        "Job started: 2 pairs, 11 votes each\n"
        "https://app.rapidata.ai/audiences/aud_MU1GZYoESyO/job/job_1\n"
    )


@pytest.mark.parametrize("kind", METHODS)
@pytest.mark.parametrize(
    ("pairs", "media"), [(IMAGE_PAIRS, "image"), (VIDEO_PAIRS, "video")]
)
def test_each_method_runs_the_pinned_template_for_its_media(
    dataset, kind, pairs, media
):
    service = _service()

    _call(RapidataTemplateManager(service), kind, pairs)

    run = service.order.job_api.job_definition_definition_id_run_post
    assert (
        run.call_args.kwargs["definition_id"]
        == TEMPLATE_IDS["rapidata.ai"][f"{kind}/{media}"]
    )
    assert _run_body(service)["datasetId"] == "dst_1"


@pytest.mark.parametrize("kind", ["preference", "coherence"])
def test_preference_and_coherence_send_no_prompts_and_no_shortening(dataset, kind):
    service = _service()

    _call(RapidataTemplateManager(service), kind, IMAGE_PAIRS)

    assert _dataset_body(service) == {"name": "my-model vs flux-2"}
    points = dataset.add_datapoints.call_args.args[0]
    assert [p.context for p in points] == [None, None]


@pytest.mark.parametrize("kind", METHODS)
def test_a_b_names_go_out_as_a_name_and_b_name(dataset, kind):
    service = _service()

    _call(
        RapidataTemplateManager(service),
        kind,
        IMAGE_PAIRS,
        a_b_names=["my-model", "flux-2"],
    )

    assert _run_body(service) == {
        "name": "my-model vs flux-2",
        "datasetId": "dst_1",
        "aName": "my-model",
        "bName": "flux-2",
    }


def test_run_is_sent_without_unsafe_retries(dataset):
    service = _service()
    rule_during_run: list[bool] = []
    run = service.order.job_api.job_definition_definition_id_run_post
    run.side_effect = lambda **kwargs: (
        rule_during_run.append(rest._unsafe_retries.get()) or run.return_value
    )

    _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert rule_during_run == [False]
    assert rest._unsafe_retries.get() is True


def test_mixed_call_is_rejected_before_anything_is_sent(dataset):
    service = _service()
    pairs = [list(pair) for pair in IMAGE_PAIRS * 6]
    for index in (3, 7, 9):
        pairs[index] = [f"a{index}.mp4", f"b{index}.mp4"]
    pairs += [["c.png", "d.png"]] * 3

    with pytest.raises(ValueError) as raised:
        _call(
            RapidataTemplateManager(service),
            "alignment",
            pairs,
            contexts=["A cat"] * 15,
        )

    assert str(raised.value) == (
        "Images and videos can't be mixed in one call (the question depends on the "
        "media type): 12 datapoints are images, 3 are videos (datapoints[3], [7], [9]). "
        "Send them as two calls, one with only images and one with only videos."
    )
    _assert_nothing_sent(service)
    dataset.add_datapoints.assert_not_called()


def test_mixed_call_names_the_smaller_group_and_at_most_five_of_it():
    service = _service()
    pairs = [["a.png", "b.png"]] * 6 + [["a.mp4", "b.mp4"]] * 10

    with pytest.raises(ValueError) as raised:
        _call(RapidataTemplateManager(service), "coherence", pairs)

    assert (
        "6 datapoints are images (datapoints[0], [1], [2], [3], [4], …), 10 are videos."
        in str(raised.value)
    )
    _assert_nothing_sent(service)


@pytest.mark.parametrize(
    "pair",
    [
        ["only.png"],
        ["same.png", "same.png"],
        ["a.png", "b.png", "c.png"],
        "a.png",
    ],
)
def test_a_pair_must_be_two_different_files(pair):
    service = _service()

    with pytest.raises(ValueError, match=r"datapoints\[1\] must be a pair of 2"):
        _call(RapidataTemplateManager(service), "preference", [IMAGE_PAIRS[0], pair])

    _assert_nothing_sent(service)


def test_a_pair_of_an_image_and_a_video_is_rejected():
    service = _service()

    with pytest.raises(
        ValueError, match=r"datapoints\[0\] pairs an image with a video"
    ):
        _call(RapidataTemplateManager(service), "preference", [["a.png", "b.mp4"]])

    _assert_nothing_sent(service)


@pytest.mark.parametrize(
    "file", ["clip.mov", "voice.mp3", "https://cdn.example/x?id=1"]
)
def test_unknown_media_is_rejected_naming_the_file(file):
    service = _service()

    with pytest.raises(ValueError) as raised:
        _call(RapidataTemplateManager(service), "preference", [["a.png", file]])

    assert f"datapoints[0]: {file!r} is neither an image" in str(raised.value)
    _assert_nothing_sent(service)


def test_template_ids_override_wins(dataset, monkeypatch):
    service = _service()
    monkeypatch.setenv(
        "RAPIDATA_TEMPLATE_IDS", json.dumps({"coherence/video": "jdf_dev_coherence"})
    )

    _call(RapidataTemplateManager(service), "coherence", VIDEO_PAIRS)

    run = service.order.job_api.job_definition_definition_id_run_post
    assert run.call_args.kwargs["definition_id"] == "jdf_dev_coherence"


def test_an_environment_without_ids_names_itself_and_the_variable():
    service = _service(environment="rapidata.dev")

    with pytest.raises(ValueError) as raised:
        _call(RapidataTemplateManager(service), "alignment", IMAGE_PAIRS)

    assert "rapidata.dev" in str(raised.value)
    assert "RAPIDATA_TEMPLATE_IDS" in str(raised.value)
    _assert_nothing_sent(service)


@pytest.mark.parametrize("override", ['{"alignment/video": "jdf_x"}', "not json", "[]"])
def test_an_override_without_the_id_names_the_variable(monkeypatch, override):
    monkeypatch.setenv("RAPIDATA_TEMPLATE_IDS", override)

    with pytest.raises(ValueError, match="RAPIDATA_TEMPLATE_IDS"):
        template_id("rapidata.ai", "alignment/image")


@pytest.mark.parametrize("environment", ["rapidata.ai", "rabbitdata.ch"])
def test_every_environment_pins_all_six_templates(environment):
    assert sorted(TEMPLATE_IDS[environment]) == sorted(
        f"{kind}/{media}" for kind in METHODS for media in ("image", "video")
    )
    ids = list(TEMPLATE_IDS[environment].values())
    assert all(re.fullmatch(r"jdf_[0-9A-Za-z]{14}", i) for i in ids), ids
    assert len(set(ids)) == 6


def test_long_prompts_warn_before_the_upload(dataset, caplog):
    service = _service()
    logged_before_upload: list[str] = []
    service.dataset.dataset_api.dataset_post.side_effect = lambda **kwargs: (
        logged_before_upload.extend(r.getMessage() for r in caplog.records)
        or MagicMock(dataset_id="dst_1")
    )

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        _call(
            RapidataTemplateManager(service),
            "alignment",
            IMAGE_PAIRS,
            contexts=["A cat wearing a red scarf", "A dog surfing at sunset, " * 20],
        )

    assert logged_before_upload == [
        "1 of 2 prompts is longer than 200 characters. Keep prompts under 200 for "
        "better results: annotators read them on a phone.",
        "1 of 2 prompts is longer than 400 characters. Rapidata shortens it to what "
        "the question needs.",
    ]


def test_prompts_between_200_and_400_only_get_the_first_warning(dataset, caplog):
    with caplog.at_level(logging.WARNING, logger="rapidata"):
        _call(
            RapidataTemplateManager(_service()),
            "alignment",
            IMAGE_PAIRS,
            contexts=["x" * 201, "y" * 300],
        )

    assert [r.getMessage() for r in caplog.records] == [
        "2 of 2 prompts are longer than 200 characters. Keep prompts under 200 for "
        "better results: annotators read them on a phone."
    ]


@pytest.mark.parametrize(
    ("contexts", "message"),
    [
        (["only one"], "contexts has 1 prompts for 2 pairs"),
        (None, "contexts must be a list"),
        (["A cat", ""], r"contexts\[1\] is empty"),
        (["A cat", "   "], r"contexts\[1\] is empty"),
    ],
)
def test_alignment_needs_one_prompt_per_pair(contexts, message):
    service = _service()

    with pytest.raises(ValueError, match=message):
        _call(
            RapidataTemplateManager(service),
            "alignment",
            IMAGE_PAIRS,
            contexts=contexts,
        )

    _assert_nothing_sent(service)


@pytest.mark.parametrize(
    ("name", "a_b_names", "message"),
    [
        ("", None, "Name must be 1 to 256 characters."),
        ("x" * 257, None, "Name must be 1 to 256 characters."),
        ("   ", None, "Name must be 1 to 256 characters."),
        ("ok", ["only-one"], "a_b_names needs 2 different names"),
        ("ok", ["same", "same"], "a_b_names needs 2 different names"),
        ("ok", ["a", ""], "a_b_names needs 2 different names"),
        ("ok", ["my-model", " "], "a_b_names needs 2 different names"),
    ],
)
def test_bad_name_or_side_names_are_rejected_before_upload(name, a_b_names, message):
    service = _service()

    with pytest.raises(ValueError, match=message):
        RapidataTemplateManager(service).run_preference(
            name=name, datapoints=IMAGE_PAIRS, a_b_names=a_b_names
        )

    _assert_nothing_sent(service)


def test_a_failed_upload_raises_before_run_naming_the_dataset(dataset):
    service = _service()
    dataset.add_datapoints.side_effect = lambda points: (
        points[:1],
        [
            FailedUpload(
                item=points[1], error_message="404", error_type="AssetUploadFailed"
            )
        ],
    )

    with pytest.raises(FailedUploadException) as raised:
        _call(RapidataTemplateManager(service), "alignment", IMAGE_PAIRS)

    assert isinstance(raised.value, TemplateUploadException)
    assert str(raised.value).startswith(
        "1 of 2 pairs failed to upload into dataset dst_1, so no job was started. "
        "Fix them and call client.job.template.run_alignment() again."
    )
    assert "1 datapoint(s) failed to upload" in str(raised.value)
    assert "error_handling" not in str(raised.value)
    with pytest.raises(RuntimeError, match="can't be retried"):
        raised.value.retry()
    service.order.job_api.job_definition_definition_id_run_post.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        RapidataError(status_code=504, message="Gateway Timeout"),
        RapidataError(status_code=502, message="Bad Gateway"),
        RapidataError(status_code=503, message="Service Unavailable"),
        ApiException(status=0, reason="ReadTimeout\ntimed out"),
    ],
)
def test_no_answer_from_run_raises_once_naming_find_jobs(dataset, failure):
    service = _service()
    run = service.order.job_api.job_definition_definition_id_run_post
    run.side_effect = failure

    with pytest.raises(RapidataError) as raised:
        _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert raised.value.message == NO_ANSWER_MESSAGE
    assert "client.job.find_jobs(name)" in str(raised.value)
    run.assert_called_once()
    service.order.job_api.job_job_id_get.assert_not_called()


def test_a_500_from_run_may_have_started_a_job_too(dataset):
    service = _service()
    run = service.order.job_api.job_definition_definition_id_run_post
    run.side_effect = RapidataError(
        status_code=500, message="Internal Server Error", trace_id="4bf92f35"
    )

    with pytest.raises(RapidataError) as raised:
        _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert raised.value.message == NO_ANSWER_MESSAGE.replace(
        "No answer from Rapidata", "Rapidata failed while starting the job"
    )
    assert (raised.value.status_code, raised.value.trace_id) == (500, "4bf92f35")
    run.assert_called_once()


def test_other_run_errors_propagate_unchanged(dataset):
    service = _service()
    rejected = RapidataError(status_code=400, message="dst_1 has 3 pending datapoints")
    service.order.job_api.job_definition_definition_id_run_post.side_effect = rejected

    with pytest.raises(RapidataError) as raised:
        _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert raised.value is rejected


@pytest.mark.parametrize(
    "failure", [504, httpx2.ReadTimeout("no response"), httpx2.ReadError("reset")]
)
def test_through_the_real_client_a_lost_answer_is_sent_once(monkeypatch, failure):
    api_client = RapidataApiClient(
        configuration=Configuration(host="https://api.rapidata.ai")
    )
    rest_client = api_client.rest_client
    rest_client.session = MagicMock()
    attempts: list[int] = []

    def send(*args, **kwargs):
        attempts.append(1)
        if isinstance(failure, Exception):
            raise failure
        return httpx2.Response(
            failure, request=httpx2.Request("POST", "https://api.rapidata.ai")
        )

    monkeypatch.setattr(rest_client, "_send_request", send)
    monkeypatch.setattr(rest.time, "sleep", lambda _: None)
    service = MagicMock()
    service.order.job_api = JobApi(api_client)

    with pytest.raises(RapidataError) as raised:
        RapidataTemplateManager(service)._start(
            "jdf_1", "my-model vs flux-2", "dst_1", None, STARTED
        )

    assert raised.value.message == NO_ANSWER_MESSAGE
    assert len(attempts) == 1


def test_a_failed_read_after_the_start_names_the_job(dataset):
    service = _service()
    service.order.job_api.job_job_id_get.side_effect = RapidataError(
        status_code=500, message="boom", trace_id="4bf92f35"
    )

    with pytest.raises(RapidataError) as raised:
        _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert "client.job.get_job_by_id('job_1')" in str(raised.value)
    assert (raised.value.status_code, raised.value.trace_id) == (500, "4bf92f35")


def test_a_cost_warning_is_logged(dataset, caplog):
    service = _service()
    service.order.job_api.job_definition_definition_id_run_post.return_value = (
        MagicMock(
            job_id="job_1",
            definition_id="jdf_copy",
            cost_warning=MagicMock(
                estimated_cost=12.0, available_balance=2.0, shortfall=10.0
            ),
        )
    )

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert any("estimated cost of 12.00" in r.getMessage() for r in caplog.records)


def test_the_job_manager_exposes_the_templates():
    assert isinstance(RapidataJobManager(_service()).template, RapidataTemplateManager)


@pytest.mark.parametrize("kind", METHODS)
def test_gifs_run_on_the_video_template(dataset, kind):
    service = _service()

    _call(RapidataTemplateManager(service), kind, [["mine/cat.gif", "flux/cat.gif"]])

    run = service.order.job_api.job_definition_definition_id_run_post
    assert (
        run.call_args.kwargs["definition_id"]
        == TEMPLATE_IDS["rapidata.ai"][f"{kind}/video"]
    )


def test_a_gif_paired_with_a_png_is_rejected():
    service = _service()

    with pytest.raises(ValueError, match="pairs an image with a video"):
        _call(RapidataTemplateManager(service), "preference", [["a.png", "b.gif"]])

    _assert_nothing_sent(service)


@pytest.mark.parametrize(
    ("pair", "media"),
    [
        (["renders/take#2.png", "out/seed;42.png"], "image"),
        (["frames/what?.mp4", "frames/why?.mp4"], "video"),
        (["https://cdn.example/a.png?sig=1", "https://cdn.example/b.png#top"], "image"),
        (["HTTPS://CDN.EXAMPLE/A.MP4?X=1", "b.mp4"], "video"),
    ],
)
def test_local_names_keep_their_hash_question_mark_and_semicolon(dataset, pair, media):
    service = _service()

    _call(RapidataTemplateManager(service), "preference", [pair])

    run = service.order.job_api.job_definition_definition_id_run_post
    assert (
        run.call_args.kwargs["definition_id"]
        == TEMPLATE_IDS["rapidata.ai"][f"preference/{media}"]
    )


def test_contexts_and_a_b_names_are_keyword_only():
    service = _service()
    manager = RapidataTemplateManager(service)

    with pytest.raises(TypeError):
        manager.run_preference("x", IMAGE_PAIRS, ["Flux", "MJ"])
    with pytest.raises(TypeError):
        manager.run_coherence("x", IMAGE_PAIRS, ["Flux", "MJ"])
    with pytest.raises(TypeError):
        manager.run_alignment("x", IMAGE_PAIRS, PROMPTS)

    _assert_nothing_sent(service)


@pytest.mark.parametrize(
    "failure",
    [
        httpx2.ConnectError("connection refused"),
        httpx2.ConnectTimeout("connect timed out"),
        httpx2.PoolTimeout("no free connection"),
    ],
)
def test_a_start_that_never_left_the_client_raises_as_is(monkeypatch, failure):
    api_client = RapidataApiClient(
        configuration=Configuration(host="https://api.rapidata.ai")
    )
    rest_client = api_client.rest_client
    rest_client.session = MagicMock()
    attempts: list[int] = []

    def send(*args, **kwargs):
        attempts.append(1)
        raise failure

    monkeypatch.setattr(rest_client, "_send_request", send)
    monkeypatch.setattr(rest.time, "sleep", lambda _: None)
    service = MagicMock()
    service.order.job_api = JobApi(api_client)

    with pytest.raises(ApiException) as raised:
        RapidataTemplateManager(service)._start(
            "jdf_1", "my-model vs flux-2", "dst_1", None, STARTED
        )

    assert not isinstance(raised.value, RapidataError)
    assert type(failure).__name__ in str(raised.value)
    assert len(attempts) == rest._TRANSIENT_RETRY_MAX_ATTEMPTS + 1


def test_a_newer_unfinished_revision_is_skipped_for_the_completed_one(dataset, capsys):
    service = _service()
    job_api = service.order.job_api
    job_api.job_definition_definition_id_revision_get.return_value = _revision(
        votes=5, question="Draft question?", state="Pending", number=2
    )
    job_api.job_definition_definition_id_revisions_get.return_value = MagicMock(
        items=[MagicMock(revision_number=1)]
    )
    job_api.job_definition_definition_id_revision_revision_number_get.return_value = (
        _revision()
    )

    _call(RapidataTemplateManager(service), "alignment", IMAGE_PAIRS)

    listed = job_api.job_definition_definition_id_revisions_get.call_args.kwargs
    assert (listed["sort"], listed["state"].eq) == (["-revision_number"], "Completed")
    job_api.job_definition_definition_id_revision_revision_number_get.assert_called_once_with(
        definition_id=TEMPLATE_IDS["rapidata.ai"]["alignment/image"], revision_number=1
    )
    assert _dataset_body(service)["contextShortening"] == {"question": QUESTION}
    assert capsys.readouterr().out.startswith("Job started: 2 pairs, 11 votes each\n")


def test_a_template_without_a_completed_revision_fails_before_the_upload():
    service = _service()
    job_api = service.order.job_api
    job_api.job_definition_definition_id_revision_get.return_value = _revision(
        state="Pending"
    )
    job_api.job_definition_definition_id_revisions_get.return_value = MagicMock(
        items=[]
    )

    with pytest.raises(RuntimeError, match="has no completed revision to run"):
        _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    service.dataset.dataset_api.dataset_post.assert_not_called()


def test_an_unreadable_vote_count_still_returns_the_job(dataset, monkeypatch, capsys):
    monkeypatch.setattr(
        "rapidata.rapidata_client.job._revision_body._get_responses",
        MagicMock(side_effect=KeyError("totalVotes")),
    )

    job = _call(RapidataTemplateManager(_service()), "preference", IMAGE_PAIRS)

    assert job.id == "job_1"
    assert capsys.readouterr().out.startswith("Job started: 2 pairs\n")


@pytest.mark.parametrize(
    ("setting", "warned"), [(True, True), (None, False), (False, False)]
)
def test_a_forced_content_check_warns_that_templates_ignore_it(
    dataset, monkeypatch, caplog, setting, warned
):
    monkeypatch.setattr(rapidata_config.upload, "checkForExplicitContent", setting)

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        _call(RapidataTemplateManager(_service()), "preference", IMAGE_PAIRS)

    assert warned == any(
        "checkForExplicitContent = True has no effect" in r.getMessage()
        for r in caplog.records
    )


def test_the_cost_warning_survives_a_failed_read_of_the_job(dataset, caplog):
    service = _service()
    service.order.job_api.job_definition_definition_id_run_post.return_value = (
        MagicMock(
            job_id="job_1",
            definition_id="jdf_copy",
            cost_warning=MagicMock(
                estimated_cost=12.0, available_balance=2.0, shortfall=10.0
            ),
        )
    )
    service.order.job_api.job_job_id_get.side_effect = RapidataError(
        status_code=500, message="boom"
    )

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        with pytest.raises(RapidataError, match="job_1"):
            _call(RapidataTemplateManager(service), "preference", IMAGE_PAIRS)

    assert any(
        "'my-model vs flux-2' has an estimated cost of 12.00" in r.getMessage()
        for r in caplog.records
    )
