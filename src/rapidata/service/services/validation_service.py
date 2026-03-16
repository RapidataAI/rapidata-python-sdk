from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.validation_set_api import ValidationSetApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class ValidationService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._validation_api: ValidationSetApi | None = None

    @property
    def validation_api(self) -> ValidationSetApi:
        if self._validation_api is None:
            from rapidata.api_client.api.validation_set_api import ValidationSetApi
            self._validation_api = ValidationSetApi(self._api_client)
        return self._validation_api
