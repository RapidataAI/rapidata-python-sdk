from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
from rapidata.rapidata_client.config import managed_print

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob

UNLISTED_AUDIENCE_PREFIX = "ula_"


class RapidataUnlistedAudience(RapidataAudienceBase):
    """An audience made of your own annotators, reachable only through its link.

    Rapidata's annotators never see an unlisted audience. Instead, you share
    :py:attr:`link` with the people you want to label your data; they open it in a
    browser, pick a running job and annotate without an account. Jobs run exactly as
    on any other audience (:py:meth:`assign_job`, :py:meth:`find_jobs`), with the same
    pricing. There are no filters, qualification examples or recruiting.

    Create one with :py:meth:`RapidataAudienceManager.create_unlisted_audience`.

    Attributes:
        id (str): The unique identifier of the audience. Prefixed ``ula_``.
        name (str): The name of the audience.
    """

    def __init__(self, id: str, name: str, openapi_service: OpenAPIService):
        super().__init__(id=id, name=name, filters=[], openapi_service=openapi_service)

    @property
    def link(self) -> str:
        """The page to share with your annotators: lists the audience's running jobs."""
        return f"https://app.{self._openapi_service.environment}/label/{self.id}"

    def get_job_link(self, job: RapidataJob | str) -> str:
        """The page that drops your annotators straight into one job of this audience.

        Args:
            job (RapidataJob | str): A job assigned to this audience, or its id.

        Returns:
            str: The link to share with your annotators.
        """
        job_id = job if isinstance(job, str) else job.id
        return f"{self.link}/job/{job_id}"

    def _warn_if_no_graduated_annotators(self, job: RapidataJob) -> None:
        managed_print(
            f"Only people you share a link with can annotate job '{job.name}'. "
            f"Share {self.get_job_link(job)} for this job, or {self.link} for every "
            f"running job of audience '{self._name}'."
        )

    def __str__(self) -> str:
        return f"RapidataUnlistedAudience(id={self.id}, name={self._name})"
