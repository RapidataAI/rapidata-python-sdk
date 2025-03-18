from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from requests.adapters import HTTPAdapter, Retry
import requests
from rapidata.api_client.models.update_dimensions_model import UpdateDimensionsModel

class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Represents a set of all the validation tasks that can be added to an order.

    When added to an order, the tasks will be selected randomly from the set.

    Attributes:
        id (str): The ID of the validation set.
        name (str): The name of the validation set.
    """

    def __init__(self, validation_set_id, name: str, openapi_service: OpenAPIService):
        self.id = validation_set_id
        self.name = name
        self.__openapi_service = openapi_service
        self.__session = self._get_session()
    
    def add_rapid(self, rapid: Rapid):
        """Add a Rapid to the validation set.

        Args:
            rapid (Rapid): The Rapid to add to the validation set.
        """
        rapid._add_to_validation_set(self.id, self.__openapi_service, self.__session)
        return self

    def update_dimensions(self, dimensions: list[str]):
        """Update the dimensions of the validation set.

        Args:
            dimensions (list[str]): The new dimensions of the validation set.
        """
        self.__openapi_service.validation_api.validation_validation_set_id_dimensions_patch(self.id, UpdateDimensionsModel(dimensions=dimensions))
        return self

    def _get_session(self, max_retries: int = 5, max_workers: int = 10) -> requests.Session:   
        """Get a requests session with retry logic.


        Args:
            max_retries (int): The maximum number of retries.
            max_workers (int): The maximum number of workers.

        Returns:
            requests.Session: A requests session with retry logic.
        """
        session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )

        adapter = HTTPAdapter(
            pool_connections=max_workers * 2,
            pool_maxsize=max_workers * 4,
            max_retries=retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    def __str__(self):
        return f"name: '{self.name}' id: {self.id}"

    def __repr__(self):
        return f"name: '{self.name}' id: {self.id}"
