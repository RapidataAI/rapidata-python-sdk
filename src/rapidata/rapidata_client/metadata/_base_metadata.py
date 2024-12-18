from abc import abstractmethod
from typing import Any


class Metadata:
    """The base class for all Rapidata Metadata."""

    def __init__(self, identifier: str):
        self._identifier = identifier

    @abstractmethod
    def _to_model(self) -> Any:
        pass
