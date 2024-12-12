from abc import abstractmethod
from typing import Any


class RapidataSelection:

    @abstractmethod
    def to_model(self) -> Any:
        pass
