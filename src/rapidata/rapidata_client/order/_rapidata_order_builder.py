from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Sequence, get_args
import secrets

from rapidata.rapidata_client.datapoints._datapoint import Datapoint

if TYPE_CHECKING:
    from rapidata.api_client.models.create_order_model import CreateOrderModel
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.filter import RapidataFilter, UserScoreFilter
from rapidata.rapidata_client.config import (
    logger,
    managed_print,
    rapidata_config,
    tracer,
)
from rapidata.rapidata_client.validation.validation_set_manager import (
    ValidationSetManager,
)
from rapidata.rapidata_client.validation.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee import Referee
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.settings import RapidataSetting
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.selection import (
    ConditionalValidationSelection,
    LabelingSelection,
    CappedSelection,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)

StickyStateLiteral = Literal["Temporary", "Permanent", "Passive"]


class RapidataOrderBuilder:
    """Builder object for creating Rapidata orders.

    Use the fluent interface to set the desired configuration. Add a workflow to the order using `.workflow()` and finally call `.create()` to create the order.

    Args:
        openapi_service (OpenAPIService): The OpenAPIService instance.
        name (str): The name of the order.
    """

    def __init__(
        self,
        name: str,
        openapi_service: OpenAPIService,
    ):
        self._name = name
        self._openapi_service = openapi_service
        self._dataset: Optional[RapidataDataset] = None
        self._workflow: Workflow | None = None
        self._referee: Referee | None = None
        self._validation_set: RapidataValidationSet | None = None
        self._settings: Sequence[RapidataSetting] | None = None
        self._user_filters: list[RapidataFilter] = []
        self._selections: Sequence[RapidataSelection] = []
        self._priority: int | None = None
        self._datapoints: list[Datapoint] = []
        self._sticky_state_value: StickyStateLiteral | None = None
        self._validation_set_manager: ValidationSetManager = ValidationSetManager(
            self._openapi_service
        )

    def _to_model(self) -> CreateOrderModel:
        """
        Convert the builder configuration to a CreateOrderModel.

        Raises:
            ValueError: If no workflow is provided.

        Returns:
            CreateOrderModel: The model representing the order configuration.
        """
        if self._workflow is None:
            raise ValueError("You must provide a workflow to create an order.")

        if self._referee is None:
            managed_print("No referee provided, using default NaiveReferee.")
            self._referee = NaiveReferee()

        sticky_state = self._sticky_state_value

        validation_set_id = (
            self._validation_set.id
            if (self._validation_set and not self._selections)
            else None
        )
        from rapidata.api_client.models.create_order_model import CreateOrderModel
        from rapidata.api_client.models.sticky_state import StickyState

        return CreateOrderModel(
            orderName=self._name,
            workflow=self._workflow._to_model(),
            userFilters=[user_filter._to_model() for user_filter in self._user_filters],
            referee=self._referee._to_model(),
            validationSetId=validation_set_id,
            featureFlags=(
                [setting._to_feature_flag_model() for setting in self._settings]
                if self._settings is not None
                else None
            ),
            selections=(
                [selection._to_model() for selection in self._selections]
                if self._selections
                else None
            ),
            priority=self._priority,
            stickyState=(StickyState(sticky_state) if sticky_state else None),
        )

    def _generate_id(self, length=9):
        """Optimal balance: fast comparisons + low collision risk"""
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _create(self) -> RapidataOrder:
        """
        Create the Rapidata order by making the necessary API calls based on the builder's configuration.

        Raises:
            ValueError: If both media paths and texts are provided, or if neither is provided.
            AssertionError: If the workflow is a CompareWorkflow and media paths are not in pairs.

        Returns:
            RapidataOrder: The created RapidataOrder instance.
        """
        order_model = self._to_model()
        logger.debug("Creating order with model: %s", order_model)

        result = self._openapi_service.order_api.order_post(
            create_order_model=order_model
        )

        order = RapidataOrder(
            order_id=str(result.order_id),
            openapi_service=self._openapi_service,
            name=self._name,
        )
        logger.debug("Order created: %s", order)

        if not result.dataset_id:
            logger.error("No Dataset was created for order %s", order.id)
            return order

        self._dataset = RapidataDataset(result.dataset_id, self._openapi_service)

        logger.debug("Dataset created with ID: %s", self._dataset.id)
        logger.debug("Adding datapoints to the order.")
        with tracer.start_as_current_span("add_datapoints"):
            _, failed_uploads = self._dataset.add_datapoints(self._datapoints)

            if failed_uploads:
                raise FailedUploadException(self._dataset, failed_uploads, order=order)

        logger.debug("Datapoints added to the order.")
        logger.debug("Setting order to preview")
        try:
            self._openapi_service.order_api.order_order_id_preview_post(order.id)
        except Exception:
            raise FailedUploadException(self._dataset, failed_uploads, order=order)
        return order

    def _set_workflow(self, workflow: Workflow) -> RapidataOrderBuilder:
        """
        Set the workflow for the order.

        Args:
            workflow (Workflow): The workflow to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(workflow, Workflow):
            raise TypeError("Workflow must be of type Workflow.")

        self._workflow = workflow
        return self

    def _set_referee(self, referee: Referee) -> "RapidataOrderBuilder":
        """
        Set the referee for the order.

        Args:
            referee (Referee): The referee to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(referee, Referee):
            raise TypeError("Referee must be of type Referee.")

        self._referee = referee
        return self

    def _set_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> RapidataOrderBuilder:
        """
        Set the datapoints for the order.

        Args:
            datapoints: (Sequence[Datapoint]): The datapoints to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(datapoints, list):
            raise TypeError(
                "Datapoints must be provided as a list of Datapoint objects."
            )

        self._datapoints = datapoints
        return self

    def _set_settings(
        self, settings: Sequence[RapidataSetting]
    ) -> RapidataOrderBuilder:
        """
        Set the settings for the order.

        Args:
            settings (Settings): The settings to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """

        if not isinstance(settings, list):
            raise TypeError("Settings must be provided as a list of Setting objects.")

        for s in settings:
            if not isinstance(s, RapidataSetting):
                raise TypeError("The settings list must only contain Setting objects.")

        self._settings = settings
        return self

    def _set_filters(self, filters: Sequence[RapidataFilter]) -> RapidataOrderBuilder:
        """
        Set the filters for the order, e.g., country, language, userscore, etc.

        Args:
            filters (Sequence[Filters]): The user filters to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(filters, list):
            raise TypeError("Filters must be provided as a list of Filter objects.")

        for f in filters:
            if not isinstance(f, RapidataFilter):
                raise TypeError("Filters must be of type Filter.")

        if len(self._user_filters) > 0:
            managed_print("Overwriting existing user filters.")

        self._user_filters = filters
        return self

    def _set_validation_set_id(
        self, validation_set_id: str | None = None
    ) -> RapidataOrderBuilder:
        """
        Set the validation set ID for the order.

        Args:
            validation_set_id (str): The validation set ID to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if validation_set_id is not None and not isinstance(validation_set_id, str):
            raise TypeError("Validation set ID must be of type str.")
        if validation_set_id is not None:
            self._validation_set = (
                self._validation_set_manager.get_validation_set_by_id(validation_set_id)
            )
            return self
        self._validation_set = validation_set_id
        return self

    def _set_selections(
        self, selections: Sequence[RapidataSelection]
    ) -> RapidataOrderBuilder:
        """
        Set the selections for the order.

        Args:
            selections (Sequence[Selection]): The selections to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(selections, list):
            raise TypeError(
                "Selections must be provided as a list of Selection objects."
            )

        for selection in selections:
            if not isinstance(selection, RapidataSelection):
                raise TypeError("Selections must be of type Selection.")

        self._selections = selections  # type: ignore
        return self

    def _set_priority(self, priority: int | None = None) -> RapidataOrderBuilder:
        """
        Set the priority for the order.

        Args:
            priority (int): The priority to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if priority is not None and not isinstance(priority, int):
            raise TypeError("Priority must be of type int.")

        self._priority = priority
        return self

    def _set_sticky_state(
        self, sticky_state: StickyStateLiteral | None = None
    ) -> RapidataOrderBuilder:
        """
        Set the sticky state for the order.
        """
        sticky_state_valid_values = get_args(StickyStateLiteral)

        if sticky_state is not None and sticky_state not in sticky_state_valid_values:
            raise ValueError(
                f"Sticky state must be one of {sticky_state_valid_values} or None"
            )

        self._sticky_state_value = sticky_state
        return self
