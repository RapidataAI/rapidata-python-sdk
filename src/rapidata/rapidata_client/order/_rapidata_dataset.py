from itertools import zip_longest

from rapidata.api_client.models.create_datapoint_from_text_sources_model import CreateDatapointFromTextSourcesModel
from rapidata.api_client.models.dataset_dataset_id_datapoints_post_request_metadata_inner import DatasetDatasetIdDatapointsPostRequestMetadataInner
from rapidata.rapidata_client.datapoints.datapoint import Datapoint
from rapidata.rapidata_client.datapoints.metadata import Metadata
from rapidata.rapidata_client.datapoints.assets import TextAsset, MediaAsset, MultiAsset, BaseAsset
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

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        if not datapoints:
            return [], []
        
        effective_asset_type = datapoints[0]._get_effective_asset_type()
        
        if issubclass(effective_asset_type, MediaAsset):
            return self._add_media_from_paths(datapoints)
        elif issubclass(effective_asset_type, TextAsset):
            return self._add_texts(datapoints)
        else:
            raise ValueError(f"Unsupported asset type: {effective_asset_type}")

    def _add_texts(
        self,
        datapoints: list[Datapoint],
        max_workers: int = 10,
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        
        def upload_text_datapoint(datapoint: Datapoint, index: int) -> Datapoint:
            model = datapoint.create_text_upload_model(index)
            
            self.openapi_service.dataset_api.dataset_dataset_id_datapoints_texts_post(dataset_id=self.id, create_datapoint_from_text_sources_model=model)
            return datapoint

        successful_uploads: list[Datapoint] = []
        failed_uploads: list[Datapoint] = []

        total_uploads = len(datapoints)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_datapoint = {
                executor.submit(upload_text_datapoint, datapoint, index=i): datapoint
                for i, datapoint in enumerate(datapoints)
            }

            with tqdm(total=total_uploads, desc="Uploading text datapoints", disable=RapidataOutputManager.silent_mode) as pbar:
                for future in as_completed(future_to_datapoint.keys()):
                    datapoint = future_to_datapoint[future]
                    try:
                        result = future.result()
                        pbar.update(1)
                        successful_uploads.append(result)
                    except Exception as e:
                        failed_uploads.append(datapoint)
                        logger.error(f"Upload failed for {datapoint}: {str(e)}")

        return successful_uploads, failed_uploads

    def _process_single_upload(
        self,
        datapoint: Datapoint,
        index: int,
        max_retries: int = 3,
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Process single upload with retry logic and error tracking.
        
        Args:
            media_asset: MediaAsset or MultiAsset to upload
            meta_list: Optional sequence of metadata for the asset
            index: Sort index for the upload
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            tuple[list[Datapoint], list[Datapoint]]: Lists of successful and failed datapoints
        """
        local_successful: list[Datapoint] = []
        local_failed: list[Datapoint] = []

        metadata = datapoint.get_prepared_metadata()

        local_paths = datapoint.get_local_file_paths()
        urls = datapoint.get_urls()

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
                
                local_successful.append(datapoint)

                return local_successful, local_failed
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 1s, then 2s, then 4s
                    retry_delay = 2 ** attempt
                    time.sleep(retry_delay)
                    managed_print(f"\nRetrying {attempt + 1} of {max_retries}...\n")
                    
        # If we get here, all retries failed
        local_failed.append(datapoint)
        logger.error(f"\nUpload failed for {datapoint} after {max_retries} attempts. Final error: {str(last_exception)}")

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
        datapoints: list[Datapoint],
        max_workers: int,
        chunk_size: int,
        stop_progress_tracking: threading.Event,
        progress_tracking_error: threading.Event
    ) -> tuple[list[Datapoint], list[Datapoint]]:
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
        successful_uploads: list[Datapoint] = []
        failed_uploads: list[Datapoint] = []
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Process uploads in chunks to avoid overwhelming the system
                for chunk_idx, chunk in enumerate(chunk_list(datapoints, chunk_size)):
                    futures = [
                        executor.submit(
                            self._process_single_upload, 
                            datapoint, 
                            index=(chunk_idx * chunk_size + i)
                        )
                        for i, datapoint in enumerate(chunk)
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
        successful_uploads: list[Datapoint],
        failed_uploads: list[Datapoint]
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
        datapoints: list[Datapoint],
        max_workers: int = 10,
        chunk_size: int = 50,
        progress_poll_interval: float = 0.5,
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Upload media paths in chunks with managed resources.
        
        Args:
            datapoints: List of Datapoint objects to upload
            max_workers: Maximum number of concurrent upload workers
            chunk_size: Number of items to process in each batch
            progress_poll_interval: Time in seconds between progress checks
            
        Returns:
            tuple[list[Datapoint], list[Datapoint]]: Lists of successful and failed datapoints
            
        Raises:
            ValueError: If multi_metadata lengths don't match media_paths length
        """
        
        # Setup tracking variables
        total_uploads = len(datapoints)
        
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
                datapoints,
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

        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()
