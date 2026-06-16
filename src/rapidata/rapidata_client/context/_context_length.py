from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger

if TYPE_CHECKING:
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.rapidata_client.context.context_manager import ContextManager

# Mirrors the backend's datapoint/group context validation
# (datasets-service CreateDatapointCommandValidator: `RuleFor(x => x.Context).MaximumLength(400)`).
# Keep in sync if the backend limit changes.
MAX_CONTEXT_LENGTH = 400


def enforce_context_length(
    datapoints: list[Datapoint],
    question: str | None,
    auto_shorten: bool,
    context_manager: ContextManager,
) -> None:
    """Check datapoint contexts against the backend's maximum length, in place.

    For every datapoint whose context exceeds :data:`MAX_CONTEXT_LENGTH`:

    - if ``auto_shorten`` is True and a ``question`` is available, the context
      is shortened for that question (one batched request) and substituted;
    - otherwise a warning is logged explaining the backend would reject it.
    """
    over_limit = [
        (index, datapoint)
        for index, datapoint in enumerate(datapoints)
        if datapoint.context is not None and len(datapoint.context) > MAX_CONTEXT_LENGTH
    ]
    if not over_limit:
        return

    if auto_shorten and not question:
        # auto_shorten needs the question to tune the context; without it we
        # can't shorten, so fall back to warning rather than silently proceed.
        logger.warning(
            "auto_shorten=True but no question/instruction was available to shorten "
            "the context against; leaving %d over-long context(s) unchanged.",
            len(over_limit),
        )

    if auto_shorten and question:
        pairs = [
            (datapoint.context, question)
            for _, datapoint in over_limit
            if datapoint.context is not None
        ]
        shortened = context_manager.shorten_contexts(pairs)
        for (index, datapoint), new_context in zip(over_limit, shortened):
            if not new_context:
                logger.warning(
                    "Datapoint %d: shorten-context returned an empty result; "
                    "keeping the original context.",
                    index,
                )
                continue
            assert datapoint.context is not None
            logger.info(
                "Datapoint %d: shortened context from %d to %d characters.",
                index,
                len(datapoint.context),
                len(new_context),
            )
            datapoint.context = new_context
        return

    for index, datapoint in over_limit:
        assert datapoint.context is not None
        logger.warning(
            "Datapoint %d has a context of %d characters, which exceeds the maximum "
            "of %d and would be rejected by the backend. Shorten it, or pass "
            "auto_shorten=True to shorten it automatically.",
            index,
            len(datapoint.context),
            MAX_CONTEXT_LENGTH,
        )
