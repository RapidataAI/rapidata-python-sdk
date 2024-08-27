from abc import abstractmethod
from typing import Any


class Metadata:

    def __init__(self):
        pass

    @abstractmethod
    def to_model(self) -> Any:
        pass
