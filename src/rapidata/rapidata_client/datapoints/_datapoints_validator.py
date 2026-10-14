from itertools import zip_longest
from typing import Literal, cast, Iterable
from rapidata.rapidata_client.datapoints._datapoint import (
    Datapoint,
    coerce_media_context,
)


class DatapointsValidator:
    @staticmethod
    def validate_datapoints(
        datapoints: list[str] | list[list[str]],
        contexts: list[str] | None = None,
        media_contexts: list[list[str]] | list[str] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
        groups: list[str] | None = None,
        multi_asset: bool = False,
        answer_options: list[list[str]] | None = None,
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
            raise ValueError("Number of media contexts must match number of datapoints")
        if sentences and len(sentences) != len(datapoints):
            raise ValueError("Number of sentences must match number of datapoints")
        if private_metadata and len(private_metadata) != len(datapoints):
            raise ValueError(
                "Number of private metadata entries must match number of datapoints"
            )
        if answer_options is not None:
            if len(answer_options) != len(datapoints):
                raise ValueError(
                    "Number of answer option lists must match number of datapoints"
                )
            for index, options in enumerate(answer_options):
                if not 2 <= len(options) <= 8:
                    raise ValueError(
                        f"Datapoint {index} must have between 2 and 8 answer options, got {len(options)}"
                    )
                if any(not option for option in options) or len(set(options)) != len(
                    options
                ):
                    raise ValueError(
                        f"Answer options of datapoint {index} must be non-empty and unique"
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
        answer_options: list[list[str]] | None = None,
    ) -> list[Datapoint]:
        DatapointsValidator.validate_datapoints(
            datapoints=datapoints,
            contexts=contexts,
            media_contexts=media_contexts,
            sentences=sentences,
            private_metadata=private_metadata,
            groups=groups,
            multi_asset=multi_asset,
            answer_options=answer_options,
        )
        # ``media_context`` may arrive as a ``str`` (legacy form, one media
        # context per datapoint) or as a ``list[str]``. The same
        # ``coerce_media_context`` helper that backs the Datapoint field
        # validator handles both — calling it here narrows the static type
        # so pyright is happy with the Datapoint constructor.
        datapoints_list = [
            Datapoint(
                asset=asset,
                data_type=data_type,
                context=context,
                media_context=coerce_media_context(media_context),
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
        for datapoint, options in zip(datapoints_list, answer_options or []):
            datapoint.answer_options = options
        return datapoints_list
