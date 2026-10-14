from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.api_client.models.feature_flag import FeatureFlag
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob
    from rapidata.rapidata_client.experiment.experiment_config import (
        ExperimentConfig,
    )


@dataclass(frozen=True)
class Experiment:
    """A created experiment."""

    id: str
    name: str


class ExperimentManager:
    """Internal: creates experiments and launches jobs under them.

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
        description: str = "",
    ) -> Experiment:
        """Creates an experiment.

        It is live as soon as a campaign references it — meant to be paired with
        :py:meth:`run_experiment`, which attaches it to the job's campaign.
        """
        with tracer.start_as_current_span("ExperimentManager.create"):
            from rapidata.api_client.models.create_experiment_endpoint_input import (
                CreateExperimentEndpointInput,
            )
            from rapidata.api_client.models.create_experiment_endpoint_split import (
                CreateExperimentEndpointSplit,
            )

            api = self._openapi_service.campaign.experiment_api
            created = api.campaign_experiments_post(
                create_experiment_endpoint_input=CreateExperimentEndpointInput(
                    name=name,
                    description=description,
                    flags=flags or [],
                    split=CreateExperimentEndpointSplit(treatmentBps=treatment_bps),
                )
            )
            logger.info("Created experiment '%s'", created.id)
            return Experiment(id=created.id, name=created.name)

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
