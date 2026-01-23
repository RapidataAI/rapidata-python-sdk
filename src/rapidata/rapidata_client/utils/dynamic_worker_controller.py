"""Dynamic worker controller using conservative AIMD algorithm."""

import os
from typing import Optional, TYPE_CHECKING

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.utils.performance_monitor import PerformanceMonitor
from rapidata.rapidata_client.utils.worker_config_persistence import (
    WorkerConfigPersistence,
)

if TYPE_CHECKING:
    from rapidata.rapidata_client.config.upload_config import UploadConfig


class DynamicWorkerController:
    """
    Controls worker count using adaptive AIMD algorithm.

    Uses Additive Increase / Multiplicative Decrease (AIMD) to find
    optimal worker count based on real-time performance monitoring.
    This is the same proven algorithm used in TCP congestion control.
    """

    def __init__(self, config: "UploadConfig", environment: str):
        """
        Initialize the dynamic worker controller.

        Args:
            config: Upload configuration containing adjustment parameters.
            environment: The environment name (e.g., "production", "staging").
        """
        self.config = config
        self.environment = environment
        self.persistence = WorkerConfigPersistence(config.persistConfigPath)
        self.current_workers = self.get_initial_workers()
        self.previous_batch_throughput: Optional[float] = None
        self.total_upload_count = 0

    def get_initial_workers(self) -> int:
        """
        Get initial worker count - load from disk or calculate from CPU cores.

        Returns:
            Initial worker count to use.
        """
        # Try loading learned value from previous sessions
        learned = self.persistence.load_optimal_workers(self.environment)
        if learned is not None:
            # Ensure learned value respects current bounds
            clamped = max(
                self.config.minWorkers, min(learned, self.config.maxWorkersLimit)
            )
            logger.info("Loaded learned optimal workers from disk: %d", clamped)
            return clamped

        # Fallback: Calculate based on CPU cores
        cpu_cores = os.cpu_count() or 4
        initial = max(
            self.config.minWorkers,
            min(2 * cpu_cores, self.config.maxWorkers, self.config.maxWorkersLimit),
        )

        logger.info(
            "No learned config - starting with %d workers (CPUs: %d)",
            initial,
            cpu_cores,
        )
        return initial

    def record_batch_complete(self, batch_monitor: PerformanceMonitor) -> None:
        """
        Record that a batch has completed for tracking.

        Args:
            batch_monitor: Performance monitor for the completed batch.
        """
        self.total_upload_count += batch_monitor.success_count

    def calculate_adjustment(
        self, batch_monitor: PerformanceMonitor
    ) -> tuple[int, str]:
        """
        Calculate new worker count using balanced AIMD.

        The algorithm uses:
        - Proportional decrease (×0.7, ×0.85) when problems detected
        - Proportional increase (×1.1, ×1.2) when performing well
        - No stability period - adjust immediately based on performance

        Args:
            batch_monitor: Performance monitor for the current batch.

        Returns:
            Tuple of (new_worker_count, reason_string).
        """
        current_throughput = batch_monitor.get_throughput()
        error_rate = batch_monitor.get_error_rate()

        # DECREASE: Aggressive response to problems

        if error_rate > 0.05:  # 5% error rate
            # 30% reduction - significant but not panic
            new = max(self.config.minWorkers, int(self.current_workers * 0.7))
            reason = f"Error rate too high ({error_rate:.1%}) - reducing load"
            return new, reason

        if self.previous_batch_throughput is not None:
            degradation_ratio = current_throughput / self.previous_batch_throughput

            if degradation_ratio < 0.85:  # 15% degradation
                # 15% reduction - proportional response
                new = max(self.config.minWorkers, int(self.current_workers * 0.85))
                reason = f"Performance degraded ({degradation_ratio:.2f}x) - likely hit capacity limit"
                self.previous_batch_throughput = current_throughput
                return new, reason

        # INCREASE: Performance is good - push for more throughput

        if self.previous_batch_throughput is not None:
            improvement_ratio = current_throughput / self.previous_batch_throughput

            if error_rate < 0.05 and improvement_ratio > 1.05:  # 5% improvement
                # 20% increase - aggressive growth when improving
                new = min(
                    self.config.maxWorkersLimit, int(self.current_workers * 1.2)
                )
                reason = f"Performance improving ({improvement_ratio:.2f}x) - scaling up"
                self.previous_batch_throughput = current_throughput
                return new, reason

        # Stable and healthy - try cautious growth
        if error_rate < 0.03:  # <3% error rate
            # 10% increase - keep pushing towards optimal
            new = min(self.config.maxWorkersLimit, int(self.current_workers * 1.1))
            if new > self.current_workers:
                reason = "Stable performance - cautious increase"
                self.previous_batch_throughput = current_throughput
                return new, reason

        # STEADY STATE: No change needed
        reason = f"Performance acceptable - maintaining {self.current_workers} workers"
        self.previous_batch_throughput = current_throughput
        return self.current_workers, reason

    def finalize_upload(self) -> None:
        """Save learned configuration for future sessions."""
        if self.total_upload_count > 0:
            self.persistence.save_optimal_workers(
                self.environment, self.current_workers, self.total_upload_count
            )
            logger.info(
                "Saved learned workers (%d) to disk for %s",
                self.current_workers,
                self.environment,
            )
