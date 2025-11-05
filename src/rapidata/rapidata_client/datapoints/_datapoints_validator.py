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
        private_notes: list[str] | None = None,
        groups: list[str] | None = None,
    ) -> None:
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("Number of contexts must match number of datapoints")
        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("Number of media contexts must match number of datapoints")
        if sentences and len(sentences) != len(datapoints):
            raise ValueError("Number of sentences must match number of datapoints")
        if private_notes and len(private_notes) != len(datapoints):
            raise ValueError("Number of private notes must match number of datapoints")
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
        private_notes: list[str] | None = None,
        groups: list[str] | None = None,
        data_type: Literal["text", "media"] = "media",
    ) -> list[Datapoint]:
        DatapointsValidator.validate_datapoints(
            datapoints=datapoints,
            contexts=contexts,
            media_contexts=media_contexts,
            sentences=sentences,
            private_notes=private_notes,
            groups=groups,
        )
        return [
            Datapoint(
                asset=asset,
                data_type=data_type,
                context=context,
                media_context=media_context,
                sentence=sentence,
                private_note=private_note,
                group=group,
            )
            for asset, context, media_context, sentence, private_note, group in cast(
                "Iterable[tuple[str | list[str], str | None, str | None, str | None, str | None, str | None]]",  # because iterator only supports 5 arguments with specific type casting
                zip_longest(
                    datapoints,
                    contexts or [],
                    media_contexts or [],
                    sentences or [],
                    private_notes or [],
                    groups or [],
                ),
            )
        ]
