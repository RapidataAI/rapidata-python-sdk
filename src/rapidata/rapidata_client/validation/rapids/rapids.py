from rapidata.api_client import ClassifyPayload
from rapidata.rapidata_client import assets
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.metadata import Metadata
from typing import Sequence
from rapidata.rapidata_client.validation.rapids.box import Box
from typing import Any
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.add_validation_text_rapid_model import (
    AddValidationTextRapidModel,
)
from rapidata.api_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)
from rapidata.api_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)

from rapidata.api_client.models.datapoint_metadata_model_metadata_inner import (
    DatapointMetadataModelMetadataInner,
)


class Rapid():
    def __init__(self, asset: MediaAsset | TextAsset | MultiAsset, metadata: Sequence[Metadata], payload: Any, truth: Any, randomCorrectProbability: float, explanation: str | None):
        self.asset = asset
        self.metadata = metadata
        self.payload = payload
        self.truth = truth
        self.randomCorrectProbability = randomCorrectProbability
        self.explanation = explanation 

    def to_media_model(self, validationSetId: str) -> tuple[AddValidationRapidModel, list[str | tuple[str, bytes]]]:
        assets: list[MediaAsset] = [] 
        if isinstance(self.asset, MultiAsset):
            for asset in self.asset.assets:
                if isinstance(asset, MediaAsset):
                    assets.append(asset)
                else:
                    raise TypeError("The asset is a multiasset, but not all assets are MediaAssets")

        if isinstance(self.asset, TextAsset):
            raise TypeError("The asset must contain Media")

        if isinstance(self.asset, MediaAsset):
            assets = [self.asset]

        return (AddValidationRapidModel(
            validationSetId=validationSetId,
            payload=AddValidationRapidModelPayload(self.payload),
            truth=AddValidationRapidModelTruth(self.truth),
            metadata=[
              DatapointMetadataModelMetadataInner(meta._to_model())
              for meta in self.metadata
            ],
            randomCorrectProbability=self.randomCorrectProbability,
            explanation=self.explanation
        ), [self._convert_asset(asset) for asset in assets])

    def _convert_asset(self, asset: MediaAsset) -> str | tuple[str, bytes]:
        if isinstance(asset.path, str):
            return asset.path
        elif isinstance(asset.path, bytes):
            return (asset.name, asset.path)
        else:
            raise ValueError("upload file failed")

    def to_text_model(self, validationSetId: str) -> AddValidationTextRapidModel:
        texts: list[str] = []
        if isinstance(self.asset, MultiAsset):
            for asset in self.asset.assets:
                if isinstance(asset, TextAsset):
                    texts.append(asset.text)
                else:
                    raise TypeError("The asset is a multiasset, but not all assets are TextAssets")

        if isinstance(self.asset, MediaAsset):
            raise TypeError("The asset must contain Text")

        if isinstance(self.asset, TextAsset):
            texts = [self.asset.text]

        return AddValidationTextRapidModel(
          validationSetId=validationSetId,
          payload=AddValidationRapidModelPayload(self.payload),
          truth=AddValidationRapidModelTruth(self.truth),
          metadata=[
              DatapointMetadataModelMetadataInner(meta._to_model())
              for meta in self.metadata
          ],
          randomCorrectProbability=self.randomCorrectProbability,
          texts=texts,
          explanation=self.explanation
      )