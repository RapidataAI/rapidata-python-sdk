from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.multi_asset_input_assets_inner import (
    MultiAssetInput,
    MultiAssetInputAssetsInner,
)
from rapidata.api_client.models.add_validation_rapid_new_model import (
    AddValidationRapidNewModel,
)
from rapidata.api_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)
from rapidata.api_client.models.create_datapoint_from_files_model_metadata_inner import (
    CreateDatapointFromFilesModelMetadataInner,
)
from rapidata.api_client.models.existing_asset_input import ExistingAssetInput
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints.metadata import (
    PromptMetadata,
    MediaAssetMetadata,
    SelectWordsMetadata,
    Metadata,
)
from rapidata.api_client.models.add_validation_rapid_new_model_asset import (
    AddValidationRapidNewModelAsset,
)
from rapidata.api_client.models.text_asset_input import TextAssetInput
from rapidata.api_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)


class ValidationRapidUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_rapid(self, rapid: Rapid, validation_set_id: str) -> None:
        metadata = self._get_metadata(rapid)

        uploaded_asset = (
            self._handle_media_rapid(rapid)
            if rapid.data_type == "media"
            else self._handle_text_rapid(rapid)
        )

        self.openapi_service.validation_api.validation_set_validation_set_id_rapid_new_post(
            validation_set_id=validation_set_id,
            add_validation_rapid_new_model=AddValidationRapidNewModel(
                asset=uploaded_asset,
                metadata=metadata,
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

    def _get_metadata(
        self, rapid: Rapid
    ) -> list[CreateDatapointFromFilesModelMetadataInner]:
        rapid_metadata: list[Metadata] = []
        if rapid.context:
            rapid_metadata.append(PromptMetadata(prompt=rapid.context))
        if rapid.sentence:
            rapid_metadata.append(SelectWordsMetadata(select_words=rapid.sentence))
        if rapid.media_context:
            rapid_metadata.append(
                MediaAssetMetadata(
                    internal_file_name=self.asset_uploader.upload_asset(
                        rapid.media_context
                    )
                )
            )

        metadata = [
            CreateDatapointFromFilesModelMetadataInner(
                actual_instance=metadata.to_model()
            )
            for metadata in rapid_metadata
        ]

        return metadata

    def _handle_text_rapid(self, rapid: Rapid) -> AddValidationRapidNewModelAsset:
        return AddValidationRapidNewModelAsset(
            actual_instance=self.asset_uploader.get_uploaded_text_input(rapid.asset),
        )

    def _handle_media_rapid(self, rapid: Rapid) -> AddValidationRapidNewModelAsset:
        return AddValidationRapidNewModelAsset(
            actual_instance=self.asset_uploader.get_uploaded_asset_input(rapid.asset),
        )
