from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.api_client.models.add_validation_rapid_model_asset import (
    AddValidationRapidModelAsset,
)
from rapidata.api_client.models.add_validation_rapid_model_context_asset import (
    AddValidationRapidModelContextAsset,
)
from rapidata.api_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)


class ValidationRapidUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_rapid(self, rapid: Rapid, validation_set_id: str) -> None:
        uploaded_asset = (
            self._handle_media_rapid(rapid)
            if rapid.data_type == "media"
            else self._handle_text_rapid(rapid)
        )

        self.openapi_service.validation_api.validation_set_validation_set_id_rapid_post(
            validation_set_id=validation_set_id,
            add_validation_rapid_model=AddValidationRapidModel(
                asset=uploaded_asset,
                context=rapid.context,
                contextAsset=(
                    AddValidationRapidModelContextAsset(
                        actual_instance=self.asset_uploader.get_uploaded_asset_input(
                            rapid.media_context
                        ),
                    )
                    if rapid.media_context
                    else None
                ),
                payload=self._get_payload(rapid),
                truth=AddValidationRapidModelTruth(actual_instance=rapid.truth),
                randomCorrectProbability=rapid.random_correct_probability,
                explanation=rapid.explanation,
                featureFlags=(
                    [setting._to_feature_flag() for setting in rapid.settings]
                    if rapid.settings
                    else None
                ),
            ),
        )

    def _get_payload(self, rapid: Rapid) -> AddValidationRapidModelPayload:
        if isinstance(rapid.payload, dict):
            return AddValidationRapidModelPayload(actual_instance=rapid.payload)
        return AddValidationRapidModelPayload(actual_instance=rapid.payload.to_dict())

    def _handle_text_rapid(self, rapid: Rapid) -> AddValidationRapidModelAsset:
        return AddValidationRapidModelAsset(
            actual_instance=self.asset_uploader.get_uploaded_text_input(rapid.asset),
        )

    def _handle_media_rapid(self, rapid: Rapid) -> AddValidationRapidModelAsset:
        return AddValidationRapidModelAsset(
            actual_instance=self.asset_uploader.get_uploaded_asset_input(rapid.asset),
        )
