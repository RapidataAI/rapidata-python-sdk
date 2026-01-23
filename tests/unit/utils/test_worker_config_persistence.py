"""Unit tests for WorkerConfigPersistence."""

import json
import tempfile
from pathlib import Path
import pytest
from rapidata.rapidata_client.utils.worker_config_persistence import (
    WorkerConfigPersistence,
)


class TestWorkerConfigPersistence:
    """Test suite for WorkerConfigPersistence."""

    @pytest.fixture
    def temp_config_path(self):
        """Create a temporary config file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "worker_config.json"

    def test_initialization(self, temp_config_path):
        """Test persistence initialization."""
        persistence = WorkerConfigPersistence(temp_config_path)
        assert persistence.config_path == temp_config_path

    def test_load_optimal_workers_no_file(self, temp_config_path):
        """Test loading when config file doesn't exist."""
        persistence = WorkerConfigPersistence(temp_config_path)
        result = persistence.load_optimal_workers("production")
        assert result is None

    def test_save_and_load_optimal_workers(self, temp_config_path):
        """Test saving and loading optimal workers."""
        persistence = WorkerConfigPersistence(temp_config_path)

        # Save
        persistence.save_optimal_workers(
            environment="production", workers=45, sample_count=100
        )

        # Load
        result = persistence.load_optimal_workers("production")
        assert result == 45

    def test_save_multiple_environments(self, temp_config_path):
        """Test saving multiple environments."""
        persistence = WorkerConfigPersistence(temp_config_path)

        # Save production
        persistence.save_optimal_workers(
            environment="production", workers=45, sample_count=100
        )

        # Save staging
        persistence.save_optimal_workers(
            environment="staging", workers=30, sample_count=50
        )

        # Load both
        prod_result = persistence.load_optimal_workers("production")
        staging_result = persistence.load_optimal_workers("staging")

        assert prod_result == 45
        assert staging_result == 30

    def test_load_nonexistent_environment(self, temp_config_path):
        """Test loading an environment that doesn't exist."""
        persistence = WorkerConfigPersistence(temp_config_path)

        # Save production
        persistence.save_optimal_workers(
            environment="production", workers=45, sample_count=100
        )

        # Try to load staging (doesn't exist)
        result = persistence.load_optimal_workers("staging")
        assert result is None

    def test_overwrite_existing_environment(self, temp_config_path):
        """Test overwriting an existing environment."""
        persistence = WorkerConfigPersistence(temp_config_path)

        # Save initial value
        persistence.save_optimal_workers(
            environment="production", workers=30, sample_count=50
        )

        # Overwrite with new value
        persistence.save_optimal_workers(
            environment="production", workers=50, sample_count=150
        )

        # Load - should have new value
        result = persistence.load_optimal_workers("production")
        assert result == 50

    def test_json_structure(self, temp_config_path):
        """Test the JSON structure of saved config."""
        persistence = WorkerConfigPersistence(temp_config_path)

        persistence.save_optimal_workers(
            environment="production", workers=45, sample_count=100
        )

        # Read the JSON file directly
        with open(temp_config_path, "r") as f:
            config_data = json.load(f)

        # Verify structure
        assert "production" in config_data
        assert config_data["production"]["optimal_workers"] == 45
        assert config_data["production"]["sample_count"] == 100
        assert "last_updated" in config_data["production"]

    def test_ensure_config_dir(self, temp_config_path):
        """Test ensuring config directory exists."""
        # Use a path with nested directories
        nested_path = temp_config_path.parent / "nested" / "dir" / "config.json"
        persistence = WorkerConfigPersistence(nested_path)

        # Ensure directory is created
        persistence.ensure_config_dir()
        assert nested_path.parent.exists()

    def test_get_config_path(self, temp_config_path):
        """Test getting the config path."""
        persistence = WorkerConfigPersistence(temp_config_path)
        assert persistence.get_config_path() == temp_config_path

    def test_corrupted_json_file(self, temp_config_path):
        """Test handling corrupted JSON file."""
        # Create a corrupted JSON file
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, "w") as f:
            f.write("{ invalid json }")

        persistence = WorkerConfigPersistence(temp_config_path)
        result = persistence.load_optimal_workers("production")

        # Should return None on error
        assert result is None
