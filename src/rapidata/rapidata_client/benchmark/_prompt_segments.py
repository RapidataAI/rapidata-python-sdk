from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from rapidata.api_client.models.i_asset import IAsset
    from rapidata.api_client.models.prompt_segment import PromptSegment

# The two keys every benchmark's prompt structure starts with, and that the
# backend migration moved the old flat `prompt` / `promptAsset` content into.
# They mirror `PromptSegmentKeys` in the leaderboard service — writing an
# unknown key is a backend error, not a silently ignored field.
DEFAULT_TEXT_SEGMENT_KEY = "prompt"
DEFAULT_ASSET_SEGMENT_KEY = "prompt_asset"


def find_asset_segment(
    segments: Sequence[PromptSegment] | None,
) -> IAsset | None:
    """Resolve the asset a prompt's segments carry, if any.

    Prefers the default key so a default-structure benchmark round-trips
    exactly; falls back to the first asset-kind segment, which is how the
    backend's own faucets resolve reference media on a benchmark that renamed
    its segments.
    """
    from rapidata.api_client.models.prompt_segment_kind import PromptSegmentKind

    if not segments:
        return None

    asset_segments = [
        segment for segment in segments if segment.kind == PromptSegmentKind.ASSET
    ]
    for segment in asset_segments:
        if segment.key == DEFAULT_ASSET_SEGMENT_KEY and segment.asset is not None:
            return segment.asset

    for segment in asset_segments:
        if segment.asset is not None:
            return segment.asset

    return None
