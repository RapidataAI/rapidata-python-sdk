from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence, TYPE_CHECKING

from opentelemetry import context as otel_context
from tqdm.auto import tqdm

from rapidata.rapidata_client.config import logger, tracer, rapidata_config

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint

# Mirrors the backend's datapoint/group context validation
# (datasets-service CreateDatapointCommandValidator: `RuleFor(x => x.Context).MaximumLength(400)`).
# Keep in sync if the backend limit changes.
MAX_CONTEXT_LENGTH = 400

# The endpoint shortens the pairs of one request concurrently, but the request
# only returns once its slowest pair is done. Splitting a large call into several
# requests lets them overlap, reports progress as they land, and keeps a batch
# short enough that one model call cannot stall the whole set.
SHORTEN_BATCH_SIZE = 10


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
        """Shorten a batch of ``(context, question)`` pairs.

        The pairs are sent in concurrent batched requests, with a progress bar
        while they run (suppressed by ``rapidata_config.logging.silent_mode``).

        Args:
            pairs: The ``(context, question)`` pairs to shorten.

        Returns:
            The shortened contexts, in the same order as ``pairs``.
        """
        if not pairs:
            return []

        with tracer.start_as_current_span("ContextManager.shorten_contexts"):
            if len(pairs) <= SHORTEN_BATCH_SIZE:
                return self._shorten_batch(pairs)

            batches = [
                pairs[start : start + SHORTEN_BATCH_SIZE]
                for start in range(0, len(pairs), SHORTEN_BATCH_SIZE)
            ]
            results: list[list[str]] = [[] for _ in batches]
            current_context = otel_context.get_current()

            def shorten_batch(index: int) -> None:
                token = otel_context.attach(current_context)
                try:
                    results[index] = self._shorten_batch(batches[index])
                finally:
                    otel_context.detach(token)

            with ThreadPoolExecutor(
                max_workers=rapidata_config.upload.maxWorkers
            ) as executor:
                futures = {
                    executor.submit(shorten_batch, index): index
                    for index in range(len(batches))
                }
                with tqdm(
                    total=len(pairs),
                    desc="Shortening contexts",
                    disable=rapidata_config.logging.silent_mode,
                ) as progress:
                    for future in as_completed(futures):
                        future.result()
                        progress.update(len(batches[futures[future]]))

            return [context for batch in results for context in batch]

    def _shorten_batch(self, pairs: Sequence[tuple[str, str]]) -> list[str]:
        """Shorten one batch of ``(context, question)`` pairs in a single request."""
        from rapidata.api_client.models.shorten_context_endpoint_input import (
            ShortenContextEndpointInput,
        )
        from rapidata.api_client.models.shorten_context_endpoint_input_item import (
            ShortenContextEndpointInputItem,
        )

        output = self._openapi_service.dataset.context_shortening_api.datasets_shorten_context_post(
            shorten_context_endpoint_input=ShortenContextEndpointInput(
                items=[
                    ShortenContextEndpointInputItem(context=context, question=question)
                    for context, question in pairs
                ]
            )
        )
        return [item.shortened_context for item in output.items]

    def _apply_context_shortening(
        self, datapoints: list[Datapoint], question: str
    ) -> None:
        """Shorten datapoint contexts for ``question``, in place.

        A context longer than :data:`MAX_CONTEXT_LENGTH` is **always** shortened
        — the backend would reject it otherwise — and a warning reports it, since
        the annotators then see text the caller did not write.

        With ``rapidata_config.upload.contextShortening`` enabled, every context
        is shortened, not only the over-long ones: a context tuned to the question
        focuses the annotator even when it already fits.
        """
        shorten_all = rapidata_config.upload.contextShortening

        candidates = [
            (index, datapoint, datapoint.context)
            for index, datapoint in enumerate(datapoints)
            if datapoint.context is not None
            and (shorten_all or len(datapoint.context) > MAX_CONTEXT_LENGTH)
        ]
        if not candidates:
            return

        over_limit_count = sum(
            1 for _, _, context in candidates if len(context) > MAX_CONTEXT_LENGTH
        )
        if over_limit_count:
            logger.warning(
                "%d context(s) exceed the maximum of %d characters and are being "
                "shortened for the instruction so the backend accepts them.",
                over_limit_count,
                MAX_CONTEXT_LENGTH,
            )

        shortened = self.shorten_contexts(
            [(context, question) for _, _, context in candidates]
        )
        for (index, datapoint, context), new_context in zip(candidates, shortened):
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
