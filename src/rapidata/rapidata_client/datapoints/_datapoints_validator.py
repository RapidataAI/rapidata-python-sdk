from itertools import zip_longest
from typing import Literal, cast, Iterable
from rapidata.rapidata_client.datapoints._datapoint import Datapoint


class DatapointsValidator:
    @staticmethod
    def validate_datapoints(
        datapoints: list[str] | list[list[str]],
        contexts: list[str] | None = None,
        media_contexts: list[str] | list[list[str]] | None = None,
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
        if media_contexts is not None:
            if len(media_contexts) != len(datapoints):
                raise ValueError(
                    "Number of media contexts must match number of datapoints"
                )
            # Allow either list[str] (one image per datapoint) or
            # list[list[str]] (multiple images per datapoint). Reject mixed input.
            has_str = any(isinstance(mc, str) for mc in media_contexts)
            has_list = any(isinstance(mc, list) for mc in media_contexts)
            if has_str and has_list:
                raise ValueError(
                    "media_contexts must be either a list of strings or a list of lists of strings, not a mix."
                )
            if has_list:
                for mc in media_contexts:
                    if not isinstance(mc, list):
                        # should not happen because of has_list/has_str check
                        continue
                    if len(mc) == 0:
                        raise ValueError(
                            "Each inner media_contexts list must contain at least one string. Use None for the whole field if not needed."
                        )
                    if any(not isinstance(item, str) or item == "" for item in mc):
                        raise ValueError(
                            "Every entry in a media_contexts inner list must be a non-empty string."
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
        media_contexts: list[str] | list[list[str]] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
        groups: list[str] | None = None,
        data_type: Literal["text", "media"] = "media",
        multi_asset: bool = False,
    ) -> list[Datapoint]:
        DatapointsValidator.validate_datapoints(
            datapoints=datapoints,
            contexts=contexts,
            media_contexts=media_contexts,
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
                "Iterable[tuple[str | list[str], str | None, str | list[str] | None, str | None, dict[str, str] | None, str | None]]",  # because iterator only supports 5 arguments with specific type casting
                zip_longest(
                    datapoints,
                    contexts or [],
                    media_contexts or [],
                    sentences or [],
                    private_metadata or [],
                    groups or [],
                ),
            )
        ]
