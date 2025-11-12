from typing import Literal, Optional, Sequence, get_args, cast
import random
import secrets

from rapidata.api_client.models.ab_test_selection_a_inner import AbTestSelectionAInner
from rapidata.api_client.models.and_user_filter_model_filters_inner import (
    AndUserFilterModelFiltersInner,
)
from rapidata.api_client.models.create_order_model import CreateOrderModel
from rapidata.api_client.models.create_order_model_referee import (
    CreateOrderModelReferee,
)
from rapidata.api_client.models.create_order_model_workflow import (
    CreateOrderModelWorkflow,
)
from rapidata.api_client.models.sticky_state import StickyState

from rapidata.rapidata_client.datapoints._datapoint import Datapoint
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
from rapidata.rapidata_client.order.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee import Referee
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.settings import RapidataSetting
from rapidata.rapidata_client.workflow import (
    Workflow,
    CompareWorkflow,
    ClassifyWorkflow,
)
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
        self.__dataset: Optional[RapidataDataset] = None
        self.__workflow: Workflow | None = None
        self.__referee: Referee | None = None
        self.__validation_set: RapidataValidationSet | None = None
        self.__settings: Sequence[RapidataSetting] | None = None
        self.__user_filters: list[RapidataFilter] = []
        self.__selections: Sequence[RapidataSelection] = []
        self.__priority: int | None = None
        self.__datapoints: list[Datapoint] = []
        self.__sticky_state_value: StickyStateLiteral | None = None
        self.__temporary_sticky_enabled: bool = False
        self.__validation_set_manager: ValidationSetManager = ValidationSetManager(
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
        if self.__workflow is None:
            raise ValueError("You must provide a workflow to create an order.")

        if self.__referee is None:
            managed_print("No referee provided, using default NaiveReferee.")
            self.__referee = NaiveReferee()

        sticky_state = self.__sticky_state_value
        if not sticky_state and self.__temporary_sticky_enabled:
            sticky_state = "Temporary"
            logger.debug(
                "Setting sticky state to Temporary due to temporary sticky enabled."
            )

        return CreateOrderModel(
            _t="CreateOrderModel",
            orderName=self._name,
            workflow=CreateOrderModelWorkflow(self.__workflow._to_model()),
            userFilters=[
                AndUserFilterModelFiltersInner(user_filter._to_model())
                for user_filter in self.__user_filters
            ],
            referee=CreateOrderModelReferee(self.__referee._to_model()),
            validationSetId=self.__validation_set.id if self.__validation_set else None,
            featureFlags=(
                [setting._to_feature_flag() for setting in self.__settings]
                if self.__settings is not None
                else None
            ),
            selections=(
                [
                    AbTestSelectionAInner(selection._to_model())
                    for selection in self.__selections
                ]
                if self.__selections
                else None
            ),
            priority=self.__priority,
            stickyState=(StickyState(sticky_state) if sticky_state else None),
        )

    def _generate_id(self, length=9):
        """Optimal balance: fast comparisons + low collision risk"""
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _set_validation_set_id(self) -> None:
        """
        Get the validation set ID for the order.
        """
        assert self.__workflow is not None

        required_amount = min(int(len(self.__datapoints) * 0.01) or 3, 15)

        if self.__validation_set is None:
            try:
                with suppress_rapidata_error_logging():
                    val_set_id = (
                        (
                            self._openapi_service.validation_api.validation_set_recommended_get(
                                asset_type=[self.__datapoints[0].get_asset_type()],
                                modality=[self.__workflow.modality],
                                instruction=self.__workflow._get_instruction(),
                                prompt_type=[
                                    t.value
                                    for t in self.__datapoints[0].get_prompt_type()
                                ],
                            )
                        )
                        .validation_sets[0]
                        .id
                    )
                    self.__validation_set = (
                        self.__validation_set_manager.get_validation_set_by_id(
                            val_set_id
                        )
                    )

            except Exception as e:
                logger.debug("No recommended validation set found, error: %s", e)

        sufficient_rapids_count = False
        if self.__validation_set is not None:
            sufficient_rapids_count = (
                self.__validation_set_manager._get_total_and_labeled_rapids_count(
                    self.__validation_set.id
                )[1]
                >= required_amount
            )

        if self.__validation_set is None or not sufficient_rapids_count:
            if (
                len(self.__datapoints)
                < rapidata_config.order.minOrderDatapointsForValidation
            ):
                logger.debug(
                    "No recommended validation set found, dataset too small to create one."
                )
                return

            logger.info("No recommended validation set found, creating new one.")
            managed_print()
            managed_print(
                f"No recommended validation set found, new one will be created."
            )

            new_dimension = self._generate_id()
            logger.debug("New dimension created: %s", new_dimension)
            rng = random.Random(42)
            self.__validation_set = (
                self.__validation_set_manager._create_order_validation_set(
                    workflow=self.__workflow,
                    name=self._name,
                    datapoints=rng.sample(
                        self.__datapoints, len(self.__datapoints)
                    ),  # shuffle the datapoints with a specific seed
                    required_amount=required_amount,
                    settings=self.__settings,
                    dimensions=[new_dimension],
                )
            )

        self.__validation_set.update_should_alert(False)
        self.__validation_set.update_can_be_flagged(False)

        logger.debug("New validation set created for order: %s", self.__validation_set)

        self.__selections = [
            CappedSelection(
                selections=[
                    ConditionalValidationSelection(
                        validation_set_id=self.__validation_set.id,
                        dimensions=self.__validation_set.dimensions,
                        thresholds=[0, 0.5, 0.7],
                        chances=[1, 1, 0.2],
                        rapid_counts=[10, 1, 1],
                    ),
                    LabelingSelection(amount=1),
                ],
                max_rapids=3,
            )
        ]

        for dimension in self.__validation_set.dimensions:
            self.__user_filters.append(
                UserScoreFilter(
                    lower_bound=0.3,
                    upper_bound=1,
                    dimension=dimension,
                )
            )

    def _create(self) -> RapidataOrder:
        """
        Create the Rapidata order by making the necessary API calls based on the builder's configuration.

        Raises:
            ValueError: If both media paths and texts are provided, or if neither is provided.
            AssertionError: If the workflow is a CompareWorkflow and media paths are not in pairs.

        Returns:
            RapidataOrder: The created RapidataOrder instance.
        """
        if (
            rapidata_config.order.autoValidationSetCreation
            and isinstance(self.__workflow, (CompareWorkflow, ClassifyWorkflow))
            and not self.__selections
            and rapidata_config.enableBetaFeatures
        ):
            self._set_validation_set_id()
            self.__temporary_sticky_enabled = True
            logger.debug("Temporary sticky enabled for order creation.")

        order_model = self._to_model()
        logger.debug("Creating order with model: %s", order_model)

        self.__temporary_sticky_enabled = False
        logger.debug("Disabling temporary sticky after order creation.")

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

        self.__dataset = RapidataDataset(result.dataset_id, self._openapi_service)

        logger.debug("Dataset created with ID: %s", self.__dataset.id)
        logger.debug("Adding datapoints to the order.")
        with tracer.start_as_current_span("add_datapoints"):
            _, failed_uploads = self.__dataset.add_datapoints(self.__datapoints)

            if failed_uploads:
                raise FailedUploadException(self.__dataset, order, failed_uploads)

        logger.debug("Datapoints added to the order.")
        logger.debug("Setting order to preview")
        try:
            self._openapi_service.order_api.order_order_id_preview_post(order.id)
        except Exception:
            raise FailedUploadException(self.__dataset, order, failed_uploads)
        return order

    def _workflow(self, workflow: Workflow) -> "RapidataOrderBuilder":
        """
        Set the workflow for the order.

        Args:
            workflow (Workflow): The workflow to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(workflow, Workflow):
            raise TypeError("Workflow must be of type Workflow.")

        self.__workflow = workflow
        return self

    def _referee(self, referee: Referee) -> "RapidataOrderBuilder":
        """
        Set the referee for the order.

        Args:
            referee (Referee): The referee to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(referee, Referee):
            raise TypeError("Referee must be of type Referee.")

        self.__referee = referee
        return self

    def _datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> "RapidataOrderBuilder":
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

        self.__datapoints = datapoints
        return self

    def _settings(self, settings: Sequence[RapidataSetting]) -> "RapidataOrderBuilder":
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

        self.__settings = settings
        return self

    def _filters(self, filters: Sequence[RapidataFilter]) -> "RapidataOrderBuilder":
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

        if len(self.__user_filters) > 0:
            managed_print("Overwriting existing user filters.")

        self.__user_filters = filters
        return self

    def _validation_set_id(
        self, validation_set_id: str | None = None
    ) -> "RapidataOrderBuilder":
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
            self.__validation_set = (
                self.__validation_set_manager.get_validation_set_by_id(
                    validation_set_id
                )
            )
            return self
        self.__validation_set = validation_set_id
        return self

    def _rapids_per_bag(self, amount: int) -> "RapidataOrderBuilder":
        """
        Define the number of tasks a user sees in a single session.

        Args:
            amount (int): The number of tasks a user sees in a single session.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.

        Raises:
            NotImplementedError: This method is not implemented yet.
        """
        raise NotImplementedError("Not implemented yet.")

    def _selections(
        self, selections: Sequence[RapidataSelection]
    ) -> "RapidataOrderBuilder":
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

        self.__selections = selections  # type: ignore
        return self

    def _priority(self, priority: int | None = None) -> "RapidataOrderBuilder":
        """
        Set the priority for the order.

        Args:
            priority (int): The priority to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if priority is not None and not isinstance(priority, int):
            raise TypeError("Priority must be of type int.")

        self.__priority = priority
        return self

    def _sticky_state(
        self, sticky_state: StickyStateLiteral | None = None
    ) -> "RapidataOrderBuilder":
        """
        Set the sticky state for the order.
        """
        sticky_state_valid_values = get_args(StickyStateLiteral)

        if sticky_state is not None and sticky_state not in sticky_state_valid_values:
            raise ValueError(
                f"Sticky state must be one of {sticky_state_valid_values} or None"
            )

        self.__sticky_state_value = sticky_state
        return self
