from pydantic import StrictBytes, StrictStr
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata
from typing import Sequence
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

from rapidata.service.openapi_service import OpenAPIService

import requests

class Rapid():
    def __init__(self, asset: MediaAsset | TextAsset | MultiAsset, metadata: Sequence[Metadata], payload: Any, truth: Any, randomCorrectProbability: float, explanation: str | None):
        self.asset = asset
        self.metadata = metadata
        self.payload = payload
        self.truth = truth
        self.randomCorrectProbability = randomCorrectProbability
        self.explanation = explanation 

    def _add_to_validation_set(self, validationSetId: str, openapi_service: OpenAPIService, session: requests.Session) -> None:
        if isinstance(self.asset, TextAsset) or (isinstance(self.asset, MultiAsset) and isinstance(self.asset.assets[0], TextAsset)):
            openapi_service.validation_api.validation_add_validation_text_rapid_post(
                add_validation_text_rapid_model=self.__to_text_model(validationSetId)
            )

        elif isinstance(self.asset, MediaAsset) or (isinstance(self.asset, MultiAsset) and isinstance(self.asset.assets[0], MediaAsset)):
            model = self.__to_media_model(validationSetId, session=session)
            openapi_service.validation_api.validation_add_validation_rapid_post(
                model=model[0], files=model[1]
            )
            
        else:
            raise TypeError("The asset must be a MediaAsset, TextAsset, or MultiAsset")

    def __to_media_model(self, validationSetId: str, session: requests.Session) -> tuple[AddValidationRapidModel, list[StrictStr | tuple[StrictStr, StrictBytes] | StrictBytes]]:
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

        for asset in assets:
            asset.session = session

        return (AddValidationRapidModel(
            validationSetId=validationSetId,
            payload=AddValidationRapidModelPayload(self.payload),
            truth=AddValidationRapidModelTruth(self.truth),
            metadata=[
              DatapointMetadataModelMetadataInner(meta.to_model())
              for meta in self.metadata
            ],
            randomCorrectProbability=self.randomCorrectProbability,
            explanation=self.explanation
        ), [asset.to_file() for asset in assets])

    def __to_text_model(self, validationSetId: str) -> AddValidationTextRapidModel:
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
              DatapointMetadataModelMetadataInner(meta.to_model())
              for meta in self.metadata
          ],
          randomCorrectProbability=self.randomCorrectProbability,
          texts=texts,
          explanation=self.explanation
      )
