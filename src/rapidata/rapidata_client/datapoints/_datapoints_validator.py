from itertools import zip_longest
from typing import Literal, cast, Iterable
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.config import logger


def _normalize_media_contexts(
    media_contexts: list[list[str]] | list[str] | None,
) -> list[list[str]] | None:
    """Normalize media_contexts to ``list[list[str]] | None``.

    Accepts the legacy ``list[str]`` shape (one media context per datapoint)
    by wrapping each string in a single-element list, after emitting a
    deprecation warning. This way the rest of the pipeline only ever has
    to deal with ``list[list[str]]``.
    """
    if media_contexts is None:
        return None

    if not isinstance(media_contexts, list):
        raise ValueError(
            "media_contexts must be a list of lists of strings or None, "
            f"got {type(media_contexts).__name__}."
        )

    has_str = any(isinstance(mc, str) for mc in media_contexts)
    has_list = any(isinstance(mc, list) for mc in media_contexts)
    if has_str and has_list:
        raise ValueError(
            "media_contexts must be a list of lists of strings, not a mix of strings and lists."
        )

    if has_str:
        logger.warning(
            "Passing a flat list of strings for media_contexts is deprecated; "
            "pass a list of lists of strings instead. Each string has been "
            "wrapped in a single-element list."
        )
        normalized: list[list[str]] = []
        for mc in media_contexts:
            if not isinstance(mc, str):
                raise ValueError(
                    "media_contexts must be a list of lists of strings, "
                    f"got element of type {type(mc).__name__}."
                )
            if mc == "":
                raise ValueError(
                    "media_contexts entries cannot be empty strings."
                )
            normalized.append([mc])
        return normalized

    # list[list[str]] case
    for mc in media_contexts:
        if not isinstance(mc, list):
            raise ValueError(
                "media_contexts must be a list of lists of strings, "
                f"got element of type {type(mc).__name__}."
            )
        if len(mc) == 0:
            raise ValueError(
                "Each inner media_contexts list must contain at least one string. "
                "Use None for the whole field if not needed."
            )
        if any(not isinstance(item, str) or item == "" for item in mc):
            raise ValueError(
                "Every entry in a media_contexts inner list must be a non-empty string."
            )
    return cast("list[list[str]]", media_contexts)


class DatapointsValidator:
    @staticmethod
    def validate_datapoints(
        datapoints: list[str] | list[list[str]],
        contexts: list[str] | None = None,
        media_contexts: list[list[str]] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
        groups: list[str] | None = None,
        multi_asset: bool = False,
    ) -> None:
        if multi_asset and any(isinstance(datapoint, str) for datapoint in datapoints):
            raise ValueError("Datapoints must be a list of lists of strings")
        if not multi_asset and any(
            isinstance(datapoint, list) for datapoint in datapoints
        ):
            raise ValueError("Datapoints must be a list of strings")
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("Number of contexts must match number of datapoints")
        if media_contexts is not None and len(media_contexts) != len(datapoints):
            raise ValueError(
                "Number of media contexts must match number of datapoints"
            )
        if sentences and len(sentences) != len(datapoints):
            raise ValueError("Number of sentences must match number of datapoints")
        if private_metadata and len(private_metadata) != len(datapoints):
            raise ValueError(
                "Number of private metadata entries must match number of datapoints"
            )
        if groups and (
            len(groups) != len(datapoints) or len(groups) != len(set(groups))
        ):
            raise ValueError(
                "Number of groups must match number of datapoints and must be unique."
            )

    @staticmethod
    def map_datapoints(
        datapoints: list[str] | list[list[str]],
        contexts: list[str] | None = None,
        media_contexts: list[list[str]] | list[str] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
        groups: list[str] | None = None,
        data_type: Literal["text", "media"] = "media",
        multi_asset: bool = False,
    ) -> list[Datapoint]:
        # Coerce legacy list[str] form once, here, so every consumer below
        # only has to think about list[list[str]].
        normalized_media_contexts = _normalize_media_contexts(media_contexts)
        DatapointsValidator.validate_datapoints(
            datapoints=datapoints,
            contexts=contexts,
            media_contexts=normalized_media_contexts,
            sentences=sentences,
            private_metadata=private_metadata,
            groups=groups,
            multi_asset=multi_asset,
        )
        return [
            Datapoint(
                asset=asset,
                data_type=data_type,
                context=context,
                media_context=media_context,
                sentence=sentence,
                private_metadata=private_tag,
                group=group,
            )
            for asset, context, media_context, sentence, private_tag, group in cast(
                "Iterable[tuple[str | list[str], str | None, list[str] | None, str | None, dict[str, str] | None, str | None]]",  # because iterator only supports 5 arguments with specific type casting
                zip_longest(
                    datapoints,
                    contexts or [],
                    normalized_media_contexts or [],
                    sentences or [],
                    private_metadata or [],
                    groups or [],
                ),
            )
        ]
