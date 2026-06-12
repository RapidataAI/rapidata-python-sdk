from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.add_validation_rapid_endpoint_input import (
    AddValidationRapidEndpointInput,
)
from rapidata.api_client.models.i_rapid_payload_model import IRapidPayloadModel
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._truth_translator import (
    translate_compare_truth,
)


class ValidationRapidUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_rapid(self, rapid: Rapid, validation_set_id: str) -> None:
        uploaded_asset, asset_to_uploaded = (
            self.asset_uploader.build_asset_input_with_names(
                rapid.asset, rapid.data_type
            )
        )

        truth = (
            translate_compare_truth(rapid.truth, asset_to_uploaded)
            if rapid.data_type == "media"
            else rapid.truth
        )

        context_asset = (
            self.asset_uploader.upload_and_map_asset(rapid.media_context)
            if rapid.media_context
            else None
        )

        self.openapi_service.validation.validation_api.validation_set_validation_set_id_rapid_post(
            validation_set_id=validation_set_id,
            add_validation_rapid_endpoint_input=AddValidationRapidEndpointInput(
                asset=uploaded_asset,
                payload=self._get_payload(rapid),
                context=rapid.context,
                contextAsset=context_asset,
                truth=truth,
                randomCorrectProbability=rapid.random_correct_probability,
                explanation=rapid.explanation,
                featureFlags=(
                    [setting._to_feature_flag() for setting in rapid.settings]
                    if rapid.settings
                    else None
                ),
            ),
        )

    def _get_payload(self, rapid: Rapid) -> IRapidPayloadModel:
        if isinstance(rapid.payload, dict):
            return IRapidPayloadModel.from_dict(rapid.payload)
        payload_dict = rapid.payload.to_dict()
        if not isinstance(payload_dict, dict):
            raise ValueError(
                f"Expected payload to serialise to a dict, got {type(payload_dict).__name__}"
            )
        return IRapidPayloadModel.from_dict(payload_dict)
