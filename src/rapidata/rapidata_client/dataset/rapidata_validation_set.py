from typing import Any
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)
from rapidata.api_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)
from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth
from rapidata.api_client.models.bounding_box_payload import BoundingBoxPayload
from rapidata.api_client.models.bounding_box_truth import BoundingBoxTruth
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.compare_truth import CompareTruth
from rapidata.api_client.models.datapoint_metadata_model_metadata_inner import (
    DatapointMetadataModelMetadataInner,
)
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
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService


class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Get a `ValidationSet` either by using `rapi.get_validation_set(id)` to get an exisitng validation set or by using `rapi.new_validation_set(name)` to create a new validation set.
    """

    def __init__(self, validation_set_id, openapi_service: OpenAPIService):
        self.id = validation_set_id
        self.openapi_service = openapi_service

    def add_validation_rapid(
        self,
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
        ),
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
        ),
        metadata: list[Metadata],
        media_paths: str | list[str],
        randomCorrectProbability: float,
    ):
        """Add a validation rapid to the validation set.

        Args:
            payload (BoundingBoxPayload | ClassifyPayload | ComparePayload | FreeTextPayload | LinePayload | LocatePayload | NamedEntityPayload | PolygonPayload | TranscriptionPayload): The payload for the rapid.
            truths (AttachCategoryTruth | BoundingBoxTruth | CompareTruth | EmptyValidationTruth | LineTruth | LocateBoxTruth | NamedEntityTruth | PolygonTruth | TranscriptionTruth): The truths for the rapid.
            metadata (list[Metadata]): The metadata for the rapid.
            media_paths (str | list[str]): The media paths for the rapid.
            randomCorrectProbability (float): The random correct probability for the rapid.
        """
        model = AddValidationRapidModel(
            validationSetId=self.id,
            payload=AddValidationRapidModelPayload(payload),
            truth=AddValidationRapidModelTruth(truths),
            metadata=[
                DatapointMetadataModelMetadataInner(meta.to_model())
                for meta in metadata
            ],
            randomCorrectProbability=randomCorrectProbability,
        )

        self.openapi_service.validation_api.validation_add_validation_rapid_post(
            model=model, files=media_paths if isinstance(media_paths, list) else [media_paths]  # type: ignore
        )
