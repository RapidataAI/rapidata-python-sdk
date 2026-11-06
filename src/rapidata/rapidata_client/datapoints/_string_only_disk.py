from __future__ import annotations

from typing import Any

from diskcache import Disk
from diskcache.core import MODE_RAW, UNKNOWN

from rapidata.rapidata_client.config import logger


class StringOnlyDisk(Disk):
    """A diskcache ``Disk`` that stores and reads back short ``str`` keys and values only.

    The default ``Disk`` unpickles any entry marked as a pickle, so a planted entry in the
    cache directory would run code; here such an entry reads as a miss and is overwritten.
    """

    def put(self, key: Any):
        if type(key) is not str:
            raise TypeError(f"Upload cache keys must be str, got {type(key).__name__}")
        return super().put(key)

    def get(self, key: Any, raw: bool):
        if not raw or type(key) is not str:
            raise ValueError("Upload cache holds a non-string key")
        return key

    def store(self, value: Any, read: bool, key: Any = UNKNOWN):
        if type(value) is not str or len(value) >= self.min_file_size:
            raise TypeError("Upload cache values must be short str")
        return super().store(value, read, key)

    def fetch(self, mode: int, filename: str | None, value: Any, read: bool):
        if mode != MODE_RAW or type(value) is not str:
            # Cache.get treats OSError as a missing entry.
            logger.warning("Ignoring unreadable entry in the upload cache")
            raise OSError("Upload cache entry is not a raw string")
        return value
