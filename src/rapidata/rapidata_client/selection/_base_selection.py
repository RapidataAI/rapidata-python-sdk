from abc import abstractmethod
from typing import Any


class RapidataSelection:

    @abstractmethod
    def _to_model(self) -> Any:
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
