from itertools import zip_longest

from rapidata.api_client.models.create_datapoint_from_text_sources_model import CreateDatapointFromTextSourcesModel
from rapidata.api_client.models.dataset_dataset_id_datapoints_post_request_metadata_inner import DatasetDatasetIdDatapointsPostRequestMetadataInner
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.rapidata_client.assets import TextAsset, MediaAsset, MultiAsset, BaseAsset
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from typing import cast, Sequence, Generator
from rapidata.rapidata_client.logging import logger, managed_print, RapidataOutputManager
import time
import threading


def chunk_list(lst: list, chunk_size: int) -> Generator:
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()

    def _get_effective_asset_type(self, datapoints: Sequence[BaseAsset]) -> type:
        if not datapoints:
            raise ValueError("Cannot determine asset type from empty datapoints list.")
            
        first_item = datapoints[0]
        
        if isinstance(first_item, MultiAsset):
            if not first_item.assets:
                raise ValueError("MultiAsset cannot be empty.")
            return type(first_item.assets[0])
        
        return type(first_item)

    def _add_datapoints(
        self,
        datapoints: Sequence[BaseAsset],
        metadata_list: Sequence[Sequence[Metadata]] | None = None,
        max_workers: int = 10,
    ):
        effective_asset_type = self._get_effective_asset_type(datapoints)
        
        for item in datapoints:
            if isinstance(item, MultiAsset):
                if not all(isinstance(asset, effective_asset_type) for asset in item.assets):
                    raise ValueError("All MultiAssets must contain the same type of assets.")
            elif not isinstance(item, (MediaAsset, TextAsset, MultiAsset)):
                raise ValueError("All datapoints must be MediaAsset, TextAsset, or MultiAsset.")
        
        if issubclass(effective_asset_type, MediaAsset):
            media_datapoints = cast(list[MediaAsset] | list[MultiAsset], datapoints)
            self._add_media_from_paths(media_datapoints, metadata_list, max_workers)
        elif issubclass(effective_asset_type, TextAsset):
            text_datapoints = cast(list[TextAsset] | list[MultiAsset], datapoints)
            self._add_texts(text_datapoints, metadata_list)
        else:
            raise ValueError(f"Unsupported asset type: {effective_asset_type}")

    def _add_texts(
        self,
        text_assets: list[TextAsset] | list[MultiAsset],
        metadata_list: Sequence[Sequence[Metadata]] | None = None,
        max_workers: int = 10,
    ):
        for text_asset in text_assets:
            if isinstance(text_asset, MultiAsset):
                assert all(
                    isinstance(asset, TextAsset) for asset in text_asset.assets
                ), "All assets in a MultiAsset must be of type TextAsset."

        def upload_text_datapoint(text_asset: TextAsset | MultiAsset, metadata_per_datapoint: Sequence[Metadata] | None, index: int) -> None:
            if isinstance(text_asset, TextAsset):
                texts = [text_asset.text]
            elif isinstance(text_asset, MultiAsset):
                texts = [asset.text for asset in text_asset.assets if isinstance(asset, TextAsset)]
            else:
                raise ValueError(f"Unsupported asset type: {type(text_asset)}")
            
            metadata = []
            if metadata_per_datapoint:
                for meta in metadata_per_datapoint:
                    meta_model = meta.to_model() if meta else None
                    if meta_model:
                        metadata.append(DatasetDatasetIdDatapointsPostRequestMetadataInner(meta_model))

            model = CreateDatapointFromTextSourcesModel(
                textSources=texts,
                sortIndex=index,
                metadata=metadata,
            )

            self.openapi_service.dataset_api.dataset_dataset_id_datapoints_texts_post(dataset_id=self.id, create_datapoint_from_text_sources_model=model)

        total_uploads = len(text_assets)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_text_datapoint, text_asset, metadata, index=i)
                for i, (text_asset, metadata) in enumerate(zip_longest(text_assets, metadata_list or []))
            ]

            with tqdm(total=total_uploads, desc="Uploading text datapoints", disable=RapidataOutputManager.silent_mode) as pbar:
                for future in as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred during execution
                    pbar.update(1)

    def _process_single_upload(
        self,
        media_asset: MediaAsset | MultiAsset, 
        meta_list: Sequence[Metadata] | None, 
        index: int,
        max_retries: int = 3,
    ) -> tuple[list[str], list[str]]:
        """
        Process single upload with retry logic and error tracking.
        
        Args:
            media_asset: MediaAsset or MultiAsset to upload
            meta_list: Optional sequence of metadata for the asset
            index: Sort index for the upload
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed identifiers
        """
        local_successful: list[str] = []
        local_failed: list[str] = []
        identifiers_to_track: list[str] = []
        
        # Get identifier for this upload (URL or file path)
        if isinstance(media_asset, MediaAsset):
            assets = [media_asset]
            identifier = media_asset._url if media_asset._url else media_asset.path
            identifiers_to_track = [identifier] if identifier else []
        elif isinstance(media_asset, MultiAsset):
            assets = cast(list[MediaAsset], media_asset.assets)
            identifiers_to_track = [
                (asset._url if asset._url else cast(str, asset.path)) 
                for asset in assets
            ]
        else:
            raise ValueError(f"Unsupported asset type: {type(media_asset)}")

        metadata: list[DatasetDatasetIdDatapointsPostRequestMetadataInner] = []
        if meta_list:
            for meta in meta_list:
                meta_model = meta.to_model() if meta else None
                if meta_model:
                    metadata.append(DatasetDatasetIdDatapointsPostRequestMetadataInner(meta_model))

        local_paths = [asset.to_file() for asset in assets if asset.is_local()]
        urls = [asset.path for asset in assets if not asset.is_local()]

        last_exception = None
        for attempt in range(max_retries):
            try:
                self.openapi_service.dataset_api.dataset_dataset_id_datapoints_post(
                    dataset_id=self.id,
                    file=local_paths,
                    url=urls,
                    metadata=metadata,
                    sort_index=index,
                )
                
                # If we get here, the upload was successful
                local_successful.extend(identifiers_to_track)
                return local_successful, local_failed
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 1s, then 2s, then 4s
                    retry_delay = 2 ** attempt
                    time.sleep(retry_delay)
                    managed_print(f"\nRetrying {attempt + 1} of {max_retries}...\n")
                    
        # If we get here, all retries failed
        logger.error(f"\nUpload failed for {identifiers_to_track} after {max_retries} attempts. Final error: {str(last_exception)}")
        local_failed.extend(identifiers_to_track)

        return local_successful, local_failed

    def _get_progress_tracker(
        self, 
        total_uploads: int, 
        stop_event: threading.Event, 
        progress_error_event: threading.Event,
        progress_poll_interval: float,
    ) -> threading.Thread:
        """
        Create and return a progress tracking thread that shows actual API progress.
        
        Args:
            total_uploads: Total number of uploads to track
            initial_ready: Initial number of ready items
            initial_progress: Initial progress state
            stop_event: Event to signal thread to stop
            progress_error_event: Event to signal an error in progress tracking
            progress_poll_interval: Time between progress checks
            
        Returns:
            threading.Thread: The progress tracking thread
        """
        def progress_tracking_thread():
            try:
                # Initialize progress bar with 0 completions
                with tqdm(total=total_uploads, desc="Uploading datapoints", disable=RapidataOutputManager.silent_mode) as pbar:
                    prev_ready = 0
                    prev_failed = 0
                    stall_count = 0
                    last_progress_time = time.time()
                    
                    # We'll wait for all uploads to finish + some extra time
                    # for the backend to fully process everything
                    all_uploads_complete = threading.Event()
                    
                    while not stop_event.is_set() or not all_uploads_complete.is_set():
                        try:
                            current_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.id)
                            
                            # Calculate items completed since our initialization
                            completed_ready = current_progress.ready
                            completed_failed = current_progress.failed
                            total_completed = completed_ready + completed_failed
                            
                            # Calculate newly completed items since our last check
                            new_ready = current_progress.ready - prev_ready
                            new_failed = current_progress.failed - prev_failed
                            
                            # Update progress bar position to show actual completed items
                            # First reset to match the actual completed count
                            pbar.n = total_completed
                            pbar.refresh()
                            
                            if new_ready > 0 or new_failed > 0:
                                # We saw progress
                                stall_count = 0
                                last_progress_time = time.time()
                            else:
                                stall_count += 1
                            
                            # Update our tracking variables
                            prev_ready = current_progress.ready
                            prev_failed = current_progress.failed or 0
                            
                            # Check if stop_event was set (all uploads submitted)
                            if stop_event.is_set():
                                elapsed_since_last_progress = time.time() - last_progress_time
                                
                                # If we haven't seen progress for a while after all uploads were submitted
                                if elapsed_since_last_progress > 5.0:
                                    # If we're at 100%, we're done
                                    if total_completed >= total_uploads:
                                        all_uploads_complete.set()
                                        break
                                        
                                    # If we're not at 100% but it's been a while with no progress
                                    if stall_count > 5:
                                        # We've polled several times with no progress, assume we're done
                                        logger.warning(f"\nProgress seems stalled at {total_completed}/{total_uploads}. Please try again.")
                                        break
                                
                        except Exception as e:
                            logger.error(f"\nError checking progress: {str(e)}")
                            stall_count += 1
                            
                            if stall_count > 10:  # Too many consecutive errors
                                progress_error_event.set()
                                break
                        
                        # Sleep before next poll
                        time.sleep(progress_poll_interval)
                
            except Exception as e:
                logger.error(f"Progress tracking thread error: {str(e)}")
                progress_error_event.set()
                
        # Create and return the thread
        progress_thread = threading.Thread(target=progress_tracking_thread)
        progress_thread.daemon = True
        return progress_thread

    def _process_uploads_in_chunks(
        self,
        media_paths: list[MediaAsset] | list[MultiAsset],
        multi_metadata: Sequence[Sequence[Metadata]] | None,
        max_workers: int,
        chunk_size: int,
        stop_progress_tracking: threading.Event,
        progress_tracking_error: threading.Event
    ) -> tuple[list[str], list[str]]:
        """
        Process uploads in chunks with a ThreadPoolExecutor.
        
        Args:
            media_paths: List of assets to upload
            multi_metadata: Optional sequence of sequences of metadata
            max_workers: Maximum number of concurrent workers
            chunk_size: Number of items to process in each batch
            stop_progress_tracking: Event to signal progress tracking to stop
            progress_tracking_error: Event to detect progress tracking errors
            
        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed uploads
        """
        successful_uploads: list[str] = []
        failed_uploads: list[str] = []
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Process uploads in chunks to avoid overwhelming the system
                for chunk_idx, chunk in enumerate(chunk_list(media_paths, chunk_size)):
                    chunk_multi_metadata = multi_metadata[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size] if multi_metadata else None
                    
                    futures = [
                        executor.submit(
                            self._process_single_upload, 
                            media_asset, 
                            meta_list, 
                            index=(chunk_idx * chunk_size + i)
                        )
                        for i, (media_asset, meta_list) in enumerate(zip_longest(chunk, chunk_multi_metadata or []))
                    ]
                    
                    # Wait for this chunk to complete before starting the next one
                    for future in as_completed(futures):
                        if progress_tracking_error.is_set():
                            raise RuntimeError("Progress tracking failed, aborting uploads")
                            
                        try:
                            chunk_successful, chunk_failed = future.result()
                            successful_uploads.extend(chunk_successful)
                            failed_uploads.extend(chunk_failed)
                        except Exception as e:
                            logger.error(f"Future execution failed: {str(e)}")
        finally:
            # Signal to the progress tracking thread that all uploads have been submitted
            stop_progress_tracking.set()
                
        return successful_uploads, failed_uploads

    def _log_final_progress(
        self, 
        total_uploads: int, 
        progress_poll_interval: float,
        successful_uploads: list[str],
        failed_uploads: list[str]
    ) -> None:
        """
        Log the final progress of the upload operation.
        
        Args:
            total_uploads: Total number of uploads
            initial_ready: Initial number of ready items
            initial_progress: Initial progress state
            progress_poll_interval: Time between progress checks
            successful_uploads: List of successful uploads for fallback reporting
            failed_uploads: List of failed uploads for fallback reporting
        """
        try:            
            # Get final progress
            final_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.id)
            total_ready = final_progress.ready
            total_failed = final_progress.failed
            
            # Make sure we account for all uploads
            if total_ready + total_failed < total_uploads:
                # Try one more time after a longer wait
                time.sleep(5 * progress_poll_interval)
                final_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.id)
                total_ready = final_progress.ready
                total_failed = final_progress.failed
            
            success_rate = (total_ready / total_uploads * 100) if total_uploads > 0 else 0
            
            logger.info(f"Upload complete: {total_ready} ready, {total_uploads-total_ready} failed ({success_rate:.1f}% success rate)")
        except Exception as e:
            logger.error(f"Error getting final progress: {str(e)}")
            logger.info(f"Upload summary from local tracking: {len(successful_uploads)} succeeded, {len(failed_uploads)} failed")

        if failed_uploads:
            logger.error(f"Failed uploads: {failed_uploads}")

    def _add_media_from_paths(
        self,
        media_paths: list[MediaAsset] | list[MultiAsset],
        multi_metadata: Sequence[Sequence[Metadata]] | None = None,
        max_workers: int = 10,
        chunk_size: int = 50,
        progress_poll_interval: float = 0.5,
    ) -> tuple[list[str], list[str]]:
        """
        Upload media paths in chunks with managed resources.
        
        Args:
            media_paths: List of MediaAsset or MultiAsset objects to upload
            multi_metadata: Optional sequence of sequences of metadata matching media_paths length
            max_workers: Maximum number of concurrent upload workers
            chunk_size: Number of items to process in each batch
            progress_poll_interval: Time in seconds between progress checks
            
        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed URLs
            
        Raises:
            ValueError: If multi_metadata lengths don't match media_paths length
        """

        if multi_metadata and not len(multi_metadata) == len(media_paths):
            raise ValueError("The number of assets must match the number of metadatas.")
        
        if multi_metadata and not all(len(data) == len(multi_metadata[0]) for data in multi_metadata):
            raise ValueError("All metadatas must have the same length.")
        
        # Setup tracking variables
        total_uploads = len(media_paths)
        
        # Create thread control events
        stop_progress_tracking = threading.Event()
        progress_tracking_error = threading.Event()
        
        # Create and start progress tracking thread
        progress_thread = self._get_progress_tracker(
            total_uploads, 
            stop_progress_tracking, 
            progress_tracking_error,
            progress_poll_interval
        )
        progress_thread.start()
        
        # Process uploads in chunks
        try:
            successful_uploads, failed_uploads = self._process_uploads_in_chunks(
                media_paths,
                multi_metadata,
                max_workers,
                chunk_size,
                stop_progress_tracking,
                progress_tracking_error
            )
        finally:
            progress_thread.join(10)  # Add margin to the timeout for tqdm
        
        # Log final progress
        self._log_final_progress(
            total_uploads, 
            progress_poll_interval,
            successful_uploads,
            failed_uploads
        )

        if failed_uploads:
            raise RuntimeError(f"Upload failed for {failed_uploads}")

        return successful_uploads, failed_uploads
