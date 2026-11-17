from __future__ import annotations

from rapidata.api_client.models.board_segment_binding import BoardSegmentBinding
from rapidata.api_client.models.board_segment_source import BoardSegmentSource
from rapidata.api_client.models.board_text_binding import BoardTextBinding
from rapidata.api_client.models.i_board_rapid_spec import IBoardRapidSpec
from rapidata.api_client.models.i_board_rapid_spec_compare_board_rapid_spec import (
    IBoardRapidSpecCompareBoardRapidSpec,
)
from rapidata.rapidata_client.benchmark.prompt_metadata import (
    DEFAULT_ASSET_SEGMENT_KEY,
    DEFAULT_TEXT_SEGMENT_KEY,
)

DEFAULT_SAMPLE_SEGMENT_KEY = "sample"


def rapid_spec_from_flags(
    show_prompt: bool, show_prompt_asset: bool
) -> IBoardRapidSpec:
    return IBoardRapidSpec(
        IBoardRapidSpecCompareBoardRapidSpec(
            _t="Compare",
            asset=BoardSegmentBinding(
                source=BoardSegmentSource.SAMPLE, segment=DEFAULT_SAMPLE_SEGMENT_KEY
            ),
            context=(
                BoardTextBinding(
                    source=BoardSegmentSource.PROMPT,
                    segment=DEFAULT_TEXT_SEGMENT_KEY,
                )
                if show_prompt
                else None
            ),
            contextAsset=(
                BoardSegmentBinding(
                    source=BoardSegmentSource.PROMPT,
                    segment=DEFAULT_ASSET_SEGMENT_KEY,
                )
                if show_prompt_asset
                else None
            ),
        )
    )


def flags_from_rapid_spec(spec: IBoardRapidSpec) -> tuple[bool, bool]:
    """Returns (show_prompt, show_prompt_asset); an Open rapid shows neither."""
    compare = spec.actual_instance
    if not isinstance(compare, IBoardRapidSpecCompareBoardRapidSpec):
        return False, False
    return compare.context is not None, compare.context_asset is not None
