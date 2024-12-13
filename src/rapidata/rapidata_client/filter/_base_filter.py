from abc import abstractmethod
from typing import Any


class RapidataFilter:
    """The base class for all Rapidata Filters."""

    @abstractmethod
    def _to_model(self) -> Any:
        pass
