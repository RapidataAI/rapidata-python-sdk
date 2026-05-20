from __future__ import annotations
import json
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.signals.rapidata_signal import RapidataSignal


class SignalsManager:
    """Manage recurring scheduled Rapidata signals."""

    def __init__(self, openapi_service: "OpenAPIService") -> None:
        self.__openapi_service = openapi_service

    def _base_url(self) -> str:
        return f"{self.__openapi_service.api_client.configuration.host}/signals"

    def _parse(self, response) -> dict:
        return json.loads(response.read().decode("utf-8"))

    def create(
        self,
        name: str,
        job_definition_id: str,
        audience_id: str,
        schedule: Literal["Daily", "Weekly", "Monthly"],
        is_public: bool = False,
        pinned_revision_number: int | None = None,
    ) -> "RapidataSignal":
        """Create a new signal.

        Args:
            name: Display name for the signal.
            job_definition_id: ID of the job definition to run on each cycle.
            audience_id: ID of the audience (dimensional or filtered) to target.
            schedule: How often the signal fires — 'Daily', 'Weekly', or 'Monthly'.
            is_public: Whether the signal and its results are publicly visible.
            pinned_revision_number: Pin to a specific job definition revision.
                Omit to always use the latest revision.

        Returns:
            RapidataSignal: The created signal instance.
        """
        from rapidata.rapidata_client.signals.rapidata_signal import RapidataSignal

        payload: dict = {
            "name": name,
            "jobDefinitionId": job_definition_id,
            "audienceId": audience_id,
            "schedule": schedule,
            "isPublic": is_public,
        }
        if pinned_revision_number is not None:
            payload["pinnedRevisionNumber"] = pinned_revision_number

        response = self.__openapi_service.api_client.call_api(
            "POST",
            self._base_url(),
            body=payload,
        )
        signal_id = self._parse(response)["id"]
        return self.get(signal_id)

    def get(self, signal_id: str) -> "RapidataSignal":
        """Retrieve a signal by ID."""
        from rapidata.rapidata_client.signals.rapidata_signal import RapidataSignal

        response = self.__openapi_service.api_client.call_api(
            "GET",
            f"{self._base_url()}/{signal_id}",
        )
        data = self._parse(response)
        return RapidataSignal(data, self.__openapi_service)

    def list(self) -> list["RapidataSignal"]:
        """List all signals accessible to the current user."""
        from rapidata.rapidata_client.signals.rapidata_signal import RapidataSignal

        response = self.__openapi_service.api_client.call_api(
            "GET",
            self._base_url(),
        )
        data = self._parse(response)
        return [RapidataSignal(item, self.__openapi_service) for item in data.get("items", [])]

    def __repr__(self) -> str:
        return "SignalsManager"
