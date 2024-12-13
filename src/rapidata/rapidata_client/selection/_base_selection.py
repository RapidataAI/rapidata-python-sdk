from abc import abstractmethod
from typing import Any


class RapidataSelection:

    @abstractmethod
    def _to_model(self) -> Any:
        pass
