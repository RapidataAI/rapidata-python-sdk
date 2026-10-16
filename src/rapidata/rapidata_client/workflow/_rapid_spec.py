from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.api_client.models.asset_binding import AssetBinding
from rapidata.api_client.models.i_order_workflow_input import IOrderWorkflowInput
from rapidata.api_client.models.i_order_workflow_input_simple_workflow_input import (
    IOrderWorkflowInputSimpleWorkflowInput,
)
from rapidata.api_client.models.i_rapid_spec import IRapidSpec
from rapidata.api_client.models.text_binding import TextBinding
from rapidata.rapidata_client.datapoints._default_segments import ASSET_SEGMENT_KEY

if TYPE_CHECKING:
    from rapidata.api_client.models.i_rapid_spec_bounding_box_rapid_spec import (
        IRapidSpecBoundingBoxRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_classify_rapid_spec import (
        IRapidSpecClassifyRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_compare_rapid_spec import (
        IRapidSpecCompareRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_free_text_rapid_spec import (
        IRapidSpecFreeTextRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_line_rapid_spec import (
        IRapidSpecLineRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_locate_rapid_spec import (
        IRapidSpecLocateRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_scrub_rapid_spec import (
        IRapidSpecScrubRapidSpec,
    )
    from rapidata.api_client.models.i_rapid_spec_transcription_rapid_spec import (
        IRapidSpecTranscriptionRapidSpec,
    )

    RapidSpec = (
        IRapidSpecBoundingBoxRapidSpec
        | IRapidSpecClassifyRapidSpec
        | IRapidSpecCompareRapidSpec
        | IRapidSpecFreeTextRapidSpec
        | IRapidSpecLineRapidSpec
        | IRapidSpecLocateRapidSpec
        | IRapidSpecScrubRapidSpec
        | IRapidSpecTranscriptionRapidSpec
    )

ASSET = AssetBinding(segment=ASSET_SEGMENT_KEY)


def literal(text: str) -> TextBinding:
    return TextBinding(literal=text)


def segment(key: str) -> TextBinding:
    return TextBinding(segment=key)


def simple_workflow(spec: RapidSpec) -> IOrderWorkflowInput:
    return IOrderWorkflowInput(
        actual_instance=IOrderWorkflowInputSimpleWorkflowInput(
            _t="SimpleWorkflow",
            rapid=IRapidSpec(actual_instance=spec),
        )
    )
