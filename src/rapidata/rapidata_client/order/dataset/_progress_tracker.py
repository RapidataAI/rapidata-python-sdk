import threading
import time
from tqdm import tqdm

from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, rapidata_config


class ProgressTracker:
    """
    Track dataset upload progress in a background thread with shallow indentation.

    This class encapsulates the progress polling loop to keep methods in
    `RapidataDataset` simpler and below the maximum indentation depth.
    """

    def __init__(
        self,
        dataset_id: str,
        openapi_service: OpenAPIService,
        total_uploads: int,
        progress_poll_interval: float,
    ) -> None:
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.total_uploads = total_uploads
        self.progress_poll_interval = progress_poll_interval

    def _get_progress_or_none(self):
        try:
            return self.openapi_service.dataset_api.dataset_dataset_id_progress_get(
                self.dataset_id
            )
        except Exception:  # noqa: BLE001
            return None

    def run(self) -> None:
        try:
            with tqdm(
                total=self.total_uploads,
                desc="Uploading datapoints",
                disable=rapidata_config.logging.silent_mode,
            ) as pbar:
                while True:
                    current_progress = self._get_progress_or_none()
                    if current_progress is None:
                        time.sleep(self.progress_poll_interval)
                        continue

                    total_completed = current_progress.ready + current_progress.failed

                    pbar.n = total_completed
                    pbar.refresh()

                    time.sleep(self.progress_poll_interval)
                    if total_completed >= self.total_uploads:
                        break

                pbar.close()

                logger.info(
                    "Upload complete: %s ready, %s failed (%s%% success rate)",
                    current_progress.ready,
                    current_progress.failed,
                    (
                        (current_progress.ready / self.total_uploads * 100)
                        if self.total_uploads > 0
                        else 0
                    ),
                )
        except Exception as e:  # noqa: BLE001
            logger.error("Progress tracking thread error: %s", str(e))
            raise RuntimeError("Progress tracking failed, aborting uploads")

    def create_thread(self) -> threading.Thread:
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        return thread
