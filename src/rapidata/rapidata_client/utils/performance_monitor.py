"""Performance monitoring for batch-level upload metrics."""

import time
from typing import Optional


class PerformanceMonitor:
    """
    Tracks upload performance metrics for a single batch.

    This class monitors success/failure rates and throughput to inform
    dynamic worker adjustment decisions.
    """

    def __init__(self, total_items: int):
        """
        Initialize the performance monitor for a batch.

        Args:
            total_items: Total number of items in this batch.
        """
        self.total_items = total_items
        self.success_count = 0
        self.error_count = 0
        self.start_time = time.time()
        self.end_time: Optional[float] = None

    def record_completion(self, success: bool) -> None:
        """
        Record the completion of a single item upload.

        Args:
            success: True if the upload succeeded, False if it failed.
        """
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def finish_batch(self) -> None:
        """Mark the batch as complete and record the end time."""
        self.end_time = time.time()

    def get_throughput(self) -> float:
        """
        Calculate successful items per second.

        Returns:
            Throughput in items/second. Returns 0 if batch not finished or duration is 0.
        """
        if self.end_time is None:
            return 0.0

        duration = self.end_time - self.start_time
        if duration <= 0:
            return 0.0

        return self.success_count / duration

    def get_error_rate(self) -> float:
        """
        Calculate the error rate as a fraction.

        Returns:
            Error rate between 0.0 and 1.0. Returns 0 if no items processed.
        """
        total_processed = self.success_count + self.error_count
        if total_processed == 0:
            return 0.0

        return self.error_count / total_processed

    def get_duration(self) -> float:
        """
        Get the batch duration in seconds.

        Returns:
            Duration in seconds. Returns 0 if batch not finished.
        """
        if self.end_time is None:
            return 0.0

        return self.end_time - self.start_time

    def reset(self) -> None:
        """Reset the monitor for a new batch (keeps total_items)."""
        self.success_count = 0
        self.error_count = 0
        self.start_time = time.time()
        self.end_time = None
