from __future__ import annotations

from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase


class RapidataFilteredAudience(RapidataAudienceBase):
    """A filtered view on top of a :class:`RapidataAudience`.

    Created via :py:meth:`RapidataAudience.filter`. The filtered audience reuses the
    base audience's pool of qualified annotators — no new qualification or recruiting
    takes place — and so the surface here is intentionally narrow: you can run jobs
    on it, list its jobs, delete it, and pass its id to leaderboard / benchmark
    creation. Operations that mutate the qualification pool
    (``add_classification_example`` / ``add_compare_example`` / ``update_filters``)
    live only on :class:`RapidataAudience` and would not be meaningful here.

    Attributes:
        id (str): The unique identifier of the filtered audience. Prefixed ``fau_``.
        name (str): The name of the underlying dimension audience.
        filters (list[RapidataFilter]): The filter tree that defines this slice.
    """
