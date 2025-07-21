from rapidata.rapidata_client.datapoints.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.datapoints.metadata import Metadata
from typing import Sequence, Any, cast
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)
from rapidata.api_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)
from rapidata.api_client.models.dataset_dataset_id_datapoints_post_request_metadata_inner import DatasetDatasetIdDatapointsPostRequestMetadataInner
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.logging import logger


class Rapid():
    def __init__(self, asset: MediaAsset | TextAsset | MultiAsset, metadata: Sequence[Metadata], payload: Any, truth: Any, randomCorrectProbability: float, explanation: str | None):
        self.asset = asset
        self.metadata = metadata
        self.payload = payload
        self.truth = truth
        self.randomCorrectProbability = randomCorrectProbability
        self.explanation = explanation 
        logger.debug(f"Created Rapid with asset: {self.asset}, metadata: {self.metadata}, payload: {self.payload}, truth: {self.truth}, randomCorrectProbability: {self.randomCorrectProbability}, explanation: {self.explanation}")

    def _add_to_validation_set(self, validationSetId: str, openapi_service: OpenAPIService) -> None:
        model = self.__to_model()
        assets = self.__convert_to_assets()
        if isinstance(assets[0], TextAsset):
            assert all(isinstance(asset, TextAsset) for asset in assets)
            texts = cast(list[TextAsset], assets)
            openapi_service.validation_api.validation_set_validation_set_id_rapid_post(
                validation_set_id=validationSetId,
                model=model,
                texts=[asset.text for asset in texts]
            )

        elif isinstance(assets[0], MediaAsset):
            assert all(isinstance(asset, MediaAsset) for asset in assets)
            files = cast(list[MediaAsset], assets)
            openapi_service.validation_api.validation_set_validation_set_id_rapid_post(
                validation_set_id=validationSetId,
                model=model,
                files=[asset.to_file() for asset in files if asset.is_local()],
                urls=[asset.path for asset in files if not asset.is_local()]
            )
            
        else:
            raise TypeError("The asset must be a MediaAsset, TextAsset, or MultiAsset")
        
    
    def __convert_to_assets(self) -> list[MediaAsset | TextAsset]:
        assets: list[MediaAsset | TextAsset] = [] 
        if isinstance(self.asset, MultiAsset):
            for asset in self.asset.assets:
                if isinstance(asset, MediaAsset):
                    assets.append(asset)
                elif isinstance(asset, TextAsset):
                    assets.append(asset)
                else:
                    raise TypeError("The asset is a multiasset, but not all assets are MediaAssets or TextAssets")

        if isinstance(self.asset, TextAsset):
            assets = [self.asset]

        if isinstance(self.asset, MediaAsset):
            assets = [self.asset]

        return assets

    def __to_model(self) -> AddValidationRapidModel:
        return AddValidationRapidModel(
            payload=AddValidationRapidModelPayload(self.payload),
            truth=AddValidationRapidModelTruth(self.truth),
            metadata=[
              DatasetDatasetIdDatapointsPostRequestMetadataInner(meta.to_model())
              for meta in self.metadata
            ],
            randomCorrectProbability=self.randomCorrectProbability,
            explanation=self.explanation
        )
