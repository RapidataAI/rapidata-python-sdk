from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from rapidata.rapidata_client.config import (
    logger,
    managed_print,
    rapidata_config,
    tracer,
)
from rapidata.rapidata_client.context.context_manager import MAX_CONTEXT_LENGTH
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError

if TYPE_CHECKING:
    from rapidata.api_client.models.get_job_revision_endpoint_output import (
        GetJobRevisionEndpointOutput,
    )
    from rapidata.api_client.models.run_job_definition_endpoint_output import (
        RunJobDefinitionEndpointOutput,
    )
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob
    from rapidata.rapidata_client.job.rapidata_job_definition import (
        RapidataJobDefinition,
    )
    from rapidata.service.openapi_service import OpenAPIService

TemplateKind = Literal["alignment", "preference", "coherence"]
Media = Literal["image", "video"]

PROMPT_WARNING_LENGTH = 200
MAX_INDEXES_SHOWN = 5
# Above the load balancer's 120 s, so a slow /run ends in its 504 rather than a client timeout.
RUN_REQUEST_TIMEOUT = (15.0, 130.0)
NO_ANSWER_STATUS_CODES = {502, 503, 504}
NO_ANSWER = "No answer from Rapidata"
# The jobs API saves the job before it publishes the start, so a 500 can follow a saved job.
FAILED_START_STATUS_CODE = 500
FAILED_START = "Rapidata failed while starting the job"


class TemplateUploadException(FailedUploadException):
    """Some pairs failed to upload into the template run's dataset, so no job was started."""

    def __init__(
        self,
        dataset: RapidataDataset,
        failed_uploads: list[FailedUpload[Datapoint]],
        total: int,
        method: str,
    ):
        self._total = total
        self._method = method
        super().__init__(dataset, failed_uploads)

    def retry(self) -> RapidataJobDefinition:
        raise RuntimeError(
            f"A template run can't be retried: call client.job.template.{self._method}() "
            "again. It uploads into a new dataset."
        )

    def __str__(self) -> str:
        return (
            f"{len(self.detailed_failures)} of {self._total} pairs failed to upload into "
            f"dataset {self.dataset.id}, so no job was started. Fix them and call "
            f"client.job.template.{self._method}() again.\n\n{self._failures_message()}"
        )


class RapidataTemplateManager:
    """Run a Rapidata template on your own pairs in one call. 11 votes per pair."""

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def run_alignment(
        self,
        name: str,
        datapoints: list[list[str]],
        *,
        contexts: list[str],
        a_b_names: list[str] | None = None,
    ) -> RapidataJob:
        """Asks which image (or video) matches the description better.

        Args:
            name: The name of the job. Not shown to annotators.
            datapoints: Pairs of file paths or URLs, [[a, b], ...]. One call is all images
                or all videos.
            contexts: One prompt per pair. Warns above 200 characters; above 400 they
                are shortened to what the question needs.
            a_b_names: Names for the first and second file of every pair, as in
                create_compare_job_definition. The results show them instead of "A" and "B".
        """
        with tracer.start_as_current_span("TemplateManager.run_alignment"):
            return self._run("alignment", name, datapoints, contexts, a_b_names)

    def run_preference(
        self,
        name: str,
        datapoints: list[list[str]],
        *,
        a_b_names: list[str] | None = None,
    ) -> RapidataJob:
        """Asks which image (or video) annotators prefer. Arguments as run_alignment."""
        with tracer.start_as_current_span("TemplateManager.run_preference"):
            return self._run("preference", name, datapoints, None, a_b_names)

    def run_coherence(
        self,
        name: str,
        datapoints: list[list[str]],
        *,
        a_b_names: list[str] | None = None,
    ) -> RapidataJob:
        """Asks which image (or video) is more likely AI-generated. The winner is the
        side that looks more AI-generated. Arguments as run_alignment."""
        with tracer.start_as_current_span("TemplateManager.run_coherence"):
            return self._run("coherence", name, datapoints, None, a_b_names)

    def _run(
        self,
        kind: TemplateKind,
        name: str,
        datapoints: list[list[str]],
        contexts: list[str] | None,
        a_b_names: list[str] | None,
    ) -> RapidataJob:
        from rapidata.rapidata_client.audience._audience_base import (
            RapidataAudienceBase,
        )
        from rapidata.rapidata_client.job._revision_body import _get_instruction
        from rapidata.rapidata_client.job._template_ids import template_id

        started = datetime.now(timezone.utc)
        _check_name(name)
        _check_a_b_names(a_b_names)
        media = _media_of_call(datapoints)
        prompts = (
            _check_contexts(contexts, len(datapoints)) if kind == "alignment" else None
        )
        if prompts is not None:
            _warn_about_long_prompts(prompts)
        _warn_if_content_check_is_forced()

        definition_id = template_id(
            self._openapi_service.environment, f"{kind}/{media}"
        )
        revision = self._read_template(definition_id)
        votes = _votes(revision)
        question = None
        if prompts is not None:
            question = _get_instruction(revision.workflow)
            if not question:
                raise RuntimeError(
                    f"Template {definition_id} has no question to shorten prompts against."
                )

        dataset = self._upload(f"run_{kind}", name, datapoints, prompts, question)
        response = self._start(definition_id, name, dataset.id, a_b_names, started)
        RapidataAudienceBase._warn_if_cost_exceeds_balance(name, response.cost_warning)

        job = self._load_job(response.job_id)
        managed_print(
            f"Job started: {_pairs(len(datapoints))}{votes}\n{job.job_details_page}"
        )
        return job

    def _read_template(self, definition_id: str) -> GetJobRevisionEndpointOutput:
        from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
            AudienceAudienceIdJobsGetJobIdParameter,
        )
        from rapidata.api_client.models.job_definition_revision_state import (
            JobDefinitionRevisionState,
        )

        job_api = self._openapi_service.order.job_api
        latest = job_api.job_definition_definition_id_revision_get(
            definition_id=definition_id
        )
        if latest.state == JobDefinitionRevisionState.COMPLETED:
            return latest

        # /run copies the latest completed revision, not a newer pending or failed one.
        completed = job_api.job_definition_definition_id_revisions_get(
            definition_id=definition_id,
            page_size=1,
            sort=["-revision_number"],
            state=AudienceAudienceIdJobsGetJobIdParameter(
                eq=JobDefinitionRevisionState.COMPLETED.value
            ),
        ).items
        if not completed:
            raise RuntimeError(
                f"Template {definition_id} has no completed revision to run."
            )
        return job_api.job_definition_definition_id_revision_revision_number_get(
            definition_id=definition_id, revision_number=completed[0].revision_number
        )

    def _upload(
        self,
        method: str,
        name: str,
        datapoints: list[list[str]],
        contexts: list[str] | None,
        question: str | None,
    ) -> RapidataDataset:
        from rapidata.api_client.models.create_dataset_endpoint_context_shortening import (
            CreateDatasetEndpointContextShortening,
        )
        from rapidata.api_client.models.create_dataset_endpoint_input import (
            CreateDatasetEndpointInput,
        )
        from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
        from rapidata.rapidata_client.datapoints._datapoints_validator import (
            DatapointsValidator,
        )

        body = (
            CreateDatasetEndpointInput(name=name)
            if question is None
            else CreateDatasetEndpointInput(
                name=name,
                contextShortening=CreateDatasetEndpointContextShortening(
                    question=question
                ),
            )
        )
        created = self._openapi_service.dataset.dataset_api.dataset_post(
            create_dataset_endpoint_input=body
        )
        dataset = RapidataDataset(created.dataset_id, self._openapi_service)

        points = DatapointsValidator.map_datapoints(
            datapoints=[list(pair) for pair in datapoints],
            contexts=contexts,
            multi_asset=True,
        )
        with tracer.start_as_current_span("add_datapoints"):
            _, failed = dataset.add_datapoints(points)
        if failed:
            raise TemplateUploadException(dataset, failed, len(points), method)
        return dataset

    def _start(
        self,
        definition_id: str,
        name: str,
        dataset_id: str,
        a_b_names: list[str] | None,
        started: datetime,
    ) -> RunJobDefinitionEndpointOutput:
        from httpx2 import ConnectError, ConnectTimeout, PoolTimeout

        from rapidata.api_client.exceptions import ApiException
        from rapidata.api_client.models.run_job_definition_endpoint_input import (
            RunJobDefinitionEndpointInput,
        )
        from rapidata.api_client.rest import without_unsafe_retries
        from rapidata.rapidata_client.api.rapidata_api_client import (
            suppress_rapidata_error_logging,
        )

        body = (
            RunJobDefinitionEndpointInput(name=name, datasetId=dataset_id)
            if a_b_names is None
            else RunJobDefinitionEndpointInput(
                name=name,
                datasetId=dataset_id,
                aName=a_b_names[0],
                bName=a_b_names[1],
            )
        )
        try:
            with without_unsafe_retries(), suppress_rapidata_error_logging():
                return self._openapi_service.order.job_api.job_definition_definition_id_run_post(
                    definition_id=definition_id,
                    run_job_definition_endpoint_input=body,
                    _request_timeout=RUN_REQUEST_TIMEOUT,
                )
        except RapidataError as e:
            if e.status_code == FAILED_START_STATUS_CODE:
                lead = FAILED_START
            elif e.status_code in NO_ANSWER_STATUS_CODES:
                lead = NO_ANSWER
            else:
                raise
            raise RapidataError(
                status_code=e.status_code,
                message=_may_have_started(lead, name, started),
                original_exception=e,
                trace_id=e.trace_id,
            ) from e
        except ApiException as e:
            # These fail before the request leaves the client, so calling again is safe.
            if isinstance(e.__context__, (ConnectError, ConnectTimeout, PoolTimeout)):
                raise
            raise RapidataError(
                message=_may_have_started(NO_ANSWER, name, started),
                original_exception=e,
            ) from e

    def _load_job(self, job_id: str) -> RapidataJob:
        from rapidata.rapidata_client.job.rapidata_job import RapidataJob

        try:
            output = self._openapi_service.order.job_api.job_job_id_get(job_id=job_id)
        except Exception as e:
            raise RapidataError(
                status_code=getattr(e, "status_code", None),
                message=(
                    f"Job {job_id} started, but reading it failed. "
                    f"Get it with client.job.get_job_by_id('{job_id}')."
                ),
                original_exception=e,
                trace_id=getattr(e, "trace_id", None),
            ) from e
        return RapidataJob(
            job_id=output.job_id,
            name=output.name,
            audience_id=output.audience_id,
            created_at=output.created_at,
            definition_id=output.definition_id,
            openapi_service=self._openapi_service,
            pipeline_id=output.pipeline_id,
        )

    def __str__(self) -> str:
        return "TemplateManager"

    def __repr__(self) -> str:
        return self.__str__()


def _may_have_started(lead: str, name: str, started: datetime) -> str:
    return (
        f"{lead}, so a job may have started. Look for it with "
        "client.job.find_jobs(name) before calling again. This call's job would be "
        f"named exactly {name!r} and created after {started:%Y-%m-%d %H:%M:%S} UTC."
    )


def _check_name(name: str) -> None:
    if not isinstance(name, str) or not name.strip() or len(name) > 256:
        raise ValueError("Name must be 1 to 256 characters.")


def _check_a_b_names(a_b_names: list[str] | None) -> None:
    if a_b_names is None:
        return
    if (
        not isinstance(a_b_names, (list, tuple))
        or len(a_b_names) != 2
        or not all(isinstance(side, str) and side.strip() for side in a_b_names)
        or a_b_names[0] == a_b_names[1]
    ):
        raise ValueError(
            "a_b_names needs 2 different names, one per side, or None for A and B."
        )


def _media_of_call(datapoints: list[list[str]]) -> Media:
    if not isinstance(datapoints, list) or not datapoints:
        raise ValueError(
            "datapoints must be a list of at least one pair, such as [[a, b]]."
        )

    images: list[int] = []
    videos: list[int] = []
    for index, pair in enumerate(datapoints):
        if (
            not isinstance(pair, (list, tuple))
            or len(pair) != 2
            or not all(isinstance(file, str) and file for file in pair)
            or pair[0] == pair[1]
        ):
            raise ValueError(
                f"datapoints[{index}] must be a pair of 2 different files, got {pair!r}."
            )
        media = {_media_of_file(file, index) for file in pair}
        if len(media) != 1:
            raise ValueError(
                f"datapoints[{index}] pairs an image with a video. Both files of a pair "
                "must be images, or both videos."
            )
        (images if media.pop() == "image" else videos).append(index)

    if images and videos:
        raise ValueError(_mixed_media_message(images, videos))
    return "image" if images else "video"


def _media_of_file(file: str, index: int) -> Media:
    from rapidata.api_client.models.asset_type import AssetType
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.rapidata_client.datapoints.assets.constants import (
        ALLOWED_IMAGE_EXTENSIONS,
        ALLOWED_VIDEO_EXTENSIONS,
    )

    asset_type = Datapoint(asset=file, data_type="media").get_asset_type()
    if asset_type == AssetType.IMAGE:
        return "image"
    if asset_type == AssetType.VIDEO:
        return "video"
    raise ValueError(
        f"datapoints[{index}]: {file!r} is neither an image "
        f"({', '.join(ALLOWED_IMAGE_EXTENSIONS)}) nor a video "
        f"({', '.join(ALLOWED_VIDEO_EXTENSIONS)}), judging by its extension."
    )


def _mixed_media_message(images: list[int], videos: list[int]) -> str:
    smaller = videos if len(videos) <= len(images) else images
    shown = smaller[:MAX_INDEXES_SHOWN]
    indexes = ", ".join(
        [f"datapoints[{shown[0]}]"] + [f"[{index}]" for index in shown[1:]]
    )
    if len(smaller) > MAX_INDEXES_SHOWN:
        indexes += ", …"

    image_part = (
        f"{len(images)} datapoints are images"
        if len(images) != 1
        else "1 datapoint is an image"
    )
    video_part = f"{len(videos)} are videos" if len(videos) != 1 else "1 is a video"
    if smaller is images:
        image_part += f" ({indexes})"
    else:
        video_part += f" ({indexes})"
    return (
        "Images and videos can't be mixed in one call (the question depends on the "
        f"media type): {image_part}, {video_part}. Send them as two calls, one with "
        "only images and one with only videos."
    )


def _check_contexts(contexts: list[str] | None, pair_count: int) -> list[str]:
    if not isinstance(contexts, list):
        raise ValueError("contexts must be a list with one prompt per pair.")
    if len(contexts) != pair_count:
        raise ValueError(
            f"contexts has {len(contexts)} prompts for {pair_count} pairs: "
            "send one prompt per pair."
        )
    for index, context in enumerate(contexts):
        if not isinstance(context, str) or not context.strip():
            raise ValueError(f"contexts[{index}] is empty: every pair needs a prompt.")
    return contexts


def _warn_about_long_prompts(contexts: list[str]) -> None:
    total = len(contexts)
    over_warning = sum(1 for c in contexts if len(c) > PROMPT_WARNING_LENGTH)
    over_limit = sum(1 for c in contexts if len(c) > MAX_CONTEXT_LENGTH)
    if over_warning:
        logger.warning(
            "%d of %d prompts %s longer than %d characters. Keep prompts under %d for "
            "better results: annotators read them on a phone.",
            over_warning,
            total,
            "is" if over_warning == 1 else "are",
            PROMPT_WARNING_LENGTH,
            PROMPT_WARNING_LENGTH,
        )
    if over_limit:
        logger.warning(
            "%d of %d prompts %s longer than %d characters. Rapidata shortens %s to "
            "what the question needs.",
            over_limit,
            total,
            "is" if over_limit == 1 else "are",
            MAX_CONTEXT_LENGTH,
            "it" if over_limit == 1 else "them",
        )


def _warn_if_content_check_is_forced() -> None:
    if rapidata_config.upload.checkForExplicitContent is True:
        logger.warning(
            "rapidata_config.upload.checkForExplicitContent = True has no effect on "
            "template runs: POST /job/definition/{definitionId}/run checks content "
            "unless your organization may skip the check."
        )


def _pairs(count: int) -> str:
    return f"{count} pair" if count == 1 else f"{count} pairs"


def _votes(revision: GetJobRevisionEndpointOutput) -> str:
    from rapidata.rapidata_client.job._revision_body import _get_responses

    try:
        return f", {_get_responses(revision.referee)} votes each"
    except (AttributeError, KeyError, TypeError, ValueError):
        return ""
