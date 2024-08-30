from abc import abstractmethod
from typing import Any


class Selection:

    @abstractmethod
    def to_model(self) -> Any:
        pass
