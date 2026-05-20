from __future__ import annotations
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


class RapidataSignal:
    """Represents a Rapidata signal instance."""

    def __init__(self, data: dict, openapi_service: "OpenAPIService") -> None:
        self._data = data
        self.__openapi_service = openapi_service

    def _url(self, path: str = "") -> str:
        host = self.__openapi_service.api_client.configuration.host
        return f"{host}/signals/{self.id}{path}"

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def job_definition_id(self) -> str:
        return self._data["jobDefinitionId"]

    @property
    def pinned_revision_number(self) -> int | None:
        return self._data.get("pinnedRevisionNumber")

    @property
    def audience_id(self) -> str:
        return self._data["audienceId"]

    @property
    def schedule(self) -> str:
        return self._data["schedule"]

    @property
    def next_run_at(self) -> str:
        return self._data["nextRunAt"]

    @property
    def is_public(self) -> bool:
        return self._data["isPublic"]

    @property
    def active(self) -> bool:
        return self._data["active"]

    @property
    def owner_mail(self) -> str:
        return self._data["ownerMail"]

    @property
    def created_at(self) -> str:
        return self._data["createdAt"]

    def trigger_run(self) -> dict:
        """Manually trigger a run outside the normal schedule.

        Returns:
            dict with keys: runId, jobId, pipelineId
        """
        response = self.__openapi_service.api_client.call_api(
            "POST",
            self._url("/runs"),
            body={},
        )
        return json.loads(response.read().decode("utf-8"))

    def get_runs(self) -> list[dict]:
        """Get all runs for this signal, newest first."""
        response = self.__openapi_service.api_client.call_api(
            "GET",
            self._url("/runs"),
        )
        data = json.loads(response.read().decode("utf-8"))
        return data.get("runs", [])

    def pause(self) -> "RapidataSignal":
        """Pause this signal (stops scheduled execution)."""
        self.__openapi_service.api_client.call_api(
            "POST",
            self._url("/active"),
            body={"active": False},
        )
        self._data["active"] = False
        return self

    def resume(self) -> "RapidataSignal":
        """Resume a paused signal."""
        self.__openapi_service.api_client.call_api(
            "POST",
            self._url("/active"),
            body={"active": True},
        )
        self._data["active"] = True
        return self

    def delete(self) -> None:
        """Permanently delete this signal."""
        self.__openapi_service.api_client.call_api(
            "DELETE",
            self._url(),
        )

    def __repr__(self) -> str:
        status = "active" if self.active else "paused"
        return f"RapidataSignal(id={self.id!r}, name={self.name!r}, schedule={self.schedule!r}, status={status!r})"
