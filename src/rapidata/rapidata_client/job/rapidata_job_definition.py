from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.exceptions.revision_conflict_error import (
    RevisionConflictError,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import tracer, logger, managed_print
from rapidata.rapidata_client.job.cost import (
    CostEstimate,
    DEFAULT_ESTIMATE_POLL_INTERVAL,
    DEFAULT_ESTIMATE_TIMEOUT,
    _poll_for_cost_estimate,
)
from rapidata.rapidata_client.job._revision_body import (
    _full_body,
    _get_answer_options,
    _get_instruction,
    _get_responses,
    _with_answer_options,
    _with_instruction,
    _with_responses,
)
import webbrowser
import urllib.parse
from colorama import Fore

if TYPE_CHECKING:
    from rapidata.api_client.models.get_job_revision_endpoint_output import (
        GetJobRevisionEndpointOutput,
    )
    from rapidata.rapidata_client.settings import RapidataSetting

RevisionState = Literal["Pending", "Completed", "Failed"]


@dataclass(frozen=True)
class RevisionInfo:
    """One revision of a job definition, as listed by ``RapidataJobDefinition.revisions()``."""

    revision: int
    base_revision: int | None
    state: RevisionState
    created_at: datetime


class RapidataJobDefinition:
    """A job definition, held at one revision.

    Reading a property returns the loaded revision's value, or your unsaved change.
    Assigning one stages the change locally; ``save()`` sends the whole revision
    in one request and moves the object to the new revision. ``audience.assign_job``
    runs the revision this object holds.
    """

    def __init__(
        self,
        id: str,
        name: str,
        openapi_service: OpenAPIService,
        revision: int | None = None,
    ):
        self.id = id
        self.name = name
        self._openapi_service = openapi_service
        self._job_details_page = (
            f"https://app.{self._openapi_service.environment}/definitions/{self.id}"
        )
        self.__estimated_cost: CostEstimate | None = None
        self._revision_number = revision
        self._loaded_snapshot: GetJobRevisionEndpointOutput | None = None
        self._pending: dict[str, Any] = {}

    @property
    def estimated_cost(self) -> CostEstimate:
        """An approximate estimate of what this job will cost to run to completion.

        This is an estimate, not the final bill - see :class:`CostEstimate`. The
        estimate is priced shortly after the definition is created; this call
        waits for it to become available.

        Raises:
            TimeoutError: If the estimate is still not available after a few minutes.
        """
        if self.__estimated_cost is None:
            with tracer.start_as_current_span("RapidataJobDefinition.estimated_cost"):
                model = _poll_for_cost_estimate(
                    lambda: self._openapi_service.order.job_api.job_definition_definition_id_cost_estimate_get(
                        self.id
                    ),
                    timeout=DEFAULT_ESTIMATE_TIMEOUT,
                    interval=DEFAULT_ESTIMATE_POLL_INTERVAL,
                )
                self.__estimated_cost = CostEstimate._from_model(model)
        return self.__estimated_cost

    def preview(self) -> RapidataJobDefinition:
        """Will open the browser where you can preview the job definition before giving it to an audience."""
        logger.info("Opening order details page in browser...")
        if not webbrowser.open(self._job_details_page):
            encoded_url = urllib.parse.quote(
                self._job_details_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )
        return self

    def delete(self) -> None:
        """Deletes the job definition and all its revisions."""
        with tracer.start_as_current_span("RapidataJobDefinition.delete"):
            logger.info("Deleting job definition '%s'", self)
            self._openapi_service.order.job_api.job_definition_definition_id_delete(
                self.id
            )
            logger.debug("Job definition '%s' has been deleted.", self)
            managed_print(f"Job definition '{self}' has been deleted.")

    @property
    def _snapshot(self) -> GetJobRevisionEndpointOutput:
        if self._loaded_snapshot is None:
            self._loaded_snapshot = self._fetch_revision(self._revision_number)
            self._revision_number = self._loaded_snapshot.revision_number
        return self._loaded_snapshot

    def _fetch_revision(self, revision: int | None) -> GetJobRevisionEndpointOutput:
        job_api = self._openapi_service.order.job_api
        if revision is None:
            return job_api.job_definition_definition_id_revision_get(
                definition_id=self.id
            )
        return job_api.job_definition_definition_id_revision_revision_number_get(
            definition_id=self.id, revision_number=revision
        )

    def _effective(self, key: str, loaded: Any) -> Any:
        return self._pending[key] if key in self._pending else loaded

    @property
    def revision(self) -> int:
        """The revision this object holds. ``assign_job`` runs exactly this revision."""
        if self._revision_number is None:
            return self._snapshot.revision_number
        return self._revision_number

    @property
    def base_revision(self) -> int | None:
        """The revision this one was edited from, or None if it was not recorded."""
        return self._snapshot.base_revision_number

    @property
    def state(self) -> RevisionState:
        """The current state of this revision, fetched from the server.

        A new revision is ``Pending`` until its preview has been built.
        """
        with tracer.start_as_current_span("RapidataJobDefinition.state"):
            self._loaded_snapshot = self._fetch_revision(self.revision)
            return self._loaded_snapshot.state.value  # type: ignore[return-value]

    @property
    def dataset_id(self) -> str:
        """The dataset of this revision, including an unsaved ``set_datapoints()``."""
        return self._effective("dataset_id", self._snapshot.dataset_id)

    @property
    def instruction(self) -> str | None:
        """The instruction shown to labelers. None when it is set per datapoint."""
        return self._effective("instruction", _get_instruction(self._snapshot.workflow))

    @instruction.setter
    def instruction(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("instruction must be a non-empty string")
        from rapidata.rapidata_client.workflow._base_workflow import (
            validate_instruction_length,
        )

        validate_instruction_length(value)
        _with_instruction(self._snapshot.workflow, value)
        self._pending["instruction"] = value

    @property
    def answer_options(self) -> list[str] | None:
        """The answer options of a classification job definition.

        None when the options are set per datapoint (the default for job definitions
        created with ``create_classification_job_definition``) or the job type has none.
        Setting it shows the same options for every datapoint.
        """
        options = self._effective(
            "answer_options", _get_answer_options(self._snapshot.workflow)
        )
        return list(options) if options is not None else None

    @answer_options.setter
    def answer_options(self, value: list[str]) -> None:
        if not isinstance(value, list) or not all(isinstance(o, str) for o in value):
            raise ValueError("answer_options must be a list of strings")
        if not 2 <= len(value) <= 8 or len(set(value)) != len(value):
            raise ValueError("answer_options needs between 2 and 8 unique options")
        _with_answer_options(self._snapshot.workflow, value)
        self._pending["answer_options"] = list(value)

    @property
    def responses_per_datapoint(self) -> int:
        """The maximum number of responses collected per datapoint."""
        return self._effective(
            "responses_per_datapoint", _get_responses(self._snapshot.referee)
        )

    @responses_per_datapoint.setter
    def responses_per_datapoint(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("responses_per_datapoint must be a positive integer")
        _with_responses(self._snapshot.referee, value)
        self._pending["responses_per_datapoint"] = value

    @property
    def settings(self) -> list[RapidataSetting]:
        """The settings of this revision, as ``CustomSetting`` objects.

        Assigning a list replaces every setting, at both the rapid and campaign level.
        """
        if "settings" in self._pending:
            return list(self._pending["settings"])
        from rapidata.rapidata_client.settings import CustomSetting

        settings: list[RapidataSetting] = []
        for flag in self._snapshot.feature_flags:
            settings.append(CustomSetting(key=flag.key, value=flag.value))
        for flag in self._snapshot.campaign_feature_flags:
            settings.append(
                CustomSetting(key=flag.key, value=flag.value, target="campaign")
            )
        return settings

    @settings.setter
    def settings(self, value: list[RapidataSetting]) -> None:
        from rapidata.rapidata_client.settings import RapidataSetting

        if not isinstance(value, list) or not all(
            isinstance(s, RapidataSetting) for s in value
        ):
            raise ValueError("settings must be a list of RapidataSetting")
        self._pending["settings"] = list(value)

    @property
    def validation_set_id(self) -> str | None:
        """The validation set pinned on this revision, or None for none."""
        return self._effective("validation_set_id", self._snapshot.validation_set_id)

    @validation_set_id.setter
    def validation_set_id(self, value: str | None) -> None:
        if value is not None and not isinstance(value, str):
            raise ValueError("validation_set_id must be a string or None")
        self._pending["validation_set_id"] = value

    @property
    def has_unsaved_changes(self) -> bool:
        """Whether a change is staged that ``save()`` has not sent yet."""
        return bool(self._pending)

    def set_datapoints(
        self,
        datapoints: list[str] | list[list[str]],
        data_type: Literal["text", "media"] = "media",
        contexts: list[str] | None = None,
        media_contexts: list[list[str]] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
        answer_options: list[str] | list[list[str]] | None = None,
    ) -> None:
        """Upload a new dataset now and stage it for the next ``save()``.

        Args:
            datapoints (list[str] | list[list[str]]): paths to the datapoints or strings for text datapoints.
            data_type (Literal["text", "media"]): The type of the datapoints.
            contexts (list[str], optional): One text context per datapoint. Defaults to None.
            media_contexts (list[list[str]], optional): Image URLs / paths shown alongside each datapoint, one inner list per datapoint. Defaults to None.
            sentences (list[str], optional): The sentences associated with each datapoint (used by select-words workflows). Defaults to None.
            private_metadata (list[dict[str, str]], optional): Key-value pairs attached to each datapoint that will not be shown to labelers. Defaults to None.
            answer_options (list[str] | list[list[str]], optional): Classification only, required when the
                options are set per datapoint: one list for every datapoint, or one list per datapoint.

        Raises:
            FailedUploadException: If any datapoint fails to upload. Nothing is staged.
        """
        with tracer.start_as_current_span("RapidataJobDefinition.set_datapoints"):
            from rapidata.rapidata_client.datapoints._datapoints_validator import (
                DatapointsValidator,
            )
            from rapidata.rapidata_client.datapoints._default_segments import (
                ANSWER_OPTIONS_SEGMENT_KEY,
                build_schema,
            )
            from rapidata.api_client.models.create_dataset_endpoint_input import (
                CreateDatasetEndpointInput,
            )
            from rapidata.rapidata_client.dataset._rapidata_dataset import (
                RapidataDataset,
            )
            from rapidata.rapidata_client.job._revision_body import (
                _required_segments,
            )

            workflow = self._snapshot.workflow
            if "answer_options" in self._pending:
                workflow = _with_answer_options(
                    workflow, self._pending["answer_options"]
                )
            required = _required_segments(workflow)

            per_datapoint_options: list[list[str]] | None = None
            if answer_options is not None:
                if all(isinstance(o, list) for o in answer_options):
                    per_datapoint_options = [list(o) for o in answer_options]  # type: ignore[arg-type]
                elif all(isinstance(o, str) for o in answer_options):
                    per_datapoint_options = [list(answer_options)] * len(datapoints)  # type: ignore[arg-type]
                else:
                    raise ValueError(
                        "answer_options must be either a list of strings or a list of lists of strings"
                    )
                required.add(ANSWER_OPTIONS_SEGMENT_KEY)
            elif ANSWER_OPTIONS_SEGMENT_KEY in required:
                raise ValueError(
                    "This job definition reads its answer options from each datapoint; "
                    "pass answer_options to set_datapoints()."
                )

            datapoints_list = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                sentences=sentences,
                private_metadata=private_metadata,
                data_type=data_type,
                answer_options=per_datapoint_options,
            )

            dataset = self._openapi_service.dataset.dataset_api.dataset_post(
                create_dataset_endpoint_input=CreateDatasetEndpointInput(
                    name=self.name + "_dataset",
                    schema=build_schema(required) if required else None,
                )
            )
            rapidata_dataset = RapidataDataset(
                dataset.dataset_id, self._openapi_service
            )

            _, failed_uploads = rapidata_dataset.add_datapoints(datapoints_list)
            if failed_uploads:
                raise FailedUploadException(
                    rapidata_dataset, failed_uploads, job_definition=self
                )

            self._pending["dataset_id"] = rapidata_dataset.id

    def save(self, require_latest: bool = False) -> int:
        """Create a new revision from this object and move the object to it.

        The request carries the complete revision: the one this object was loaded at,
        plus your staged changes. Changes saved by someone else since you loaded are
        not merged in; with ``require_latest=False`` (default) your revision becomes
        the latest anyway.

        Args:
            require_latest (bool): Only save if no other revision was saved since this
                object was loaded. Defaults to False.

        Returns:
            int: The new revision number.

        Raises:
            RevisionConflictError: With ``require_latest=True``, when another revision
                was saved in the meantime. Nothing is created and your changes stay staged.
        """
        with tracer.start_as_current_span("RapidataJobDefinition.save"):
            from rapidata.rapidata_client.api.rapidata_api_client import (
                suppress_rapidata_error_logging,
            )
            from rapidata.rapidata_client.exceptions.rapidata_error import (
                RapidataError,
            )

            snapshot = self._snapshot
            body = _full_body(snapshot, self._pending, require_latest)
            try:
                with suppress_rapidata_error_logging():
                    response = self._openapi_service.order.job_api.job_definition_definition_id_revision_post(
                        definition_id=self.id,
                        create_job_revision_endpoint_input=body,
                    )
            except RapidataError as e:
                if e.status_code == 409 and isinstance(e.details, dict):
                    raise RevisionConflictError(
                        job_definition_id=self.id,
                        base_revision=snapshot.revision_number,
                        latest_revision=e.details.get("latestRevisionNumber", -1),
                    ) from None
                logger.error("Error: %s", e)
                raise

            self._revision_number = response.revision_number
            self._loaded_snapshot = None
            self._pending = {}
            logger.info(
                "Saved job definition '%s' as revision %s (from %s)",
                self.id,
                response.revision_number,
                snapshot.revision_number,
            )
            return response.revision_number

    def reload(self, revision: int | None = None) -> RapidataJobDefinition:
        """Load a revision into this object, the latest one by default.

        Raises:
            RuntimeError: If there are unsaved changes; ``save()`` them or ``discard_changes()`` first.
        """
        if self._pending:
            raise RuntimeError(
                f"Job definition '{self.id}' has unsaved changes to "
                f"{', '.join(sorted(self._pending))}. Call save() or discard_changes() first."
            )
        with tracer.start_as_current_span("RapidataJobDefinition.reload"):
            self._loaded_snapshot = self._fetch_revision(revision)
            self._revision_number = self._loaded_snapshot.revision_number
            return self

    def discard_changes(self) -> RapidataJobDefinition:
        """Drop every staged change; the object keeps its loaded revision."""
        self._pending = {}
        return self

    def revisions(self) -> list[RevisionInfo]:
        """Every revision of this job definition, oldest first."""
        with tracer.start_as_current_span("RapidataJobDefinition.revisions"):
            job_api = self._openapi_service.order.job_api
            infos: list[RevisionInfo] = []
            page = 1
            while True:
                result = job_api.job_definition_definition_id_revisions_get(
                    definition_id=self.id,
                    page=page,
                    page_size=100,
                    sort=["revision_number"],
                )
                infos.extend(
                    RevisionInfo(
                        revision=item.revision_number,
                        base_revision=item.base_revision_number,
                        state=item.state.value,  # type: ignore[arg-type]
                        created_at=item.created_at,
                    )
                    for item in result.items
                )
                if len(result.items) < 100:
                    return infos
                page += 1

    def wait_until_ready(self, timeout: float = 300) -> RapidataJobDefinition:
        """Block until this revision's preview is built.

        Raises:
            TimeoutError: If it is still ``Pending`` after ``timeout`` seconds.
            RuntimeError: If the revision failed.
        """
        with tracer.start_as_current_span("RapidataJobDefinition.wait_until_ready"):
            deadline = time.monotonic() + timeout
            while (state := self.state) == "Pending":
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Revision {self.revision} of job definition '{self.id}' "
                        f"is still Pending after {timeout} seconds."
                    )
                time.sleep(2)
            if state == "Failed":
                raise RuntimeError(
                    f"Revision {self.revision} of job definition '{self.id}' failed."
                )
            return self

    def update_dataset(
        self,
        datapoints: list[str] | list[list[str]],
        data_type: Literal["text", "media"] = "media",
        contexts: list[str] | None = None,
        media_contexts: list[list[str]] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> RapidataJobDefinition:
        """Deprecated: use ``set_datapoints(...)`` followed by ``save()``."""
        warnings.warn(
            "update_dataset() is deprecated; call set_datapoints(...) and then save().",
            DeprecationWarning,
            stacklevel=2,
        )
        self.set_datapoints(
            datapoints=datapoints,
            data_type=data_type,
            contexts=contexts,
            media_contexts=media_contexts,
            sentences=sentences,
            private_metadata=private_metadata,
        )
        self.save()
        return self

    def __str__(self) -> str:
        revision = (
            f", revision={self._revision_number}"
            if self._revision_number is not None
            else ""
        )
        return f"JobDefinition(id={self.id}, name={self.name}{revision})"

    def __repr__(self) -> str:
        return self.__str__()
