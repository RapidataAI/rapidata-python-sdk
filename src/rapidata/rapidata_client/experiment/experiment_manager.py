from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.api_client.models.experiment_user_enrollment import (
    ExperimentUserEnrollment,
)

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.api_client.models.feature_flag import FeatureFlag
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob
    from rapidata.rapidata_client.experiment.experiment_config import (
        ExperimentConfig,
    )


@dataclass(frozen=True)
class Experiment:
    """A created, activated experiment."""

    id: str
    name: str
    state: str


class ExperimentManager:
    """Internal: creates attached-scope experiments and launches jobs under them.

    Not part of the public SDK surface — Rapidata-internal, undocumented.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        logger.debug("ExperimentManager initialized")

    def create(
        self,
        *,
        name: str,
        treatment_bps: int = 5000,
        flags: list[FeatureFlag] | None = None,
        user_enrollment: ExperimentUserEnrollment = ExperimentUserEnrollment.STICKY,
        description: str = "",
    ) -> Experiment:
        """Creates and activates an attached-scope experiment.

        The experiment is created in the draft state and immediately activated, so
        it is already serving by the time this returns — meant to be paired with
        :py:meth:`run_experiment`, which attaches it to the job's campaign before
        that campaign can serve.
        """
        with tracer.start_as_current_span("ExperimentManager.create"):
            from rapidata.api_client.models.create_experiment_endpoint_input import (
                CreateExperimentEndpointInput,
            )
            from rapidata.api_client.models.create_experiment_endpoint_split import (
                CreateExperimentEndpointSplit,
            )
            from rapidata.api_client.models.change_experiment_state_endpoint_input import (
                ChangeExperimentStateEndpointInput,
            )
            from rapidata.api_client.models.change_experiment_state_endpoint_state_action import (
                ChangeExperimentStateEndpointStateAction,
            )
            from rapidata.api_client.models.experiment_scope import ExperimentScope

            api = self._openapi_service.campaign.experiment_api
            created = api.campaign_experiments_post(
                create_experiment_endpoint_input=CreateExperimentEndpointInput(
                    name=name,
                    description=description,
                    scope=ExperimentScope.ATTACHED,
                    flags=flags or [],
                    userEnrollment=user_enrollment,
                    split=CreateExperimentEndpointSplit(treatmentBps=treatment_bps),
                )
            )
            activated = api.campaign_experiments_experiment_id_state_post(
                created.id,
                ChangeExperimentStateEndpointInput(
                    action=ChangeExperimentStateEndpointStateAction.ACTIVATE
                ),
            )
            logger.info("Created and activated experiment '%s'", activated.id)
            return Experiment(id=activated.id, name=activated.name, state="active")

    def run_experiment(self, config: ExperimentConfig) -> RapidataJob:
        """Launches ``config.job_definition`` on ``config.audience`` under the experiment.

        Raises:
            ValueError: If ``config.experiment_id`` is empty.
        """
        with tracer.start_as_current_span("ExperimentManager.run_experiment"):
            if not config.experiment_id:
                raise ValueError("ExperimentConfig.experiment_id must not be empty")

            return config.audience._create_job(
                config.job_definition, experiment_id=config.experiment_id
            )
