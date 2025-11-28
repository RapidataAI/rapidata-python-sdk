import webbrowser
import urllib.parse
from colorama import Fore
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.api_client.models.update_validation_set_model import (
    UpdateValidationSetModel,
)
from rapidata.api_client.models.update_should_alert_model import UpdateShouldAlertModel
from rapidata.rapidata_client.validation.rapids._validation_rapid_uploader import (
    ValidationRapidUploader,
)


class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Represents a set of all the validation tasks that can be added to an order.

    When added to an order, the tasks will be selected randomly from the set.

    Attributes:
        id (str): The ID of the validation set.
        name (str): The name of the validation set.
    """

    def __init__(
        self,
        validation_set_id: str,
        name: str,
        dimensions: list[str],
        openapi_service: OpenAPIService,
    ):
        self.id = validation_set_id
        self.name = name
        self.dimensions = dimensions
        self.validation_set_details_page = (
            f"https://app.{openapi_service.environment}/validation-set/detail/{self.id}"
        )
        self._openapi_service = openapi_service
        self.validation_rapid_uploader = ValidationRapidUploader(openapi_service)

    def add_rapid(self, rapid: Rapid) -> "RapidataValidationSet":
        """Add a Rapid to the validation set.

        Args:
            rapid (Rapid): The Rapid to add to the validation set.
        """
        with tracer.start_as_current_span("RapidataValidationSet.add_rapid"):
            logger.debug("Adding rapid %s to validation set %s", rapid, self.id)
            self.validation_rapid_uploader.upload_rapid(rapid, self.id)
            # Currently necessary until backend properly propagates the dimensions
            return self.update_dimensions(self.dimensions)

    def update_dimensions(self, dimensions: list[str]) -> "RapidataValidationSet":
        """Update the dimensions of the validation set.

        Args:
            dimensions (list[str]): The new dimensions of the validation set.
        """
        with tracer.start_as_current_span("RapidataValidationSet.update_dimensions"):
            logger.debug(
                "Updating dimensions for validation set %s to %s", self.id, dimensions
            )
            self._openapi_service.validation_api.validation_set_validation_set_id_patch(
                self.id, UpdateValidationSetModel(dimensions=dimensions)
            )
            self.dimensions = dimensions
            return self

    def update_should_alert(self, should_alert: bool) -> "RapidataValidationSet":
        """Determines whether users should be alerted if they answer incorrectly.

        Args:
            should_alert (bool): Specifies whether users should be alerted for incorrect answers. Defaults to True if not specifically overridden by this method.

        Note:
            The userScore dimensions which are updated when a user answers a validation task are updated regardless of the value of `should_alert`.
        """
        with tracer.start_as_current_span("RapidataValidationSet.update_should_alert"):
            logger.debug(
                "Setting shouldAlert for validation set %s to %s", self.id, should_alert
            )
            self._openapi_service.validation_api.validation_set_validation_set_id_patch(
                self.id, UpdateValidationSetModel(shouldAlert=should_alert)
            )
            return self

    def update_can_be_flagged(self, can_be_flagged: bool) -> "RapidataValidationSet":
        """Update if tasks in the validation set can be flagged for bad accuracy.

        Args:
            can_be_flagged (bool): Specifies whether tasks in the validation set can be flagged for bad accuracy. Defaults to True if not specifically overridden by this method.
        """
        with tracer.start_as_current_span(
            "RapidataValidationSet.update_can_be_flagged"
        ):
            logger.debug(
                "Setting canBeFlagged for validation set %s to %s",
                self.id,
                can_be_flagged,
            )
            self._openapi_service.validation_api.validation_set_validation_set_id_patch(
                self.id, UpdateValidationSetModel(isFlagOverruled=(not can_be_flagged))
            )
            return self

    def _get_total_and_labeled_rapids_count(self) -> tuple[int, int]:
        """Get the total and labeled rapids count of the validation set."""
        with tracer.start_as_current_span(
            "RapidataValidationSet.get_total_and_labeled_rapids_count"
        ):
            from rapidata.api_client.models.query_model import QueryModel
            from rapidata.api_client.models.get_validation_rapids_result import (
                GetValidationRapidsResult,
            )
            from rapidata.api_client.models.page_info import PageInfo

            current_page = 1
            total_pages = None
            uploaded_rapids: list[GetValidationRapidsResult] = []

            while True:
                rapids_result = self._openapi_service.validation_api.validation_set_validation_set_id_rapids_get(
                    validation_set_id=self.id,
                    model=QueryModel(page=PageInfo(index=current_page, size=100)),
                )

                if rapids_result.total_pages is None:
                    raise ValueError(
                        "An error occurred while fetching rapids: total_pages is None"
                    )

                total_pages = rapids_result.total_pages

                uploaded_rapids.extend(rapids_result.items)

                if current_page >= total_pages:
                    break

                current_page += 1

            return len(uploaded_rapids), sum(
                1 for rapid in uploaded_rapids if rapid.truth
            )

    def view(self) -> None:
        """
        Opens the validation set details page in the browser.

        Raises:
            Exception: If the order is not in processing state.
        """
        logger.info("Opening validation set details page in browser...")
        could_open_browser = webbrowser.open(self.validation_set_details_page)
        if not could_open_browser:
            encoded_url = urllib.parse.quote(
                self.validation_set_details_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def delete(self) -> None:
        """Deletes the validation set"""
        with tracer.start_as_current_span("RapidataValidationSet.delete"):
            logger.info("Deleting ValidationSet '%s'", self)
            self._openapi_service.validation_api.validation_set_validation_set_id_delete(
                self.id
            )
            logger.debug("ValidationSet '%s' has been deleted.", self)
            managed_print(f"ValidationSet '{self}' has been deleted.")

    def __str__(self) -> str:
        return f"name: '{self.name}' id: {self.id} dimensions: {self.dimensions}"

    def __repr__(self) -> str:
        return f"name: '{self.name}' id: {self.id} dimensions: {self.dimensions}"
