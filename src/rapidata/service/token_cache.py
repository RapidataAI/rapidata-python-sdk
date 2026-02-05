"""
Token caching mechanism for OAuth tokens.

This module provides a file-based cache for OAuth tokens to allow multiple
processes/workers to share the same token instead of each fetching their own.
"""

import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rapidata.rapidata_client.config import logger

# Import platform-specific file locking
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl


class TokenCache:
    """
    File-based cache for OAuth tokens with cross-process locking.

    Tokens are cached by client_id and environment to allow sharing
    across multiple processes/workers.
    """

    def __init__(self, environment: str):
        """
        Initialize token cache.

        Args:
            environment: The environment (e.g., "rapidata.ai", "rapidata.dev")
        """
        self.environment = environment
        self.cache_dir = Path.home() / ".config" / "rapidata" / "token_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, client_id: str) -> Path:
        """Get the cache file path for a given client_id."""
        # Use client_id hash to create a safe filename
        safe_filename = f"{client_id}_{self.environment}.json".replace("/", "_")
        return self.cache_dir / safe_filename

    def _lock_file(self, file_handle):
        """Acquire an exclusive lock on the file."""
        if platform.system() == "Windows":
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)

    def _unlock_file(self, file_handle):
        """Release the lock on the file."""
        if platform.system() == "Windows":
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

    def get_token(self, client_id: str, leeway: int = 60) -> Optional[dict]:
        """
        Get a cached token if it exists and is not expired.

        Args:
            client_id: The OAuth client ID
            leeway: Seconds before expiration to consider token invalid (default 60)

        Returns:
            Token dict if valid, None otherwise
        """
        cache_path = self._get_cache_path(client_id)
        if not cache_path.exists():
            logger.debug("No cached token found for client_id: %s", client_id)
            return None

        lock_path = cache_path.with_suffix(".lock")

        try:
            with open(lock_path, "w") as lock_file:
                self._lock_file(lock_file)
                try:
                    with open(cache_path, "r") as f:
                        data = json.load(f)

                    # Check if token is expired (with leeway)
                    expires_at = data.get("expires_at")
                    if expires_at:
                        current_time = time.time()
                        if current_time >= (expires_at - leeway):
                            logger.debug(
                                "Cached token expired for client_id: %s", client_id
                            )
                            return None

                    token = data.get("token")
                    if token:
                        logger.debug("Using cached token for client_id: %s", client_id)
                        return token

                    return None
                finally:
                    self._unlock_file(lock_file)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning("Failed to read cached token: %s", e)
            return None

    def store_token(self, client_id: str, token: dict) -> None:
        """
        Store a token in the cache.

        Args:
            client_id: The OAuth client ID
            token: The token dict from OAuth2Client (should contain expires_at)
        """
        cache_path = self._get_cache_path(client_id)
        lock_path = cache_path.with_suffix(".lock")

        try:
            with open(lock_path, "w") as lock_file:
                self._lock_file(lock_file)
                try:
                    data = {
                        "token": token,
                        "expires_at": token.get("expires_at"),
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                    }

                    with open(cache_path, "w") as f:
                        json.dump(data, f, indent=2)

                    # Set file permissions (read/write for user only)
                    os.chmod(cache_path, 0o600)

                    logger.debug("Cached token for client_id: %s", client_id)
                finally:
                    self._unlock_file(lock_file)
        except (IOError, OSError) as e:
            logger.warning("Failed to cache token: %s", e)

    def clear_token(self, client_id: str) -> None:
        """
        Remove a cached token.

        Args:
            client_id: The OAuth client ID
        """
        cache_path = self._get_cache_path(client_id)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.debug("Cleared cached token for client_id: %s", client_id)
            except OSError as e:
                logger.warning("Failed to clear cached token: %s", e)

    def clear_all(self) -> None:
        """Clear all cached tokens for this environment."""
        try:
            for cache_file in self.cache_dir.glob(f"*_{self.environment}.json"):
                cache_file.unlink()
            logger.debug("Cleared all cached tokens for environment: %s", self.environment)
        except OSError as e:
            logger.warning("Failed to clear all cached tokens: %s", e)
