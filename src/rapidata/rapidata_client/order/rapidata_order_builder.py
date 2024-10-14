from rapidata.api_client.models.aggregator_type import AggregatorType
from rapidata.api_client.models.capped_selection_selections_inner import (
    CappedSelectionSelectionsInner,
)
from rapidata.api_client.models.create_order_model import CreateOrderModel
from rapidata.api_client.models.create_order_model_referee import (
    CreateOrderModelReferee,
)
from rapidata.api_client.models.create_order_model_user_filters_inner import (
    CreateOrderModelUserFiltersInner,
)
from rapidata.api_client.models.create_order_model_workflow import (
    CreateOrderModelWorkflow,
)
from rapidata.api_client.models.country_user_filter_model import CountryUserFilterModel
from rapidata.rapidata_client.feature_flags import FeatureFlags
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.rapidata_client.dataset.rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee import Referee
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.workflow.compare_workflow import CompareWorkflow


class RapidataOrderBuilder:
    """Builder object for creating Rapidata orders.

    Use the fluent interface to set the desired configuration. Add a workflow to the order using `.workflow()` and finally call `.create()` to create the order.

    Args:
        openapi_service (OpenAPIService): The OpenAPIService instance.
        name (str): The name of the order.
    """

    def __init__(
        self,
        openapi_service: OpenAPIService,
        name: str,
    ):
        """
        Initialize the RapidataOrderBuilder.

        Args:
            openapi_service (OpenAPIService): The OpenAPIService instance.
            name (str): The name of the order.
        """
        self._name = name
        self._openapi_service = openapi_service
        self._workflow: Workflow | None = None
        self._referee: Referee | None = None
        self._media_paths: list[str | list[str]] = []
        self._metadata: list[Metadata] | None = None
        self._aggregator: AggregatorType | None = None
        self._validation_set_id: str | None = None
        self._feature_flags: FeatureFlags | None = None
        self._country_codes: list[str] | None = None
        self._selections: list[Selection] = []
        self._rapids_per_bag: int = 2
        self._priority: int = 50
        self._texts: list[str] | None = None
        self._media_paths: list[str | list[str]] = []

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
            print("No referee provided, using default NaiveReferee.")
            self._referee = NaiveReferee()
        if self._country_codes is None:
            country_filter = None
        else:
            country_filter = CountryUserFilterModel(
                _t="CountryFilter", countries=self._country_codes
            )

        return CreateOrderModel(
            _t="CreateOrderModel",
            orderName=self._name,
            workflow=CreateOrderModelWorkflow(self._workflow.to_model()),
            userFilters=(
                [CreateOrderModelUserFiltersInner(country_filter)]
                if country_filter
                else []
            ),
            referee=CreateOrderModelReferee(self._referee.to_model()),
            validationSetId=self._validation_set_id,
            featureFlags=(
                self._feature_flags.to_list()
                if self._feature_flags is not None
                else None
            ),
            selections=[
                CappedSelectionSelectionsInner(selection.to_model())
                for selection in self._selections
            ],
            priority=self._priority,
        )

    def create(self, submit: bool = True, max_workers: int = 10) -> RapidataOrder:
        """
        Create the Rapidata order by making the necessary API calls based on the builder's configuration.

        Args:
            submit (bool, optional): Whether to submit the order upon creation. Defaults to True.
            max_workers (int, optional): The maximum number of worker threads for processing media paths. Defaults to 10.

        Raises:
            ValueError: If both media paths and texts are provided, or if neither is provided.
            AssertionError: If the workflow is a CompareWorkflow and media paths are not in pairs.

        Returns:
            RapidataOrder: The created RapidataOrder instance.
        """
        order_model = self._to_model()
        if isinstance(
            self._workflow, CompareWorkflow
        ):  # Temporary fix; will be handled by backend in the future
            assert all(
                [len(path) == 2 for path in self._media_paths]
            ), "The media paths must come in pairs for comparison tasks."

        result = self._openapi_service.order_api.order_create_post(
            create_order_model=order_model
        )

        self.order_id = result.order_id
        self._dataset = RapidataDataset(result.dataset_id, self._openapi_service)
        order = RapidataOrder(
            order_id=self.order_id,
            dataset=self._dataset,
            openapi_service=self._openapi_service,
        )

        if self._media_paths and self._texts:
            raise ValueError(
                "You cannot provide both media paths and texts to the same order."
            )

        if not self._media_paths and not self._texts:
            raise ValueError(
                "You must provide either media paths or texts to the order."
            )

        if self._texts:
            order.dataset.add_texts(self._texts)

        if self._media_paths:
            order.dataset.add_media_from_paths(
                self._media_paths, self._metadata, max_workers
            )

        if submit:
            order.submit()

        return order

    def workflow(self, workflow: Workflow) -> "RapidataOrderBuilder":
        """
        Set the workflow for the order.

        Args:
            workflow (Workflow): The workflow to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._workflow = workflow
        return self

    def referee(self, referee: Referee) -> "RapidataOrderBuilder":
        """
        Set the referee for the order.

        Args:
            referee (Referee): The referee to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._referee = referee
        return self

    def media(
        self,
        media_paths: list[str | list[str]],
        metadata: list[Metadata] | None = None,
    ) -> "RapidataOrderBuilder":
        """
        Set the media assets for the order.

        Args:
            media_paths (list[str | list[str]]): The paths of the media assets to be set.
            metadata (list[Metadata] | None, optional): Metadata for the media assets. Defaults to None.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._media_paths = media_paths
        self._metadata = metadata
        return self

    def texts(self, texts: list[str]) -> "RapidataOrderBuilder":
        """
        Set the TextAssets for the order.

        Args:
            texts (list[str]): The texts to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._texts = texts
        return self

    def feature_flags(self, feature_flags: FeatureFlags) -> "RapidataOrderBuilder":
        """
        Set the feature flags for the order.

        Args:
            feature_flags (FeatureFlags): The feature flags to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._feature_flags = feature_flags
        return self

    def country_filter(self, country_codes: list[str]) -> "RapidataOrderBuilder":
        """
        Set the target country codes for the order.

        Args:
            country_codes (list[str]): The country codes to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._country_codes = country_codes
        return self

    def aggregator(self, aggregator: AggregatorType) -> "RapidataOrderBuilder":
        """
        Set the aggregator for the order.

        Args:
            aggregator (AggregatorType): The aggregator to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._aggregator = aggregator
        return self

    def validation_set_id(self, validation_set_id: str) -> "RapidataOrderBuilder":
        """
        Set the validation set ID for the order.

        Args:
            validation_set_id (str): The validation set ID to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._validation_set_id = validation_set_id
        return self

    def rapids_per_bag(self, amount: int) -> "RapidataOrderBuilder":
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

    def selections(self, selections: list[Selection]) -> "RapidataOrderBuilder":
        """
        Set the selections for the order.

        Args:
            selections (list[Selection]): The selections to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._selections = selections
        return self

    def priority(self, priority: int) -> "RapidataOrderBuilder":
        """
        Set the priority for the order.

        Args:
            priority (int): The priority to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        self._priority = priority
        return self
