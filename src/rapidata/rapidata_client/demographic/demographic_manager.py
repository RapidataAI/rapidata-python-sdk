from rapidata.api_client import ExistingAssetInput
from rapidata.api_client.models.create_demographic_rapid_model_asset import (
    CreateDemographicRapidModelAsset,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.rapidata_client.config import logger
from rapidata.api_client.models.create_demographic_rapid_model_new import (
    CreateDemographicRapidModelNew,
)
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader


class DemographicManager:
    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._asset_uploader = AssetUploader(openapi_service)
        logger.debug("DemographicManager initialized")

    def create_demographic_rapid(
        self, instruction: str, answer_options: list[str], datapoint: str, key: str
    ):

        model = CreateDemographicRapidModelNew(
            key=key,
            payload=ClassifyPayload(
                _t="ClassifyPayload",
                possibleCategories=answer_options,
                title=instruction,
            ),
            asset=CreateDemographicRapidModelAsset(
                actual_instance=ExistingAssetInput(
                    _t="ExistingAssetInput",
                    name=self._asset_uploader.upload_asset(datapoint),
                ),
            ),
        )

        result = self._openapi_service.rapid_api.rapid_demographic_new_post(
            create_demographic_rapid_model_new=model
        )
        logger.info(f"Demographic Rapid created: {result.rapid_id}")
        return result.rapid_id

    def __str__(self) -> str:
        return "DemographicManager"

    def __repr__(self) -> str:
        return self.__str__()
