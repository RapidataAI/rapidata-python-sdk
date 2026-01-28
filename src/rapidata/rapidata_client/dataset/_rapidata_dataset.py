from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, Future

from tqdm.auto import tqdm

from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._datapoint_uploader import DatapointUploader
from rapidata.rapidata_client.datapoints._asset_upload_orchestrator import (
    AssetUploadOrchestrator,
)
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.config import rapidata_config, logger


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.datapoint_uploader = DatapointUploader(openapi_service)
        self.asset_orchestrator = AssetUploadOrchestrator(openapi_service)

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[FailedUpload[Datapoint]]]:
        """
        Upload datapoints with incremental creation:
        - Start uploading all assets (URLs in batches + files in parallel)
        - As assets complete, check which datapoints are ready and create them
        - Continue until all uploads and datapoint creation complete

        Args:
            datapoints: List of datapoints to upload

        Returns:
            tuple[list[Datapoint], list[FailedUpload[Datapoint]]]: Lists of successful uploads and failed uploads with error details

        Raises:
            AssetUploadException: If any asset uploads fail and prevent datapoint creation
        """
        if not datapoints:
            return [], []

        # 1. Build efficient reverse mapping: asset -> datapoint indices that need it
        # This allows O(1) lookup instead of checking all pending datapoints
        asset_to_datapoints: dict[str, set[int]] = {}
        datapoint_pending_count: dict[int, int] = {}  # How many assets each datapoint still needs

        for idx, dp in enumerate(datapoints):
            assets = set()
            if isinstance(dp.asset, list):
                assets.update(dp.asset)
            else:
                assets.add(dp.asset)
            if dp.media_context:
                assets.add(dp.media_context)

            # Track how many assets this datapoint needs
            datapoint_pending_count[idx] = len(assets)

            # Build reverse mapping
            for asset in assets:
                if asset not in asset_to_datapoints:
                    asset_to_datapoints[asset] = set()
                asset_to_datapoints[asset].add(idx)

        logger.debug(f"Mapped {len(datapoints)} datapoints to their required assets")

        # 2. Track state (thread-safe)
        creation_futures: list[tuple[int, Future]] = []
        lock = threading.Lock()

        # 3. Create executor for datapoint creation
        executor = ThreadPoolExecutor(max_workers=rapidata_config.upload.maxWorkers)

        # 4. Create progress bar for datapoint creation (position=1 to show below asset upload bar)
        datapoint_pbar = tqdm(
            total=len(datapoints),
            desc="Step 2/2: Creating datapoints",
            position=1,
            disable=rapidata_config.logging.silent_mode,
            leave=True,
        )

        # 5. Define callback for asset completion
        def on_assets_complete(assets: list[str]) -> None:
            """Called when a batch of assets completes uploading."""
            ready_datapoints = []

            with lock:
                # For each completed asset, find datapoints that need it
                for asset in assets:
                    if asset in asset_to_datapoints:
                        # Get all datapoints waiting for this asset
                        for idx in list(asset_to_datapoints[asset]):
                            if idx in datapoint_pending_count:
                                # Decrement the count
                                datapoint_pending_count[idx] -= 1

                                # If all assets are ready, mark for creation
                                if datapoint_pending_count[idx] == 0:
                                    ready_datapoints.append(idx)
                                    del datapoint_pending_count[idx]

                                # Remove this datapoint from this asset's waiting list
                                asset_to_datapoints[asset].discard(idx)

            # Submit ready datapoints for creation (outside lock to avoid blocking)
            for idx in ready_datapoints:

                def upload_and_update(dp_idx):
                    """Upload datapoint and update progress bar when done."""
                    try:
                        self.datapoint_uploader.upload_datapoint(
                            dataset_id=self.id,
                            datapoint=datapoints[dp_idx],
                            index=dp_idx,
                        )
                    finally:
                        datapoint_pbar.update(1)

                future = executor.submit(upload_and_update, idx)
                with lock:
                    creation_futures.append((idx, future))

            if ready_datapoints:
                logger.debug(
                    f"Asset batch completed, {len(ready_datapoints)} datapoints now ready for creation"
                )

        # 6. Start uploads (blocking, but triggers callbacks as assets complete)
        logger.info("Starting incremental datapoint creation")
        self.asset_orchestrator.upload_all_assets(
            datapoints, asset_completion_callback=on_assets_complete
        )

        # 7. Wait for all datapoint creation to complete
        executor.shutdown(wait=True)
        datapoint_pbar.close()
        logger.debug("All datapoint creation tasks completed")

        # 8. Collect results
        successful_uploads: list[Datapoint] = []
        failed_uploads: list[FailedUpload[Datapoint]] = []

        for idx, future in creation_futures:
            try:
                future.result()  # Raises exception if failed
                successful_uploads.append(datapoints[idx])
            except Exception as e:
                logger.warning(f"Failed to create datapoint {idx}: {e}")
                failed_uploads.append(
                    FailedUpload(
                        item=datapoints[idx],
                        error_type="DatapointCreationFailed",
                        error_message=str(e),
                    )
                )

        # 9. Handle datapoints whose assets failed to upload
        with lock:
            for idx in datapoint_pending_count:
                logger.warning(f"Datapoint {idx} assets failed to upload")
                failed_uploads.append(
                    FailedUpload(
                        item=datapoints[idx],
                        error_type="AssetUploadFailed",
                        error_message="One or more required assets failed to upload",
                    )
                )

        logger.info(
            f"Datapoint creation complete: {len(successful_uploads)} succeeded, {len(failed_uploads)} failed"
        )
        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
