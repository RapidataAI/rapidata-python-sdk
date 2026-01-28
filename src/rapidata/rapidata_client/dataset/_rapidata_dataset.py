"""
RapidataDataset module for managing datapoint uploads with incremental asset processing.

Threading Model:
---------------
This module uses concurrent processing for both asset uploads and datapoint creation:

1. Asset Upload Phase (Step 1/2):
   - URLs are uploaded in batches with polling for completion
   - Files are uploaded in parallel using ThreadPoolExecutor
   - Completion callbacks are invoked from worker threads

2. Datapoint Creation Phase (Step 2/2):
   - Datapoints are created incrementally as their required assets complete
   - Uses ThreadPoolExecutor with max_workers=rapidata_config.upload.maxWorkers
   - Callbacks from asset upload trigger datapoint creation submissions

Thread-Safety:
-------------
- `lock` (threading.Lock): Protects all shared state during incremental processing
  - `datapoint_pending_count`: Maps datapoint index to remaining asset count
  - `asset_to_datapoints`: Maps asset to set of datapoint indices waiting for it
  - `creation_futures`: List of (idx, Future) tuples for datapoint creation tasks

Lock Acquisition Order:
----------------------
1. `on_assets_complete` callback acquires lock to update shared state
2. Lock is released before submitting datapoint creation tasks to avoid blocking
3. Lock is re-acquired briefly to append futures to creation_futures list

The callback-based design ensures:
- Assets can complete incrementally (batch-by-batch, file-by-file)
- Datapoints are created as soon as all their assets are ready
- No deadlocks occur between asset completion and datapoint submission
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable

from tqdm.auto import tqdm

from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._datapoint_uploader import DatapointUploader
from rapidata.rapidata_client.datapoints._asset_upload_orchestrator import (
    AssetUploadOrchestrator,
    extract_assets_from_datapoint,
)
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.config import rapidata_config, logger


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService) -> None:
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
        """
        if not datapoints:
            return [], []

        # 1. Build asset-to-datapoint mappings
        asset_to_datapoints, datapoint_pending_count = (
            self._build_asset_to_datapoint_mapping(datapoints)
        )

        # 2. Set up shared state for incremental creation
        creation_futures: list[tuple[int, Future]] = []
        lock = threading.Lock()
        executor = ThreadPoolExecutor(max_workers=rapidata_config.upload.maxWorkers)

        # 3. Execute uploads and incremental datapoint creation
        self._execute_incremental_creation(
            datapoints,
            asset_to_datapoints,
            datapoint_pending_count,
            creation_futures,
            lock,
            executor,
        )

        # 4. Collect and return results
        return self._collect_and_return_results(
            datapoints, creation_futures, datapoint_pending_count, lock
        )

    def _build_asset_to_datapoint_mapping(
        self, datapoints: list[Datapoint]
    ) -> tuple[dict[str, set[int]], dict[int, int]]:
        """
        Build efficient reverse mapping: asset -> datapoint indices that need it.
        This allows O(1) lookup instead of checking all pending datapoints.

        Note on using indices: We use integer indices instead of datapoint objects because:
        - Indices are hashable (required for dict keys and sets)
        - Lightweight and fast to compare
        - Provides stable references to datapoints in the list
        - The datapoint objects remain in a single location (the datapoints list)

        Args:
            datapoints: List of datapoints to process. Indices into this list are used as identifiers.

        Returns:
            Tuple of (asset_to_datapoints, datapoint_pending_count):
                - asset_to_datapoints: Maps each asset to set of datapoint indices (positions in datapoints list) that need it
                - datapoint_pending_count: Maps each datapoint index to count of remaining assets it needs
        """
        # Using indices instead of datapoints directly for hashability and performance
        asset_to_datapoints: dict[str, set[int]] = {}
        datapoint_pending_count: dict[int, int] = {}

        for idx, dp in enumerate(datapoints):
            # Extract all assets for this datapoint using shared utility
            assets = extract_assets_from_datapoint(dp)

            # Track how many assets this datapoint needs
            datapoint_pending_count[idx] = len(assets)

            # Build reverse mapping
            for asset in assets:
                if asset not in asset_to_datapoints:
                    asset_to_datapoints[asset] = set()
                asset_to_datapoints[asset].add(idx)

        logger.debug(f"Mapped {len(datapoints)} datapoints to their required assets")
        return asset_to_datapoints, datapoint_pending_count

    def _execute_incremental_creation(
        self,
        datapoints: list[Datapoint],
        asset_to_datapoints: dict[str, set[int]],
        datapoint_pending_count: dict[int, int],
        creation_futures: list[tuple[int, Future]],
        lock: threading.Lock,
        executor: ThreadPoolExecutor,
    ) -> None:
        """
        Execute asset uploads and incremental datapoint creation.

        Args:
            datapoints: List of datapoints being processed.
            asset_to_datapoints: Mapping from asset to datapoint indices.
            datapoint_pending_count: Pending asset count per datapoint.
            creation_futures: List to store creation futures.
            lock: Lock protecting shared state.
            executor: Thread pool executor for datapoint creation.
        """
        # Create progress bar for datapoint creation
        datapoint_pbar = tqdm(
            total=len(datapoints),
            desc="Step 2/2: Creating datapoints",
            position=1,
            disable=rapidata_config.logging.silent_mode,
            leave=True,
        )

        try:
            # Create callback that submits datapoints for creation
            on_assets_complete = self._create_asset_completion_callback(
                datapoints,
                asset_to_datapoints,
                datapoint_pending_count,
                creation_futures,
                lock,
                executor,
                datapoint_pbar,
            )

            # Extract all unique assets from the mapping
            all_assets = set(asset_to_datapoints.keys())

            # Start uploads (blocking, but triggers callbacks as assets complete)
            logger.info("Starting incremental datapoint creation")
            asset_failures = self.asset_orchestrator.upload_all_assets(
                all_assets, asset_completion_callback=on_assets_complete
            )

            if asset_failures:
                logger.warning(
                    f"{len(asset_failures)} asset(s) failed to upload, affected datapoints will be marked as failed"
                )

            # Wait for all datapoint creation to complete
            executor.shutdown(wait=True)
            logger.debug("All datapoint creation tasks completed")
        finally:
            # Always close progress bar, even on exception
            datapoint_pbar.close()

    def _create_asset_completion_callback(
        self,
        datapoints: list[Datapoint],
        asset_to_datapoints: dict[str, set[int]],
        datapoint_pending_count: dict[int, int],
        creation_futures: list[tuple[int, Future]],
        lock: threading.Lock,
        executor: ThreadPoolExecutor,
        datapoint_pbar: tqdm,
    ) -> Callable[[list[str]], None]:
        """
        Create callback function that handles asset completion.

        THREAD-SAFETY: The returned callback is invoked from worker threads during asset upload.
        All access to shared state is protected by the lock.

        Args:
            datapoints: List of datapoints being processed.
            asset_to_datapoints: Mapping from asset to datapoint indices.
            datapoint_pending_count: Pending asset count per datapoint.
            creation_futures: List to store creation futures.
            lock: Lock protecting shared state.
            executor: Thread pool executor for datapoint creation.
            datapoint_pbar: Progress bar for datapoint creation.

        Returns:
            Callback function to be invoked when assets complete.
        """

        def on_assets_complete(assets: list[str]) -> None:
            """Called when a batch of assets completes uploading."""
            ready_datapoint_indices = self._find_ready_datapoints(
                assets, asset_to_datapoints, datapoint_pending_count, lock
            )

            # Submit ready datapoints for creation (outside lock to avoid blocking)
            self._submit_datapoints_for_creation(
                ready_datapoint_indices,
                datapoints,
                creation_futures,
                lock,
                executor,
                datapoint_pbar,
            )

        return on_assets_complete

    def _find_ready_datapoints(
        self,
        assets: list[str],
        asset_to_datapoints: dict[str, set[int]],
        datapoint_pending_count: dict[int, int],
        lock: threading.Lock,
    ) -> list[int]:
        """
        Find datapoints that are ready for creation after asset completion.

        Returns indices into the original datapoints list for datapoints whose
        assets are now all complete.

        Args:
            assets: List of completed assets.
            asset_to_datapoints: Mapping from asset to datapoint indices.
            datapoint_pending_count: Pending asset count per datapoint index.
            lock: Lock protecting shared state.

        Returns:
            List of datapoint indices (positions in the datapoints list) ready for creation.
        """
        ready_datapoint_indices = []

        with lock:
            # For each completed asset, find datapoints that need it
            for asset in assets:
                if asset in asset_to_datapoints:
                    # Get all datapoint indices waiting for this asset
                    for datapoint_idx in list(asset_to_datapoints[asset]):
                        if datapoint_idx in datapoint_pending_count:
                            # Decrement the remaining asset count for this datapoint
                            datapoint_pending_count[datapoint_idx] -= 1

                            # If all assets are now ready, mark this datapoint for creation
                            if datapoint_pending_count[datapoint_idx] == 0:
                                ready_datapoint_indices.append(datapoint_idx)
                                del datapoint_pending_count[datapoint_idx]

                            # Remove this datapoint from this asset's waiting list
                            asset_to_datapoints[asset].discard(datapoint_idx)

        return ready_datapoint_indices

    def _submit_datapoints_for_creation(
        self,
        ready_datapoint_indices: list[int],
        datapoints: list[Datapoint],
        creation_futures: list[tuple[int, Future]],
        lock: threading.Lock,
        executor: ThreadPoolExecutor,
        datapoint_pbar: tqdm,
    ) -> None:
        """
        Submit ready datapoints for creation.

        Args:
            ready_datapoint_indices: Indices (positions in datapoints list) of datapoints ready for creation.
            datapoints: List of all datapoints (indexed by ready_datapoint_indices).
            creation_futures: List to store creation futures.
            lock: Lock protecting creation_futures.
            executor: Thread pool executor for datapoint creation.
            datapoint_pbar: Progress bar for datapoint creation.
        """
        for datapoint_idx in ready_datapoint_indices:

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

            future = executor.submit(upload_and_update, datapoint_idx)
            with lock:
                creation_futures.append((datapoint_idx, future))

        if ready_datapoint_indices:
            logger.debug(
                f"Asset batch completed, {len(ready_datapoint_indices)} datapoints now ready for creation"
            )

    def _collect_and_return_results(
        self,
        datapoints: list[Datapoint],
        creation_futures: list[tuple[int, Future]],
        datapoint_pending_count: dict[int, int],
        lock: threading.Lock,
    ) -> tuple[list[Datapoint], list[FailedUpload[Datapoint]]]:
        """
        Collect results from datapoint creation tasks.

        Args:
            datapoints: List of all datapoints.
            creation_futures: List of creation futures.
            datapoint_pending_count: Datapoints whose assets failed.
            lock: Lock protecting datapoint_pending_count.

        Returns:
            Tuple of (successful_uploads, failed_uploads).
        """
        successful_uploads: list[Datapoint] = []
        failed_uploads: list[FailedUpload[Datapoint]] = []

        # Collect results from creation tasks
        for idx, future in creation_futures:
            try:
                future.result()  # Raises exception if failed
                successful_uploads.append(datapoints[idx])
            except Exception as e:
                logger.warning(f"Failed to create datapoint {idx}: {e}")
                # Use from_exception to extract proper error reason from RapidataError
                failed_uploads.append(FailedUpload.from_exception(datapoints[idx], e))

        # Handle datapoints whose assets failed to upload
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
