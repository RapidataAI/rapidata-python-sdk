from warnings import warn

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

from rapidata.rapidata_client.settings import RapidataSettings, RapidataSetting, TranslationBehaviour
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.rapidata_client.order.rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.selection.base_selection import RapidataSelection
from rapidata.rapidata_client.filter import RapidataFilter, CountryFilter, LanguageFilter
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee import Referee
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.workflow.compare_workflow import CompareWorkflow

from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset, BaseAsset

from typing import Optional, cast, Sequence

from deprecated import deprecated


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
        """
        Initialize the RapidataOrderBuilder.

        Args:
            openapi_service (OpenAPIService): The OpenAPIService instance.
            name (str): The name of the order.
        """
        self._name = name
        self.order_id: str | None = None
        self._openapi_service = openapi_service
        self._dataset: Optional[RapidataDataset]
        self._workflow: Workflow | None = None
        self._referee: Referee | None = None
        self._metadata: Sequence[Metadata] | None = None
        self._aggregator: AggregatorType | None = None
        self._validation_set_id: str | None = None
        self._settings: Sequence[RapidataSetting] | None = None
        self._user_filters: list[RapidataFilter] = []
        self._selections: list[RapidataSelection] = []
        self._rapids_per_bag: int = 2
        self._priority: int = 50
        self._assets: Sequence[BaseAsset] = []

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

        return CreateOrderModel(
            _t="CreateOrderModel",
            orderName=self._name,
            workflow=CreateOrderModelWorkflow(self._workflow.to_model()),
            userFilters=[
                CreateOrderModelUserFiltersInner(user_filter.to_model())
                for user_filter in self._user_filters
            ],
            referee=CreateOrderModelReferee(self._referee.to_model()),
            validationSetId=self._validation_set_id,
            featureFlags=(
                [setting.to_feature_flag() for setting in self._settings]
                if self._settings is not None
                else None
            ),
            selections=[
                CappedSelectionSelectionsInner(selection.to_model())
                for selection in self._selections
            ],
            priority=self._priority,
        )

    def create(self, max_upload_workers: int = 10) -> RapidataOrder:
        """
        Create the Rapidata order by making the necessary API calls based on the builder's configuration.

        Args:
            max_upload_workers (int, optional): The maximum number of worker threads for processing media paths. Defaults to 10.

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
                isinstance(item, MultiAsset) for item in self._assets
            ), "The media paths must be of type MultiAsset for comparison tasks."

        result = self._openapi_service.order_api.order_create_post(
            create_order_model=order_model
        )

        self.order_id = result.order_id

        self._dataset = (
            RapidataDataset(result.dataset_id, self._openapi_service)
            if result.dataset_id
            else None
        )

        order = RapidataOrder(
            order_id=self.order_id,
            dataset=self._dataset,
            openapi_service=self._openapi_service,
            name=self._name,
        )

        if all(isinstance(item, MediaAsset) for item in self._assets) and order.dataset:
            assets = cast(list[MediaAsset], self._assets)
            order.dataset.add_media_from_paths(assets, self._metadata, max_upload_workers)

        elif (
            all(isinstance(item, TextAsset) for item in self._assets) and order.dataset
        ):
            assets = cast(list[TextAsset], self._assets)
            order.dataset.add_texts(assets)

        elif (
            all(isinstance(item, MultiAsset) for item in self._assets) and order.dataset
        ):
            multi_assets = cast(list[MultiAsset], self._assets)

            # Check if all MultiAssets contain the same type of assets
            first_asset_type = type(multi_assets[0].assets[0])
            if not all(
                isinstance(asset, first_asset_type)
                for multi_asset in multi_assets
                for asset in multi_asset.assets
            ):
                raise ValueError(
                    "All MultiAssets must contain the same type of assets (either all MediaAssets or all TextAssets)."
                )

            # Process based on the asset type
            if issubclass(first_asset_type, MediaAsset):
                order.dataset.add_media_from_paths(
                    multi_assets, self._metadata, max_upload_workers
                )

            elif issubclass(first_asset_type, TextAsset):
                order.dataset.add_texts(multi_assets)

            else:
                raise ValueError(
                    "MultiAsset must contain MediaAssets or TextAssets objects."
                )

        elif order.dataset:
            raise ValueError(
                "Media paths must all be of the same type: MediaAsset, TextAsset, or MultiAsset."
            )

        return order

    def workflow(self, workflow: Workflow) -> "RapidataOrderBuilder":
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

    def referee(self, referee: Referee) -> "RapidataOrderBuilder":
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

    def media(
        self,
        asset: Sequence[BaseAsset],
        metadata: Sequence[Metadata] | None = None,
    ) -> "RapidataOrderBuilder":
        """
        Set the media assets for the order.

        Args:
            media_paths (list[MediaAsset] | list[TextAsset] | list[MultiAsset]): The paths of the media assets to be set.
            metadata (list[Metadata] | None, optional): Metadata for the media assets. Defaults to None.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(asset, list):
            raise TypeError("Media paths must be provided as a list of paths.")

        # for a in asset:
        #     if not isinstance(a, (MediaAsset, TextAsset, MultiAsset)):
        #         raise TypeError(
        #             "Media paths must be of type MediaAsset, TextAsset, or MultiAsset."
        #         )

        if metadata:
            for data in metadata:
                if not isinstance(data, Metadata):
                    raise TypeError("Metadata must be of type Metadata.")

        self._assets = asset
        self._metadata = metadata
        return self

    def settings(self, settings: Sequence[RapidataSetting]) -> "RapidataOrderBuilder":
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

    def filters(self, filters: Sequence[RapidataFilter]) -> "RapidataOrderBuilder":
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
            print("Overwriting existing user filters.")

        self._user_filters = filters
        return self

    def aggregator(self, aggregator: AggregatorType) -> "RapidataOrderBuilder":
        """
        Set the aggregator for the order.

        Args:
            aggregator (AggregatorType): The aggregator to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(aggregator, AggregatorType):
            raise TypeError("Aggregator must be of type AggregatorType.")

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
        if not isinstance(validation_set_id, str):
            raise TypeError("Validation set ID must be of type str.")

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

    def selections(self, selections: Sequence[RapidataSelection]) -> "RapidataOrderBuilder":
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

    def priority(self, priority: int) -> "RapidataOrderBuilder":
        """
        Set the priority for the order.

        Args:
            priority (int): The priority to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(priority, int):
            raise TypeError("Priority must be of type int.")

        self._priority = priority
        return self
