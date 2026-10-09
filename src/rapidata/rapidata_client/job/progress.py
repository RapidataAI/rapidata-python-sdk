from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.rapidata_client.audience.recruiting import RecruitingMetrics


@dataclass(frozen=True)
class JobProgress:
    """A snapshot of how far along a job is.

    ``completion_percentage`` tracks the labeling itself, while ``recruiting`` (present
    only for custom audiences) tells you about the annotator pool behind it — together
    they let you tell normal labeling from a job that is waiting on recruiting or has
    stalled.

    Attributes:
        state: The job's current state, the same value returned by
            :py:meth:`RapidataJob.get_status`.
        completion_percentage: How much of the requested labeling is done, from 0 to 100.
        recruiting: The recruiting-funnel snapshot for the job's audience, or ``None``
            for curated audiences (which do not recruit their own pool).
    """

    state: str
    completion_percentage: float
    recruiting: RecruitingMetrics | None
