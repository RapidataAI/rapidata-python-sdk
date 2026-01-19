import threading
from typing import Callable, cast

from diskcache import FanoutCache
from rapidata.rapidata_client.config import logger

from concurrent.futures import Future


class SingleFlightCache:
    """Cache with single-flight pattern to prevent duplicate concurrent fetches."""

    def __init__(self, name: str, storage: dict[str, str] | FanoutCache | None = None):
        self._name = name
        self._storage: dict[str, str] | FanoutCache = (
            storage if storage is not None else {}
        )
        self._in_flight: dict[str, Future[str]] = {}
        self._lock = threading.Lock()

    def set_storage(self, storage: dict[str, str] | FanoutCache) -> None:
        """Replace the cache storage."""
        with self._lock:
            old_storage = self._storage
            self._storage = storage
            if isinstance(old_storage, FanoutCache):
                try:
                    old_storage.close()
                except Exception:
                    pass

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], str],
        should_cache: bool = True,
    ) -> str:
        """Get value from cache or fetch it, preventing duplicate concurrent fetches."""
        # Fast path - check cache without lock
        cached = self._storage.get(key)
        if cached is not None:
            logger.debug("%s: cache hit", self._name)
            return cast(str, cached)

        with self._lock:
            # Double-check cache under lock
            cached = self._storage.get(key)
            if cached is not None:
                logger.debug("%s: cache hit", self._name)
                return cast(str, cached)

            # Check if there's an in-flight request
            in_flight = self._in_flight.get(key)
            if in_flight is None:
                in_flight = Future()
                self._in_flight[key] = in_flight
                should_fetch = True
            else:
                should_fetch = False

        if not should_fetch:
            logger.debug("%s: waiting for in-flight request", self._name)
            return in_flight.result()

        # We need to fetch
        try:
            result = fetch_fn()
            if should_cache:
                self._storage[key] = result
                logger.debug("%s: cached result", self._name)
            in_flight.set_result(result)
            return result
        except Exception as e:
            in_flight.set_exception(e)
            raise
        finally:
            with self._lock:
                self._in_flight.pop(key, None)

    def clear(self) -> None:
        """Clear the cache."""
        self._storage.clear()
