from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.add_validation_rapid_endpoint_input import (
    AddValidationRapidEndpointInput,
)
from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_rapid_payload_model import IRapidPayloadModel
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
            uploaded_asset, asset_to_uploaded = self._upload_rapid_asset(rapid.asset)
        else:
            uploaded_asset = self.asset_mapper.create_text_input(rapid.asset)

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
                truth=self._translate_compare_truth(rapid, asset_to_uploaded),
                randomCorrectProbability=rapid.random_correct_probability,
                explanation=rapid.explanation,
                featureFlags=(
                    [setting._to_feature_flag() for setting in rapid.settings]
                    if rapid.settings
                    else None
                ),
            ),
        )

    def _upload_rapid_asset(
        self, asset: str | list[str]
    ) -> tuple[IAssetInput, dict[str, str]]:
        """Upload the rapid asset(s) and return the wrapped input plus a path→name map.

        The map lets ``_translate_compare_truth`` rewrite truth references
        (winner ids, correct combinations) from caller-supplied paths to the
        uploaded names the API expects. Truth only ever points at the rapid's
        own assets, so this mapping isn't needed for ``media_context``.
        """
        if isinstance(asset, list):
            asset_to_uploaded = {a: self.asset_uploader.upload_asset(a) for a in asset}
            return (
                self.asset_mapper.create_existing_asset_input(
                    list(asset_to_uploaded.values())
                ),
                asset_to_uploaded,
            )

        uploaded_name = self.asset_uploader.upload_asset(asset)
        return (
            self.asset_mapper.create_existing_asset_input(uploaded_name),
            {asset: uploaded_name},
        )

    def _translate_compare_truth(
        self, rapid: Rapid, asset_to_uploaded: dict[str, str]
    ) -> IValidationTruthModel | None:
        """Translate compare rapid truth from original asset paths to uploaded names.

        For compare rapids with media assets, ``winnerId`` /
        ``correctCombinations`` reference assets by their original path, but
        the API expects uploaded names.
        """
        if not rapid.truth or rapid.data_type != "media":
            return rapid.truth

        if not rapid.truth.actual_instance:
            return rapid.truth

        if isinstance(
            rapid.truth.actual_instance, IValidationTruthModelCompareTruthModel
        ):
            compare_truth = rapid.truth.actual_instance
            original_winner_id = compare_truth.winner_id

            if original_winner_id in asset_to_uploaded:
                return IValidationTruthModel(
                    actual_instance=IValidationTruthModelCompareTruthModel(
                        _t="CompareTruth",
                        winnerId=asset_to_uploaded[original_winner_id],
                    )
                )

        elif isinstance(
            rapid.truth.actual_instance, IValidationTruthModelMultiCompareTruthModel
        ):
            multi_compare_truth = rapid.truth.actual_instance
            translated_combinations = [
                [
                    asset_to_uploaded.get(asset_id, asset_id)
                    for asset_id in combination
                ]
                for combination in multi_compare_truth.correct_combinations
            ]

            return IValidationTruthModel(
                actual_instance=IValidationTruthModelMultiCompareTruthModel(
                    _t="MultiCompareTruth", correctCombinations=translated_combinations
                )
            )

        return rapid.truth

    def _get_payload(self, rapid: Rapid) -> IRapidPayloadModel:
        if isinstance(rapid.payload, dict):
            return IRapidPayloadModel.from_dict(rapid.payload)
        payload_dict = rapid.payload.to_dict()
        if not isinstance(payload_dict, dict):
            raise ValueError(
                f"Expected payload to serialise to a dict, got {type(payload_dict).__name__}"
            )
        return IRapidPayloadModel.from_dict(payload_dict)
