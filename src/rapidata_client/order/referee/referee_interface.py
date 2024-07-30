from abc import ABC, abstractmethod
from typing import Any


class Referee(ABC):
    """
    The referee defines when a rapid is considered complete. 
    """
    @abstractmethod
    def to_dict(self) -> dict[str, str | int | float]:
        """
        Convert the referee to a referee configuration dict.
        """
        pass