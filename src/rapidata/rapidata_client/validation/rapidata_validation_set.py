from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService

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
    
    def add_rapid(self, rapid: Rapid):
        """Add a Rapid to the validation set.

        Args:
            rapid (Rapid): The Rapid to add to the validation set.
        """
        rapid._add_to_validation_set(self.id, self.__openapi_service)

    def __str__(self):
        return f"name: '{self.name}' id: {self.id}"

    def __repr__(self):
        return f"name: '{self.name}' id: {self.id}"
