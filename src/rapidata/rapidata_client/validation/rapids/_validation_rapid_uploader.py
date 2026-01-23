from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_validation_truth_model import IValidationTruthModel
from rapidata.api_client.models.i_validation_truth_model_compare_truth_model import (
    IValidationTruthModelCompareTruthModel,
)
from rapidata.api_client.models.i_validation_truth_model_multi_compare_truth_model import (
    IValidationTruthModelMultiCompareTruthModel,
)
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._asset_mapper import AssetMapper


class ValidationRapidUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)
        self.asset_mapper = AssetMapper()

    def upload_rapid(self, rapid: Rapid, validation_set_id: str) -> None:
        asset_to_uploaded: dict[str, str] = {}

        if rapid.data_type == "media":
            uploaded_asset, asset_to_uploaded = self._upload_and_map_asset(rapid.asset)
        else:
            uploaded_asset = self.asset_mapper.create_text_input(rapid.asset)

        # Translate truth for compare rapids with media assets
        truth = self._translate_compare_truth(rapid, asset_to_uploaded)

        self.openapi_service.validation_api.validation_set_validation_set_id_rapid_post(
            validation_set_id=validation_set_id,
            add_validation_rapid_model=AddValidationRapidModel(
                asset=uploaded_asset,
                payload=self._get_payload(rapid),
                context=rapid.context,
                contextAsset=(
                    self.asset_mapper.create_existing_asset_input(
                        self.asset_uploader.upload_asset(rapid.media_context)
                    )
                    if rapid.media_context
                    else None
                ),
                truth=truth,
                randomCorrectProbability=rapid.random_correct_probability,
                explanation=rapid.explanation,
                featureFlags=(
                    [setting._to_feature_flag_model() for setting in rapid.settings]
                    if rapid.settings
                    else None
                ),
            ),
        )

    def _upload_and_map_asset(
        self, asset: str | list[str]
    ) -> tuple[IAssetInput, dict[str, str]]:
        """Upload asset(s) and map to IAssetInput.

        Returns:
            Tuple of (IAssetInput, mapping from original asset paths to uploaded names)
        """
        if isinstance(asset, list):
            asset_to_uploaded = {a: self.asset_uploader.upload_asset(a) for a in asset}
            uploaded_names = list(asset_to_uploaded.values())
            return (
                self.asset_mapper.create_existing_asset_input(uploaded_names),
                asset_to_uploaded,
            )
        else:
            uploaded_name = self.asset_uploader.upload_asset(asset)
            return (
                self.asset_mapper.create_existing_asset_input(uploaded_name),
                {asset: uploaded_name},
            )

    def _translate_compare_truth(
        self, rapid: Rapid, asset_to_uploaded: dict[str, str]
    ) -> IValidationTruthModel | None:
        """Translate compare rapid truth from original asset paths to uploaded names.

        For compare rapids with media assets, the truth's winnerId or correctCombinations
        need to be translated from original asset paths to uploaded asset names.
        """
        if not rapid.truth or rapid.data_type != "media":
            return rapid.truth

        if not rapid.truth.actual_instance:
            return rapid.truth

        # Handle CompareTruth
        if isinstance(
            rapid.truth.actual_instance, IValidationTruthModelCompareTruthModel
        ):
            compare_truth = rapid.truth.actual_instance
            original_winner_id = compare_truth.winner_id

            # If the winner_id is in our mapping, translate it
            if original_winner_id in asset_to_uploaded:
                uploaded_winner_id = asset_to_uploaded[original_winner_id]
                return IValidationTruthModel(
                    actual_instance=IValidationTruthModelCompareTruthModel(
                        _t="CompareTruth", winnerId=uploaded_winner_id
                    )
                )

        # Handle MultiCompareTruth
        elif isinstance(
            rapid.truth.actual_instance, IValidationTruthModelMultiCompareTruthModel
        ):
            multi_compare_truth = rapid.truth.actual_instance
            translated_combinations = []

            for combination in multi_compare_truth.correct_combinations:
                translated_combo = [
                    asset_to_uploaded.get(asset_id, asset_id) for asset_id in combination
                ]
                translated_combinations.append(translated_combo)

            return IValidationTruthModel(
                actual_instance=IValidationTruthModelMultiCompareTruthModel(
                    _t="MultiCompareTruth", correctCombinations=translated_combinations
                )
            )

        return rapid.truth

    def _get_payload(self, rapid: Rapid) -> IRapidPayload:
        if isinstance(rapid.payload, dict):
            return IRapidPayload(actual_instance=rapid.payload)
        return IRapidPayload(actual_instance=rapid.payload.to_dict())
