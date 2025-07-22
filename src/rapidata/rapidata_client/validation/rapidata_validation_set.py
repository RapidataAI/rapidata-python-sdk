from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.logging import logger
from rapidata.api_client.models.update_dimensions_model import UpdateDimensionsModel
from rapidata.api_client.models.update_should_alert_model import UpdateShouldAlertModel

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
        return self

    def update_dimensions(self, dimensions: list[str]):
        """Update the dimensions of the validation set.

        Args:
            dimensions (list[str]): The new dimensions of the validation set.
        """
        logger.debug(f"Updating dimensions for validation set {self.id} to {dimensions}")
        self.__openapi_service.validation_api.validation_set_validation_set_id_dimensions_put(self.id, UpdateDimensionsModel(dimensions=dimensions))
        return self
    
    def update_should_alert(self, should_alert: bool):
        """Determines whether users should be alerted if they answer incorrectly.

        Args:
            should_alert (bool): Specifies whether users should be alerted for incorrect answers. Defaults to True if not specifically overridden by this method.

        Note:
            The userScore dimensions which are updated when a user answers a validation task are updated regardless of the value of `should_alert`.
        """
        logger.debug(f"Setting shouldAlert for validation set {self.id} to {should_alert}")
        self.__openapi_service.validation_api.validation_set_validation_set_id_shouldalert_patch(
            self.id, 
            UpdateShouldAlertModel(shouldAlert=should_alert)
        )
        return self

    def __str__(self):
        return f"name: '{self.name}' id: {self.id}"

    def __repr__(self):
        return f"name: '{self.name}' id: {self.id}"
