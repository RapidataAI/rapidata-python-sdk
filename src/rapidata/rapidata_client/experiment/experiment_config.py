from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.rapidata_client.job.rapidata_job_definition import (
        RapidataJobDefinition,
    )
    from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience


@dataclass(frozen=True)
class ExperimentConfig:
    """Ties a job definition and audience to the experiment they should run under."""

    job_definition: RapidataJobDefinition
    experiment_id: str
    audience: RapidataAudience
