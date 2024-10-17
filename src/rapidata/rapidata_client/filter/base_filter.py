from abc import abstractmethod
from typing import Any


class Filter:

    @abstractmethod
    def to_model(self) -> Any:
        pass
