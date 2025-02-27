from abc import abstractmethod
from typing import Any


class Metadata:
    """The base class for all Rapidata Metadata."""

    @abstractmethod
    def to_model(self) -> Any:
        pass
