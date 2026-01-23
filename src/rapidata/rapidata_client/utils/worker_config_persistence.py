"""Persistence layer for learned worker configuration."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from rapidata.rapidata_client.config import logger


class WorkerConfigPersistence:
    """
    Persists learned worker configuration across sessions.

    Stores optimal worker counts per environment in a JSON file,
    allowing the system to remember learned values across kernel
    restarts and process termination.
    """

    def __init__(self, config_path: Path):
        """
        Initialize the persistence layer.

        Args:
            config_path: Path to the JSON configuration file.
        """
        self.config_path = config_path

    def load_optimal_workers(self, environment: str) -> Optional[int]:
        """
        Load the learned optimal worker count for an environment.

        Args:
            environment: The environment name (e.g., "production", "staging").

        Returns:
            The optimal worker count if found, None otherwise.
        """
        try:
            if not self.config_path.exists():
                logger.debug(
                    "Worker config file does not exist: %s", self.config_path
                )
                return None

            with open(self.config_path, "r") as f:
                config_data = json.load(f)

            env_config = config_data.get(environment)
            if not env_config:
                logger.debug("No config found for environment: %s", environment)
                return None

            optimal_workers = env_config.get("optimal_workers")
            last_updated = env_config.get("last_updated")
            sample_count = env_config.get("sample_count", 0)

            logger.debug(
                "Loaded config for %s: %d workers (updated %s, %d samples)",
                environment,
                optimal_workers,
                last_updated,
                sample_count,
            )

            return optimal_workers

        except Exception as e:
            logger.warning("Failed to load worker config: %s", e)
            return None

    def save_optimal_workers(
        self, environment: str, workers: int, sample_count: int
    ) -> None:
        """
        Save the learned optimal worker count for an environment.

        Args:
            environment: The environment name (e.g., "production", "staging").
            workers: The optimal worker count to save.
            sample_count: Number of uploads that informed this value.
        """
        try:
            # Ensure directory exists
            self.ensure_config_dir()

            # Load existing config or create new
            config_data = {}
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config_data = json.load(f)

            # Update environment config
            config_data[environment] = {
                "optimal_workers": workers,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "sample_count": sample_count,
            }

            # Write back to file
            with open(self.config_path, "w") as f:
                json.dump(config_data, f, indent=2)

            logger.debug(
                "Saved worker config for %s: %d workers (%d samples)",
                environment,
                workers,
                sample_count,
            )

        except Exception as e:
            logger.warning("Failed to save worker config: %s", e)

    def ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Failed to create config directory: %s", e)

    def get_config_path(self) -> Path:
        """
        Get the path to the configuration file.

        Returns:
            Path to the worker config JSON file.
        """
        return self.config_path
