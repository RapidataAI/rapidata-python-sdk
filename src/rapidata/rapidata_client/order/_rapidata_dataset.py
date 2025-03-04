from itertools import zip_longest

from rapidata.api_client.models.datapoint_metadata_model import DatapointMetadataModel
from rapidata.api_client.models.create_datapoint_from_urls_model import (
    CreateDatapointFromUrlsModelMetadataInner,
)
from rapidata.api_client.models.create_datapoint_from_urls_model import CreateDatapointFromUrlsModel
from rapidata.api_client.models.upload_text_sources_to_dataset_model import (
    UploadTextSourcesToDatasetModel,
)
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.rapidata_client.assets import TextAsset, MediaAsset, MultiAsset
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from pydantic import StrictBytes, StrictStr
from typing import Optional, cast, Sequence, Generator, Any
from logging import Logger
from requests.adapters import HTTPAdapter, Retry
import time
import requests
import threading


def chunk_list(lst: list, chunk_size: int) -> Generator:
    """Split list into chunks to prevent resource exhaustion"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()
        self._logger = Logger(__name__)

    def _add_texts(
        self,
        text_assets: list[TextAsset] | list[MultiAsset],
        max_workers: int = 10,
    ):
        for text_asset in text_assets:
            if isinstance(text_asset, MultiAsset):
                assert all(
                    isinstance(asset, TextAsset) for asset in text_asset.assets
                ), "All assets in a MultiAsset must be of type TextAsset."

        def upload_text_datapoint(text_asset: TextAsset | MultiAsset, index: int) -> None:
            if isinstance(text_asset, TextAsset):
                texts = [text_asset.text]
            elif isinstance(text_asset, MultiAsset):
                texts = [asset.text for asset in text_asset.assets if isinstance(asset, TextAsset)]
            else:
                raise ValueError(f"Unsupported asset type: {type(text_asset)}")

            model = UploadTextSourcesToDatasetModel(
                datasetId=self.dataset_id,
                textSources=texts,
                sortIndex=index,
            )

            upload_response = self.openapi_service.dataset_api.dataset_creat_text_datapoint_post(model)

            if upload_response.errors:
                raise ValueError(f"Error uploading text datapoint: {upload_response.errors}")

        total_uploads = len(text_assets)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_text_datapoint, text_asset, index=i)
                for i, text_asset in enumerate(text_assets)
            ]

            with tqdm(total=total_uploads, desc="Uploading text datapoints") as pbar:
                for future in as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred during execution
                    pbar.update(1)

    def _create_session_with_retries(self, max_workers: int, max_retries: int) -> requests.Session:
        """
        Create and configure a requests session with retry logic.
        
        Args:
            max_workers: Maximum number of concurrent workers
            max_retries: Maximum number of retry attempts per failed request
            
        Returns:
            requests.Session: Configured session with retry logic
        """
        session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            pool_connections=max_workers * 2,
            pool_maxsize=max_workers * 4,
            max_retries=retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session

    def _process_single_upload(
        self,
        media_asset: MediaAsset | MultiAsset, 
        meta: Metadata | None, 
        index: int,
        session: requests.Session
    ) -> tuple[list[str], list[str]]:
        """
        Process single upload with error tracking.
        
        Args:
            media_asset: MediaAsset or MultiAsset to upload
            meta: Optional metadata for the asset
            index: Sort index for the upload
            session: Requests session for HTTP requests
            
        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed identifiers
        """
        local_successful: list[str] = []
        local_failed: list[str] = []
        identifiers_to_track: list[str] = []
        
        try:
            # Get identifier for this upload (URL or file path)
            if isinstance(media_asset, MediaAsset):
                media_asset.session = session
                assets = [media_asset]
                identifier = media_asset._url if media_asset._url else media_asset.path
                identifiers_to_track = [identifier] if identifier else []
            elif isinstance(media_asset, MultiAsset):
                assets = cast(list[MediaAsset], media_asset.assets)
                for asset in assets:
                    asset.session = session
                identifiers_to_track: list[str] = [
                    (asset._url if asset._url else cast(str, asset.path)) 
                    for asset in assets
                ]
            else:
                raise ValueError(f"Unsupported asset type: {type(media_asset)}")

            meta_model = meta.to_model() if meta else None

            local_paths: bool = assets[0].is_local()
            files: list[StrictStr] = []
            for asset in assets:
                if isinstance(asset, MediaAsset):
                    files.append(asset.path)

            if local_paths:
                model = DatapointMetadataModel(
                    datasetId=self.dataset_id,
                    metadata=([CreateDatapointFromUrlsModelMetadataInner(meta_model)] if meta_model else []),
                    sortIndex=index,
                )
                upload_response = self.openapi_service.dataset_api.dataset_create_datapoint_post(
                    model=model,
                    files=files # type: ignore
                )
            else:
                upload_response = self.openapi_service.dataset_api.dataset_dataset_id_datapoints_urls_post(
                    dataset_id=self.dataset_id,
                    create_datapoint_from_urls_model=CreateDatapointFromUrlsModel(urls=files),
                )
                
            if upload_response.errors:
                error_msg = f"Error uploading datapoint: {upload_response.errors}"
                self._logger.error(error_msg)
                local_failed.extend(identifiers_to_track)
                raise ValueError(error_msg)

            local_successful.extend(identifiers_to_track)

        except Exception as e:
            self._logger.error(f"\nUpload failed for {identifiers_to_track}: {str(e)}") # \n to avoid same line as tqdm
            local_failed.extend(identifiers_to_track)

        return local_successful, local_failed

    def _get_progress_tracker(
        self, 
        total_uploads: int, 
        initial_ready: int, 
        initial_progress: Any, 
        stop_event: threading.Event, 
        progress_error_event: threading.Event,
        progress_poll_interval: float,
        progress_timeout: int
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
            progress_timeout: Maximum time to wait for progress
            
        Returns:
            threading.Thread: The progress tracking thread
        """
        def progress_tracking_thread():
            try:
                # Initialize progress bar with 0 completions
                with tqdm(total=total_uploads, desc="Uploading datapoints") as pbar:
                    prev_ready = initial_ready
                    prev_failed = initial_progress.failed or 0
                    stall_count = 0
                    start_time = time.time()
                    last_progress_time = start_time
                    
                    # We'll wait for all uploads to finish + some extra time
                    # for the backend to fully process everything
                    all_uploads_complete = threading.Event()
                    
                    while not stop_event.is_set() or not all_uploads_complete.is_set():
                        try:
                            current_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.dataset_id)
                            
                            # Calculate items completed since our initialization
                            completed_ready = current_progress.ready - initial_ready
                            completed_failed = (current_progress.failed or 0) - (initial_progress.failed or 0)
                            total_completed = completed_ready + completed_failed
                            
                            # Calculate newly completed items since our last check
                            new_ready = current_progress.ready - prev_ready
                            new_failed = (current_progress.failed or 0) - prev_failed
                            
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
                                        self._logger.warning(f"Progress seems stalled at {total_completed}/{total_uploads}. Completing progress bar.")
                                        pbar.n = total_uploads  # Force to 100%
                                        pbar.refresh()
                                        all_uploads_complete.set()
                                        break
                            
                            # Check for overall timeout
                            if time.time() - start_time > progress_timeout:
                                self._logger.warning(f"Progress tracking timed out after {progress_timeout} seconds")
                                # Force to 100% on timeout
                                pbar.n = total_uploads
                                pbar.refresh()
                                all_uploads_complete.set()
                                break
                                
                        except Exception as e:
                            self._logger.error(f"Error checking progress: {str(e)}")
                            stall_count += 1
                            
                            if stall_count > 10:  # Too many consecutive errors
                                progress_error_event.set()
                                break
                        
                        # Sleep before next poll
                        time.sleep(progress_poll_interval)
                
            except Exception as e:
                self._logger.error(f"Progress tracking thread error: {str(e)}")
                progress_error_event.set()
                
        # Create and return the thread
        progress_thread = threading.Thread(target=progress_tracking_thread)
        progress_thread.daemon = True
        return progress_thread

    def _process_uploads_in_chunks(
        self,
        media_paths: list[MediaAsset] | list[MultiAsset],
        metadata: Sequence[Metadata] | None,
        session: requests.Session,
        max_workers: int,
        chunk_size: int,
        stop_progress_tracking: threading.Event,
        progress_tracking_error: threading.Event
    ) -> tuple[list[str], list[str]]:
        """
        Process uploads in chunks with a ThreadPoolExecutor.
        
        Args:
            media_paths: List of assets to upload
            metadata: Optional sequence of metadata
            session: Requests session for HTTP requests
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
                    chunk_metadata = metadata[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size] if metadata else None
                    
                    futures = [
                        executor.submit(
                            self._process_single_upload, 
                            media_asset, 
                            meta, 
                            index=(chunk_idx * chunk_size + i),
                            session=session
                        )
                        for i, (media_asset, meta) in enumerate(zip_longest(chunk, chunk_metadata or []))
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
                            self._logger.error(f"Future execution failed: {str(e)}")
        finally:
            # Signal to the progress tracking thread that all uploads have been submitted
            stop_progress_tracking.set()
                
        return successful_uploads, failed_uploads



    def _log_final_progress(
        self, 
        total_uploads: int, 
        initial_ready: int, 
        initial_progress: Any, 
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
            # Wait a bit for the final counts to stabilize
            time.sleep(2 * progress_poll_interval)
            
            # Get final progress
            final_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.dataset_id)
            total_ready = final_progress.ready - initial_ready
            total_failed = final_progress.failed - (initial_progress.failed or 0)
            
            # Make sure we account for all uploads
            if total_ready + total_failed < total_uploads:
                # Try one more time after a longer wait
                time.sleep(5 * progress_poll_interval)
                final_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.dataset_id)
                total_ready = final_progress.ready - initial_ready
                total_failed = final_progress.failed - (initial_progress.failed or 0)
            
            success_rate = (total_ready / total_uploads * 100) if total_uploads > 0 else 0
            
            self._logger.info(f"Upload complete: {total_ready} ready, {total_failed} failed ({success_rate:.1f}% success rate)")
            print(f"Upload complete, {total_ready} ready, {total_failed} failed ({success_rate:.1f}% success rate)")
        except Exception as e:
            self._logger.error(f"Error getting final progress: {str(e)}")
            self._logger.info(f"Upload summary from local tracking: {len(successful_uploads)} succeeded, {len(failed_uploads)} failed")

        if failed_uploads:
            print(f"Failed uploads: {failed_uploads}")

    def _add_media_from_paths(
        self,
        media_paths: list[MediaAsset] | list[MultiAsset],
        metadata: Sequence[Metadata] | None = None,
        max_workers: int = 10,
        max_retries: int = 5,
        chunk_size: int = 50,
        progress_poll_interval: float = 0.5,
        progress_timeout: int = 300,  # 5 minutes timeout for progress
    ) -> tuple[list[str], list[str]]:
        """
        Upload media paths in chunks with managed resources.
        
        Args:
            media_paths: List of MediaAsset or MultiAsset objects to upload
            metadata: Optional sequence of metadata matching media_paths length
            max_workers: Maximum number of concurrent upload workers
            max_retries: Maximum number of retry attempts per failed request
            chunk_size: Number of items to process in each batch
            progress_poll_interval: Time in seconds between progress checks
            progress_timeout: Maximum time in seconds to wait for progress to complete
            
        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed URLs
            
        Raises:
            ValueError: If metadata length doesn't match media_paths length
        """
        if metadata is not None and len(metadata) != len(media_paths):
            raise ValueError("metadata must be None or have the same length as media_paths")

        # Configure session with retry logic
        session = self._create_session_with_retries(max_workers, max_retries)

        # Get initial progress state
        initial_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(self.dataset_id)
        initial_ready = initial_progress.ready
        
        # Setup tracking variables
        total_uploads = len(media_paths)
        
        # Create thread control events
        stop_progress_tracking = threading.Event()
        progress_tracking_error = threading.Event()
        
        # Create and start progress tracking thread
        progress_thread = self._get_progress_tracker(
            total_uploads, 
            initial_ready, 
            initial_progress, 
            stop_progress_tracking, 
            progress_tracking_error,
            progress_poll_interval,
            progress_timeout
        )
        progress_thread.start()
        
        # Process uploads in chunks
        try:
            successful_uploads, failed_uploads = self._process_uploads_in_chunks(
                media_paths,
                metadata,
                session,
                max_workers,
                chunk_size,
                stop_progress_tracking,
                progress_tracking_error
            )
        finally:
            # Wait for progress thread to finish naturally
            # It will exit after either finishing all processing or timeout
            progress_thread.join(timeout=progress_timeout + 10)  # Add margin to the timeout
        
        # Log final progress
        self._log_final_progress(
            total_uploads, 
            initial_ready, 
            initial_progress, 
            progress_poll_interval,
            successful_uploads,
            failed_uploads
        )

        return successful_uploads, failed_uploads
