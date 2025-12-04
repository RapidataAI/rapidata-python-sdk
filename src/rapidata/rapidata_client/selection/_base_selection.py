from abc import abstractmethod

from rapidata.api_client.models.i_selection import ISelection


class RapidataSelection:

    @abstractmethod
    def _to_model(self) -> ISelection:
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
