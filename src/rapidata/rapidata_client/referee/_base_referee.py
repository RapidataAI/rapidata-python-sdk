from abc import ABC, abstractmethod
from typing import Mapping
import json

from rapidata.api_client.models.i_referee_model import IRefereeModel


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
    def _to_model(self) -> IRefereeModel:
        """
        Convert the referee to a referee configuration model.
        """
        pass

    def __str__(self) -> str:
        return json.dumps(self._to_dict())

    def __repr__(self) -> str:
        return self.__str__()
