from abc import abstractmethod
from typing import Any


class Metadata:

    def __init__(self, identifier: str):
        self._identifier = identifier

    @abstractmethod
    def to_model(self) -> Any:
        pass
