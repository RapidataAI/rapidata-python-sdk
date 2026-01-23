"""Unit tests for PerformanceMonitor."""

import time
import pytest
from rapidata.rapidata_client.utils.performance_monitor import PerformanceMonitor


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor."""

    def test_initialization(self):
        """Test monitor initialization."""
        monitor = PerformanceMonitor(total_items=100)
        assert monitor.total_items == 100
        assert monitor.success_count == 0
        assert monitor.error_count == 0
        assert monitor.end_time is None

    def test_record_completion_success(self):
        """Test recording successful completions."""
        monitor = PerformanceMonitor(total_items=10)
        monitor.record_completion(success=True)
        monitor.record_completion(success=True)
        assert monitor.success_count == 2
        assert monitor.error_count == 0

    def test_record_completion_failure(self):
        """Test recording failed completions."""
        monitor = PerformanceMonitor(total_items=10)
        monitor.record_completion(success=False)
        monitor.record_completion(success=False)
        monitor.record_completion(success=False)
        assert monitor.success_count == 0
        assert monitor.error_count == 3

    def test_record_completion_mixed(self):
        """Test recording mixed success and failure."""
        monitor = PerformanceMonitor(total_items=10)
        monitor.record_completion(success=True)
        monitor.record_completion(success=False)
        monitor.record_completion(success=True)
        monitor.record_completion(success=True)
        assert monitor.success_count == 3
        assert monitor.error_count == 1

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        monitor = PerformanceMonitor(total_items=10)
        # No items processed
        assert monitor.get_error_rate() == 0.0

        # 25% error rate
        monitor.record_completion(success=True)
        monitor.record_completion(success=True)
        monitor.record_completion(success=True)
        monitor.record_completion(success=False)
        assert monitor.get_error_rate() == 0.25

        # 50% error rate
        monitor.record_completion(success=False)
        monitor.record_completion(success=False)
        assert monitor.get_error_rate() == 0.5

    def test_throughput_calculation(self):
        """Test throughput calculation."""
        monitor = PerformanceMonitor(total_items=10)

        # No end time yet
        assert monitor.get_throughput() == 0.0

        # Simulate processing
        monitor.record_completion(success=True)
        monitor.record_completion(success=True)
        monitor.record_completion(success=True)
        time.sleep(0.1)  # 100ms
        monitor.finish_batch()

        # Should be approximately 30 items/sec (3 items in 0.1s)
        throughput = monitor.get_throughput()
        assert throughput > 20  # Allow for timing variance
        assert throughput < 40

    def test_duration_calculation(self):
        """Test duration calculation."""
        monitor = PerformanceMonitor(total_items=10)

        # No end time yet
        assert monitor.get_duration() == 0.0

        # Simulate processing
        time.sleep(0.1)
        monitor.finish_batch()

        # Should be approximately 0.1 seconds
        duration = monitor.get_duration()
        assert duration >= 0.09  # Allow for timing variance
        assert duration <= 0.15

    def test_reset(self):
        """Test resetting the monitor."""
        monitor = PerformanceMonitor(total_items=10)
        monitor.record_completion(success=True)
        monitor.record_completion(success=False)
        monitor.finish_batch()

        # Reset
        monitor.reset()

        # Should be reset except total_items
        assert monitor.total_items == 10
        assert monitor.success_count == 0
        assert monitor.error_count == 0
        assert monitor.end_time is None

    def test_finish_batch(self):
        """Test finishing a batch."""
        monitor = PerformanceMonitor(total_items=10)
        assert monitor.end_time is None

        monitor.finish_batch()
        assert monitor.end_time is not None
        assert monitor.end_time >= monitor.start_time
