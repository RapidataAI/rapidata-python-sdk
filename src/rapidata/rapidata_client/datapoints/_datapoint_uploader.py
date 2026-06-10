from __future__ import annotations

import time
from typing import TYPE_CHECKING

from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)
from rapidata.rapidata_client.config import logger, rapidata_config
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader

if TYPE_CHECKING:
    from rapidata.api_client.models.create_datapoint_endpoint_input import (
        CreateDatapointEndpointInput,
    )
    from rapidata.api_client.models.create_datapoint_endpoint_output import (
        CreateDatapointEndpointOutput,
    )


class DatapointUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_datapoint(
        self, datapoint: Datapoint, dataset_id: str, index: int
    ) -> CreateDatapointEndpointOutput:
        from rapidata.api_client.models.create_datapoint_endpoint_input import (
            CreateDatapointEndpointInput,
        )

        uploaded_asset = self.asset_uploader.build_asset_input(
            datapoint.asset, datapoint.data_type
        )

        # If the datapoint belongs to a group, context is handled at group level
        has_group = datapoint.group is not None
        context = None if has_group else datapoint.context
        context_asset = (
            None
            if has_group or not datapoint.media_context
            else self.asset_uploader.upload_and_map_asset(datapoint.media_context)
        )

        payload = CreateDatapointEndpointInput(
            asset=uploaded_asset,
            context=context,
            contextAsset=context_asset,
            transcription=datapoint.sentence,
            sortIndex=index,
            group=datapoint.group,
            privateMetadata=datapoint.private_metadata,
        )

        return self._create_datapoint_with_retries(dataset_id, index, payload)

    def _create_datapoint_with_retries(
        self,
        dataset_id: str,
        index: int,
        payload: CreateDatapointEndpointInput,
    ) -> CreateDatapointEndpointOutput:
        max_retries = rapidata_config.upload.maxRetries
        last_exception: Exception | None = None

        for attempt in range(max_retries):
            try:
                with suppress_rapidata_error_logging():
                    return self.openapi_service.dataset.datapoints_api.dataset_dataset_id_datapoint_post(
                        dataset_id=dataset_id,
                        create_datapoint_endpoint_input=payload,
                    )
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    retry_delay = 2**attempt
                    logger.debug(
                        "Datapoint creation failed (attempt %s/%s) for index %s: %s. Retrying in %ss...",
                        attempt + 1,
                        max_retries,
                        index,
                        e,
                        retry_delay,
                    )
                    time.sleep(retry_delay)

        assert last_exception is not None
        raise last_exception
