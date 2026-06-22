from __future__ import annotations

from typing import Sequence, TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer, rapidata_config

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint

# Mirrors the backend's datapoint/group context validation
# (datasets-service CreateDatapointCommandValidator: `RuleFor(x => x.Context).MaximumLength(400)`).
# Keep in sync if the backend limit changes.
MAX_CONTEXT_LENGTH = 400


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

    def _enforce_context_length(
        self, datapoints: list[Datapoint], question: str | None
    ) -> None:
        """Check datapoint contexts against the backend's maximum length, in place.

        For every datapoint whose context exceeds :data:`MAX_CONTEXT_LENGTH`:

        - if ``rapidata_config.upload.autoShortenContext`` is set and a
          ``question`` is available, the context is shortened for that question
          (one batched request) and substituted;
        - otherwise a warning is logged explaining the backend would reject it.
        """
        over_limit = [
            (index, datapoint, datapoint.context)
            for index, datapoint in enumerate(datapoints)
            if datapoint.context is not None
            and len(datapoint.context) > MAX_CONTEXT_LENGTH
        ]
        if not over_limit:
            return

        auto_shorten = rapidata_config.upload.autoShortenContext

        if auto_shorten and not question:
            # Shortening needs the question to tune the context against; without
            # it we can't shorten, so fall back to warning instead of proceeding.
            logger.warning(
                "rapidata_config.upload.autoShortenContext is set but no "
                "question/instruction was available to shorten against; leaving "
                "%d over-long context(s) unchanged.",
                len(over_limit),
            )

        if auto_shorten and question:
            shortened = self.shorten_contexts(
                [(context, question) for _, _, context in over_limit]
            )
            for (index, datapoint, context), new_context in zip(over_limit, shortened):
                if not new_context:
                    logger.warning(
                        "Datapoint %d: shorten-context returned an empty result; "
                        "keeping the original context.",
                        index,
                    )
                    continue
                logger.info(
                    "Datapoint %d: shortened context from %d to %d characters.",
                    index,
                    len(context),
                    len(new_context),
                )
                datapoint.context = new_context
            return

        for index, _, context in over_limit:
            logger.warning(
                "Datapoint %d has a context of %d characters, which exceeds the "
                "maximum of %d and would be rejected by the backend. Shorten it, "
                "or set rapidata_config.upload.autoShortenContext = True to shorten "
                "it automatically.",
                index,
                len(context),
                MAX_CONTEXT_LENGTH,
            )
