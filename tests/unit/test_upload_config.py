"""Unit tests for UploadConfig."""

from pathlib import Path
import pytest
from rapidata.rapidata_client.config.upload_config import UploadConfig


class TestUploadConfig:
    """Test suite for UploadConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = UploadConfig()
        assert config.maxWorkers == 25
        assert config.maxRetries == 3
        assert config.enableDynamicWorkers is True
        assert config.batchSize == 1000
        assert config.minWorkers == 5
        assert config.maxWorkersLimit == 200
        assert config.persistConfigPath == Path.home() / ".rapidata" / "worker_config.json"

    def test_custom_values(self):
        """Test setting custom configuration values."""
        config = UploadConfig(
            maxWorkers=50,
            maxRetries=5,
            enableDynamicWorkers=False,
            batchSize=500,
            minWorkers=10,
            maxWorkersLimit=150,
        )
        assert config.maxWorkers == 50
        assert config.maxRetries == 5
        assert config.enableDynamicWorkers is False
        assert config.batchSize == 500
        assert config.minWorkers == 10
        assert config.maxWorkersLimit == 150

    def test_min_workers_validation(self):
        """Test minWorkers validation."""
        # Valid value
        config = UploadConfig(minWorkers=1)
        assert config.minWorkers == 1

        # Invalid value
        with pytest.raises(ValueError, match="minWorkers must be at least 1"):
            UploadConfig(minWorkers=0)

    def test_batch_size_validation(self):
        """Test batchSize validation."""
        # Valid value
        config = UploadConfig(batchSize=10)
        assert config.batchSize == 10

        # Invalid value
        with pytest.raises(ValueError, match="batchSize must be at least 10"):
            UploadConfig(batchSize=5)

    def test_max_workers_warning(self, caplog):
        """Test maxWorkers warning for values > 200."""
        import logging
        caplog.set_level(logging.WARNING)

        config = UploadConfig(maxWorkers=250)
        assert config.maxWorkers == 250
        assert "above the recommended limit of 200" in caplog.text

    def test_max_workers_limit_warning(self, caplog):
        """Test maxWorkersLimit warning for values > 200."""
        import logging
        caplog.set_level(logging.WARNING)

        config = UploadConfig(maxWorkersLimit=300)
        assert config.maxWorkersLimit == 300
        assert "above the recommended limit of 200" in caplog.text

    def test_backward_compatibility(self):
        """Test backward compatibility with old configs."""
        # Old code that only sets maxWorkers
        config = UploadConfig(maxWorkers=50)

        # Should still work and enable dynamic workers by default
        assert config.maxWorkers == 50
        assert config.enableDynamicWorkers is True

    def test_disable_dynamic_workers(self):
        """Test disabling dynamic workers."""
        config = UploadConfig(enableDynamicWorkers=False)
        assert config.enableDynamicWorkers is False

    def test_cache_configuration(self):
        """Test cache-related configuration."""
        config = UploadConfig(
            cacheUploads=False,
            cacheTimeout=0.5,
            cacheSizeLimit=200_000_000,
        )
        assert config.cacheUploads is False
        assert config.cacheTimeout == 0.5
        assert config.cacheSizeLimit == 200_000_000
