from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RecruitingMetrics:
    """A snapshot of where a custom audience's annotators sit in the recruiting funnel.

    A custom (distilling) audience recruits its own pool of annotators: candidates start
    in distilling, and each one eventually graduates into the eligible pool, is dropped,
    or goes inactive. These counts let you tell a healthy pool from one that is still
    filling up or has stalled — e.g. a job collecting no responses while ``graduated`` is
    still 0 is waiting on recruiting, not stuck.

    The counts are mutually exclusive: each annotator is in exactly one bucket, so a
    graduated annotator who goes quiet moves out of ``graduated`` and into ``inactive``.

    Only custom audiences recruit, so this is empty (all zeros) for curated audiences.

    Attributes:
        graduated: Annotators who passed qualification and are eligible to work now.
        distilling: Annotators still going through qualification.
        dropped: Annotators removed from the pool (score too low, limits hit, etc.).
        inactive: Previously-graduated or distilling annotators who went quiet.
    """

    graduated: int
    distilling: int
    dropped: int
    inactive: int

    @classmethod
    def _from_users_per_state(
        cls, users_per_state: Mapping[str, int]
    ) -> RecruitingMetrics:
        # The backend keys these by the AudienceUserState name. Every drop reason is
        # prefixed "Dropped" and every inactivity state "Inactive", so bucketing by
        # prefix keeps us correct if the backend adds new reasons to either group.
        graduated = distilling = dropped = inactive = 0
        for state, count in users_per_state.items():
            if state.startswith("Inactive"):
                inactive += count
            elif state.startswith("Dropped"):
                dropped += count
            elif state == "Graduated":
                graduated += count
            elif state == "Distilling":
                distilling += count

        return cls(
            graduated=graduated,
            distilling=distilling,
            dropped=dropped,
            inactive=inactive,
        )
