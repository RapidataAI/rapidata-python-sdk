from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.utils.threaded_uploader import ThreadedUploader


class TrainingRapidUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_training_rapids_to_audience(
        self, rapids: list[Rapid], audience_id: str
    ) -> tuple[list[Rapid], list[Rapid]]:
        """
        Upload training rapids to an audience in parallel using multiple threads.

        Args:
            rapids: List of rapids to upload.
            audience_id: The ID of the audience to upload to.

        Returns:
            tuple[list[Rapid], list[Rapid]]: Lists of successful and failed uploads.
        """
        with tracer.start_as_current_span(
            "TrainingRapidUploader.upload_training_rapids_to_audience"
        ):
            logger.debug(f"Uploading training rapids to audience: {audience_id}")

            def upload_single_rapid(rapid: Rapid, index: int) -> None:
                from rapidata.api_client.models.add_rapid_to_audience_model import (
                    AddRapidToAudienceModel,
                )

                self.openapi_service.audience_api.audience_audience_id_rapid_post(
                    audience_id=audience_id,
                    add_rapid_to_audience_model=AddRapidToAudienceModel(
                        asset=self.asset_uploader.get_uploaded_asset_input(rapid.asset),
                        payload=rapid.payload,
                        truth=(rapid.truth if rapid.truth else None),
                        randomCorrectProbability=rapid.random_correct_probability,
                        explanation=rapid.explanation,
                        context=rapid.context,
                        contextAsset=(
                            self.asset_uploader.get_uploaded_asset_input(
                                rapid.media_context
                            )
                            if rapid.media_context
                            else None
                        ),
                        featureFlags=(
                            [setting._to_feature_flag() for setting in rapid.settings]
                            if rapid.settings
                            else None
                        ),
                    ),
                )

            uploader: ThreadedUploader[Rapid] = ThreadedUploader(
                upload_fn=upload_single_rapid,
                description="Uploading training rapids",
            )

            successful_uploads, failed_uploads = uploader.upload(rapids)

            if failed_uploads:
                logger.error(
                    "Upload failed for %s training rapids: %s",
                    len(failed_uploads),
                    failed_uploads,
                )

            return successful_uploads, failed_uploads
