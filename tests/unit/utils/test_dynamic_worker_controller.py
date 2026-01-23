"""Unit tests for DynamicWorkerController."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from rapidata.rapidata_client.utils.dynamic_worker_controller import (
    DynamicWorkerController,
)
from rapidata.rapidata_client.utils.performance_monitor import PerformanceMonitor
from rapidata.rapidata_client.config.upload_config import UploadConfig


class TestDynamicWorkerController:
    """Test suite for DynamicWorkerController."""

    @pytest.fixture
    def temp_config_path(self):
        """Create a temporary config file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "worker_config.json"

    @pytest.fixture
    def upload_config(self, temp_config_path):
        """Create an upload config for testing."""
        config = UploadConfig()
        config.persistConfigPath = temp_config_path
        config.minWorkers = 5
        config.maxWorkers = 25
        config.maxWorkersLimit = 200
        return config

    def test_initialization(self, upload_config):
        """Test controller initialization."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        assert controller.environment == "production"
        assert controller.current_workers >= upload_config.minWorkers
        assert controller.previous_batch_throughput is None
        assert controller.total_upload_count == 0

    @patch("os.cpu_count", return_value=8)
    def test_get_initial_workers_cpu_based(self, mock_cpu, upload_config):
        """Test initial worker calculation based on CPU cores."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        # Should be 2 * 8 = 16
        assert controller.current_workers == 16

    @patch("os.cpu_count", return_value=4)
    def test_get_initial_workers_respects_min(self, mock_cpu, upload_config):
        """Test that initial workers respects minimum bound."""
        upload_config.minWorkers = 10
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        # 2 * 4 = 8, but min is 10
        assert controller.current_workers == 10

    @patch("os.cpu_count", return_value=50)
    def test_get_initial_workers_respects_max(self, mock_cpu, upload_config):
        """Test that initial workers respects maximum bound."""
        upload_config.maxWorkers = 25
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        # 2 * 50 = 100, but max is 25
        assert controller.current_workers == 25

    def test_load_learned_workers(self, upload_config):
        """Test loading learned workers from disk."""
        # Save a learned value
        controller1 = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller1.current_workers = 45
        controller1.total_upload_count = 100
        controller1.finalize_upload()

        # Create new controller - should load learned value
        controller2 = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        assert controller2.current_workers == 45

    def test_calculate_adjustment_high_error_rate(self, upload_config):
        """Test worker reduction with high error rate."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 50

        # Create monitor with 10% error rate
        monitor = PerformanceMonitor(total_items=100)
        for _ in range(90):
            monitor.record_completion(success=True)
        for _ in range(10):
            monitor.record_completion(success=False)
        monitor.finish_batch()

        new_workers, reason = controller.calculate_adjustment(monitor)

        # Should reduce by 30% (×0.7)
        assert new_workers == int(50 * 0.7)  # 35
        assert "Error rate too high" in reason

    def test_calculate_adjustment_performance_degradation(self, upload_config):
        """Test worker reduction with performance degradation."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 50
        controller.previous_batch_throughput = 100.0  # 100 items/sec

        # Create monitor with degraded performance (50 items/sec)
        monitor = PerformanceMonitor(total_items=50)
        for _ in range(50):
            monitor.record_completion(success=True)
        monitor.start_time -= 1.0  # Make it take 1 second
        monitor.finish_batch()

        new_workers, reason = controller.calculate_adjustment(monitor)

        # Should reduce by 15% (×0.85) due to 50% degradation
        assert new_workers == int(50 * 0.85)  # 42
        assert "degraded" in reason.lower()

    def test_calculate_adjustment_performance_improving(self, upload_config):
        """Test worker increase with performance improvement."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 30
        controller.previous_batch_throughput = 50.0  # 50 items/sec

        # Create monitor with improved performance (60 items/sec = 20% improvement)
        monitor = PerformanceMonitor(total_items=60)
        for _ in range(60):
            monitor.record_completion(success=True)
        monitor.start_time -= 1.0  # Make it take 1 second
        monitor.finish_batch()

        new_workers, reason = controller.calculate_adjustment(monitor)

        # Should increase by 20% (×1.2)
        assert new_workers == int(30 * 1.2)  # 36
        assert "improving" in reason.lower()

    def test_calculate_adjustment_stable_performance(self, upload_config):
        """Test cautious increase with stable performance."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 30
        controller.previous_batch_throughput = None  # First batch

        # Create monitor with low error rate
        monitor = PerformanceMonitor(total_items=100)
        for _ in range(98):
            monitor.record_completion(success=True)
        for _ in range(2):
            monitor.record_completion(success=False)
        monitor.finish_batch()

        new_workers, reason = controller.calculate_adjustment(monitor)

        # Should increase by 10% (×1.1) with <3% error rate
        assert new_workers == int(30 * 1.1)  # 33
        assert "Stable performance" in reason

    def test_calculate_adjustment_respects_min_workers(self, upload_config):
        """Test that adjustment respects minimum worker bound."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 6
        upload_config.minWorkers = 5

        # Create monitor with high error rate
        monitor = PerformanceMonitor(total_items=100)
        for _ in range(50):
            monitor.record_completion(success=True)
        for _ in range(50):
            monitor.record_completion(success=False)
        monitor.finish_batch()

        new_workers, reason = controller.calculate_adjustment(monitor)

        # Should not go below minWorkers
        assert new_workers >= upload_config.minWorkers

    def test_calculate_adjustment_respects_max_workers(self, upload_config):
        """Test that adjustment respects maximum worker bound."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 180
        upload_config.maxWorkersLimit = 200
        controller.previous_batch_throughput = 100.0

        # Create monitor with improved performance
        monitor = PerformanceMonitor(total_items=120)
        for _ in range(120):
            monitor.record_completion(success=True)
        monitor.start_time -= 1.0
        monitor.finish_batch()

        new_workers, reason = controller.calculate_adjustment(monitor)

        # Should not exceed maxWorkersLimit
        assert new_workers <= upload_config.maxWorkersLimit

    def test_record_batch_complete(self, upload_config):
        """Test recording batch completion."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )

        monitor = PerformanceMonitor(total_items=100)
        for _ in range(95):
            monitor.record_completion(success=True)
        for _ in range(5):
            monitor.record_completion(success=False)
        monitor.finish_batch()

        controller.record_batch_complete(monitor)

        assert controller.total_upload_count == 95

    def test_finalize_upload(self, upload_config):
        """Test finalizing upload saves config."""
        controller = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller.current_workers = 42
        controller.total_upload_count = 1000

        controller.finalize_upload()

        # Create new controller and verify it loads the saved value
        controller2 = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        assert controller2.current_workers == 42

    def test_per_environment_persistence(self, upload_config):
        """Test that different environments have separate configs."""
        # Save for production
        controller_prod = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller_prod.current_workers = 50
        controller_prod.total_upload_count = 100
        controller_prod.finalize_upload()

        # Save for staging
        controller_staging = DynamicWorkerController(
            config=upload_config, environment="staging"
        )
        controller_staging.current_workers = 30
        controller_staging.total_upload_count = 50
        controller_staging.finalize_upload()

        # Load and verify separate values
        controller_prod2 = DynamicWorkerController(
            config=upload_config, environment="production"
        )
        controller_staging2 = DynamicWorkerController(
            config=upload_config, environment="staging"
        )

        assert controller_prod2.current_workers == 50
        assert controller_staging2.current_workers == 30
