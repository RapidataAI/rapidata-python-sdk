from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.translation_api import TranslationApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class TranslationService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._translation_api: TranslationApi | None = None

    @property
    def translation_api(self) -> TranslationApi:
        if self._translation_api is None:
            from rapidata.api_client.api.translation_api import TranslationApi
            self._translation_api = TranslationApi(self._api_client)
        return self._translation_api
