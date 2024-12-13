from abc import ABC, abstractmethod
from typing import Any, Mapping

class Referee(ABC):
    """
    The referee defines when a rapid is considered complete. 
    """
    @abstractmethod
    def _to_dict(self) -> Mapping[str, str | int | float]:
        """
        Convert the referee to a referee configuration dict.
        """
        pass

    @abstractmethod
    def _to_model(self) -> Any:
        """
        Convert the referee to a referee configuration model.
        """
        pass
