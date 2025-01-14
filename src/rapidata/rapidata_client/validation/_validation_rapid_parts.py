from dataclasses import dataclass
from typing import Any

from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth
from rapidata.api_client.models.bounding_box_payload import BoundingBoxPayload
from rapidata.api_client.models.bounding_box_truth import BoundingBoxTruth
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.compare_truth import CompareTruth
from rapidata.api_client.models.empty_validation_truth import EmptyValidationTruth
from rapidata.api_client.models.free_text_payload import FreeTextPayload
from rapidata.api_client.models.line_payload import LinePayload
from rapidata.api_client.models.line_truth import LineTruth
from rapidata.api_client.models.locate_box_truth import LocateBoxTruth
from rapidata.api_client.models.locate_payload import LocatePayload
from rapidata.api_client.models.named_entity_payload import NamedEntityPayload
from rapidata.api_client.models.named_entity_truth import NamedEntityTruth
from rapidata.api_client.models.polygon_payload import PolygonPayload
from rapidata.api_client.models.polygon_truth import PolygonTruth
from rapidata.api_client.models.transcription_payload import TranscriptionPayload
from rapidata.api_client.models.transcription_truth import TranscriptionTruth
from rapidata.api_client.models.scrub_payload import ScrubPayload
from rapidata.api_client.models.scrub_truth import ScrubTruth

from rapidata.rapidata_client.assets._media_asset import MediaAsset
from rapidata.rapidata_client.assets._multi_asset import MultiAsset
from rapidata.rapidata_client.assets._text_asset import TextAsset
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from typing import Sequence


@dataclass
class ValidatioRapidParts:
    instruction: str
    asset: MediaAsset | TextAsset | MultiAsset
    payload: (
        BoundingBoxPayload
        | ClassifyPayload
        | ComparePayload
        | FreeTextPayload
        | LinePayload
        | LocatePayload
        | NamedEntityPayload
        | PolygonPayload
        | TranscriptionPayload
        | ScrubPayload
    )
    truths: (
        AttachCategoryTruth
        | BoundingBoxTruth
        | CompareTruth
        | EmptyValidationTruth
        | LineTruth
        | LocateBoxTruth
        | NamedEntityTruth
        | PolygonTruth
        | TranscriptionTruth
        | ScrubTruth
    )
    metadata: Sequence[Metadata]
    randomCorrectProbability: float
