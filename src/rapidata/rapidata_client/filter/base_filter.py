from abc import abstractmethod
from typing import Any


class RapidataFilter:

    @abstractmethod
    def to_model(self) -> Any:
        pass
