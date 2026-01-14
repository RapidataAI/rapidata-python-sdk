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
from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_validation_truth import IValidationTruth


class ValidationRapidUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_rapid(self, rapid: Rapid, validation_set_id: str) -> None:
        uploaded_asset: IAssetInput = (
            self.asset_uploader.get_uploaded_asset_input(rapid.asset)
            if rapid.data_type == "media"
            else self.asset_uploader.get_uploaded_text_input(rapid.asset)
        )

        self.openapi_service.validation_api.validation_set_validation_set_id_rapid_post(
            validation_set_id=validation_set_id,
            add_validation_rapid_model=AddValidationRapidModel(
                asset=uploaded_asset,
                payload=self._get_payload(rapid),
                context=rapid.context,
                contextAsset=(
                    self.asset_uploader.get_uploaded_asset_input(rapid.media_context)
                    if rapid.media_context
                    else None
                ),
                truth=rapid.truth,
                randomCorrectProbability=rapid.random_correct_probability,
                explanation=rapid.explanation,
                featureFlags=(
                    [setting._to_feature_flag_model() for setting in rapid.settings]
                    if rapid.settings
                    else None
                ),
            ),
        )

    def _get_payload(self, rapid: Rapid) -> IRapidPayload:
        if isinstance(rapid.payload, dict):
            return IRapidPayload(actual_instance=rapid.payload)
        return IRapidPayload(actual_instance=rapid.payload.to_dict())
