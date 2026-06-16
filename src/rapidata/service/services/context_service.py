from __future__ import annotations

from typing import Any, TYPE_CHECKING, Sequence, cast

if TYPE_CHECKING:
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


# TODO: Replace this hand-written wrapper with the generated OpenAPI client once
# `POST /datasets/shorten-context` ships in datasets-service and the contract is
# published. At that point this service should call the generated
# ``DatasetsApi`` method (and the request/response shapes below become typed
# models) instead of crafting the request by hand. The path is kept as a single
# constant so the regeneration is a one-line removal.
_SHORTEN_CONTEXT_PATH = "/datasets/shorten-context"


class ContextService:
    """Thin client for the datasets context-shortening endpoint.

    The endpoint takes a batch of ``(context, question)`` pairs and returns a
    shortened context per item, tuned to the question the annotator answers.
    Results are cached server-side, so re-sending the same pair is cheap.
    """

    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client

    def shorten_contexts(self, items: Sequence[tuple[str, str]]) -> list[str]:
        """Shorten each ``(context, question)`` pair.

        Returns the shortened contexts in the same order as ``items``.
        """
        if not items:
            return []

        url = f"{self._api_client.configuration.host}{_SHORTEN_CONTEXT_PATH}"
        body = {
            "items": [
                {"context": context, "question": question}
                for context, question in items
            ]
        }

        response_data = self._api_client.call_api(
            "POST",
            url,
            header_params={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=body,
        )
        response_data.read()

        # Reuse the generated deserializer so error responses are converted to
        # RapidataError and tracing headers are honoured, exactly like a
        # generated endpoint call. "object" yields a plain dict.
        result = cast(
            "dict[str, Any]",
            self._api_client.response_deserialize(
                response_data=response_data,
                response_types_map={
                    "200": "object",
                    "400": "object",
                    "401": None,
                    "403": None,
                },
            ).data
            or {},
        )

        returned = result.get("items", [])
        if len(returned) != len(items):
            raise ValueError(
                "shorten-context returned "
                f"{len(returned)} item(s) for {len(items)} request item(s)."
            )

        return [item["shortenedContext"] for item in returned]
