from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.dataset_segment_definition import (
        DatasetSegmentDefinition,
    )
    from rapidata.api_client.models.dataset_segment_input import DatasetSegmentInput
    from rapidata.api_client.models.i_asset_input import IAssetInput

# Keys of the backend's default dataset schema; must match it exactly.
ASSET_SEGMENT_KEY = "asset"
CONTEXT_SEGMENT_KEY = "context"
CONTEXT_ASSET_SEGMENT_KEY = "context_asset"
TRANSCRIPTION_SEGMENT_KEY = "transcription"
ANSWER_OPTIONS_SEGMENT_KEY = "answer_options"


def build_default_segments(
    asset: IAssetInput | None = None,
    context: str | None = None,
    context_asset: IAssetInput | None = None,
    transcription: str | None = None,
    answer_options: list[str] | None = None,
) -> list[DatasetSegmentInput]:
    """Map the flat datapoint fields onto the default dataset schema; a None value gets no segment."""
    from rapidata.api_client.models.dataset_segment_input import DatasetSegmentInput
    from rapidata.api_client.models.dataset_segment_kind import DatasetSegmentKind
    from rapidata.api_client.models.dataset_segment_option import DatasetSegmentOption

    segments: list[DatasetSegmentInput] = []
    if asset is not None:
        segments.append(
            DatasetSegmentInput(
                key=ASSET_SEGMENT_KEY, kind=DatasetSegmentKind.ASSET, asset=asset
            )
        )
    if context is not None:
        segments.append(
            DatasetSegmentInput(
                key=CONTEXT_SEGMENT_KEY, kind=DatasetSegmentKind.TEXT, text=context
            )
        )
    if context_asset is not None:
        segments.append(
            DatasetSegmentInput(
                key=CONTEXT_ASSET_SEGMENT_KEY,
                kind=DatasetSegmentKind.ASSET,
                asset=context_asset,
            )
        )
    if transcription is not None:
        segments.append(
            DatasetSegmentInput(
                key=TRANSCRIPTION_SEGMENT_KEY,
                kind=DatasetSegmentKind.TEXT,
                text=transcription,
            )
        )
    if answer_options is not None:
        segments.append(
            DatasetSegmentInput(
                key=ANSWER_OPTIONS_SEGMENT_KEY,
                kind=DatasetSegmentKind.OPTIONLIST,
                options=[
                    DatasetSegmentOption(label=option, value=option)
                    for option in answer_options
                ],
            )
        )
    return segments


def build_schema(required: set[str]) -> list[DatasetSegmentDefinition]:
    """The asset and context segments, plus each workflow segment in ``required``."""
    from rapidata.api_client.models.dataset_segment_definition import (
        DatasetSegmentDefinition,
    )
    from rapidata.api_client.models.dataset_segment_kind import DatasetSegmentKind

    workflow_segments = {
        TRANSCRIPTION_SEGMENT_KEY: ("Transcription", DatasetSegmentKind.TEXT),
        ANSWER_OPTIONS_SEGMENT_KEY: ("Answer options", DatasetSegmentKind.OPTIONLIST),
    }
    return [
        DatasetSegmentDefinition(
            key=ASSET_SEGMENT_KEY,
            label="Asset",
            kind=DatasetSegmentKind.ASSET,
            required=True,
        ),
        DatasetSegmentDefinition(
            key=CONTEXT_SEGMENT_KEY,
            label="Context",
            kind=DatasetSegmentKind.TEXT,
            required=False,
            maxLength=400,
        ),
        DatasetSegmentDefinition(
            key=CONTEXT_ASSET_SEGMENT_KEY,
            label="Context asset",
            kind=DatasetSegmentKind.ASSET,
            required=False,
        ),
        *(
            DatasetSegmentDefinition(
                key=key,
                label=workflow_segments[key][0],
                kind=workflow_segments[key][1],
                required=True,
            )
            for key in sorted(required)
        ),
    ]
