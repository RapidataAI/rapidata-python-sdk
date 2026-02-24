from itertools import zip_longest
from typing import Literal, cast, Iterable
from rapidata.rapidata_client.datapoints._datapoint import Datapoint


class DatapointsValidator:
    @staticmethod
    def validate_datapoints(
        datapoints: list[str] | list[list[str]],
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
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
        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("Number of media contexts must match number of datapoints")
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
        media_contexts: list[str] | None = None,
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
                "Iterable[tuple[str | list[str], str | None, str | None, str | None, dict[str, str] | None, str | None]]",  # because iterator only supports 5 arguments with specific type casting
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
