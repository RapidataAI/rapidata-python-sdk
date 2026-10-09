from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.dataset_segment_input import DatasetSegmentInput
    from rapidata.api_client.models.i_asset_input import IAssetInput

# Keys of the backend's default dataset schema; must match it exactly.
ASSET_SEGMENT_KEY = "asset"
CONTEXT_SEGMENT_KEY = "context"
CONTEXT_ASSET_SEGMENT_KEY = "context_asset"
TRANSCRIPTION_SEGMENT_KEY = "transcription"


def build_default_segments(
    asset: IAssetInput | None = None,
    context: str | None = None,
    context_asset: IAssetInput | None = None,
    transcription: str | None = None,
) -> list[DatasetSegmentInput]:
    """Map the flat datapoint fields onto the default dataset schema; a None value gets no segment."""
    from rapidata.api_client.models.dataset_segment_input import DatasetSegmentInput
    from rapidata.api_client.models.dataset_segment_kind import DatasetSegmentKind

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
    return segments
