from __future__ import annotations

from typing import Sequence, TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


class ContextManager:
    """Shortens a datapoint's context for the specific question an annotator answers.

    A long, general context (e.g. a full scene description) is often far more
    detail than a single question needs. This manager tunes a context down to
    what is relevant for the question, which keeps it within the length the
    backend accepts and focuses the annotator. Results are cached server-side.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        logger.debug("ContextManager initialized")

    def shorten_context(self, context: str, question: str) -> str:
        """Shorten a single context for the given question.

        Args:
            context: The (potentially long) context to shorten.
            question: The question the context will be shown alongside. The
                context is tuned to what this question needs.

        Returns:
            The shortened context.
        """
        return self.shorten_contexts([(context, question)])[0]

    def shorten_contexts(self, pairs: Sequence[tuple[str, str]]) -> list[str]:
        """Shorten a batch of ``(context, question)`` pairs in one request.

        Args:
            pairs: The ``(context, question)`` pairs to shorten.

        Returns:
            The shortened contexts, in the same order as ``pairs``.
        """
        with tracer.start_as_current_span("ContextManager.shorten_contexts"):
            return self._openapi_service.context.shorten_contexts(pairs)
