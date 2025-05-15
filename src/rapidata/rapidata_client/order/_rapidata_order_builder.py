from rapidata.api_client.models.ab_test_selection_a_inner import (
    AbTestSelectionAInner,
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

from rapidata.rapidata_client.settings import RapidataSetting
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee import Referee
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.workflow._compare_workflow import CompareWorkflow

from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset, BaseAsset

from typing import Optional, cast, Sequence

from rapidata.rapidata_client.logging import logger, managed_print


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
        self.order_id: str | None = None
        self.__openapi_service = openapi_service
        self.__dataset: Optional[RapidataDataset]
        self.__workflow: Workflow | None = None
        self.__referee: Referee | None = None
        self.__multi_metadata: Sequence[Sequence[Metadata]] | None = None
        self.__validation_set_id: str | None = None
        self.__settings: Sequence[RapidataSetting] | None = None
        self.__user_filters: list[RapidataFilter] = []
        self.__selections: list[RapidataSelection] = []
        self.__priority: int = 50
        self.__assets: Sequence[BaseAsset] = []

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

        return CreateOrderModel(
            _t="CreateOrderModel",
            orderName=self._name,
            workflow=CreateOrderModelWorkflow(self.__workflow._to_model()),
            userFilters=[
                CreateOrderModelUserFiltersInner(user_filter._to_model())
                for user_filter in self.__user_filters
            ],
            referee=CreateOrderModelReferee(self.__referee._to_model()),
            validationSetId=self.__validation_set_id,
            featureFlags=(
                [setting._to_feature_flag() for setting in self.__settings]
                if self.__settings is not None
                else None
            ),
            selections=[
                AbTestSelectionAInner(selection._to_model())
                for selection in self.__selections
            ],
            priority=self.__priority,
        )

    def _create(self, max_upload_workers: int = 10) -> RapidataOrder:
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
        logger.debug(f"Creating order with model: {order_model}")
        if isinstance(
            self.__workflow, CompareWorkflow
        ):  # Temporary fix; will be handled by backend in the future
            assert all(
                isinstance(item, MultiAsset) for item in self.__assets
            ), "The media paths must be of type MultiAsset for comparison tasks."

        result = self.__openapi_service.order_api.order_post(
            create_order_model=order_model
        )

        self.order_id = str(result.order_id)
        logger.debug(f"Order created with ID: {self.order_id}")

        self.__dataset = (
            RapidataDataset(result.dataset_id, self.__openapi_service)
            if result.dataset_id
            else None
        )
        if self.__dataset:
            logger.debug(f"Dataset created with ID: {self.__dataset.dataset_id}")
        else:
            logger.warning("No dataset created for this order.")

        order = RapidataOrder(
            order_id=self.order_id,
            openapi_service=self.__openapi_service,
            name=self._name,
        )

        logger.debug(f"Order created: {order}")
        logger.debug("Adding media to the order.")

        if all(isinstance(item, MediaAsset) for item in self.__assets) and self.__dataset:
            assets = cast(list[MediaAsset], self.__assets)
            self.__dataset._add_media_from_paths(assets, self.__multi_metadata, max_upload_workers)

        elif (
            all(isinstance(item, TextAsset) for item in self.__assets) and self.__dataset
        ):
            assets = cast(list[TextAsset], self.__assets)
            self.__dataset._add_texts(assets, self.__multi_metadata)

        elif (
            all(isinstance(item, MultiAsset) for item in self.__assets) and self.__dataset
        ):
            multi_assets = cast(list[MultiAsset], self.__assets)

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
                self.__dataset._add_media_from_paths(
                    multi_assets, self.__multi_metadata, max_upload_workers
                )

            elif issubclass(first_asset_type, TextAsset):
                self.__dataset._add_texts(multi_assets, self.__multi_metadata)

            else:
                raise ValueError(
                    "MultiAsset must contain MediaAssets or TextAssets objects."
                )

        elif self.__dataset:
            raise ValueError(
                "Media paths must all be of the same type: MediaAsset, TextAsset, or MultiAsset."
            )
        
        logger.debug("Media added to the order.")
        logger.debug("Setting order to preview")
        self.__openapi_service.order_api.order_order_id_preview_post(self.order_id)

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

    def _media(
        self,
        assets: Sequence[BaseAsset],
        multi_metadata: Sequence[Sequence[Metadata]] | None = None,
    ) -> "RapidataOrderBuilder":
        """
        Set the media assets for the order.

        Args:
            assets: (list[MediaAsset] | list[TextAsset] | list[MultiAsset]): The paths of the media assets to be set.
            multi_metadata: (list[list[Metadata]] | None, optional): Metadatas for the media assets. Defaults to None.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(assets, list):
            raise TypeError("Media paths must be provided as a list of paths.")

        for a in assets:
            if not isinstance(a, (MediaAsset, TextAsset, MultiAsset)):
                raise TypeError(
                    "Media paths must be of type MediaAsset, TextAsset, or MultiAsset."
                )

        if multi_metadata:
            for data in multi_metadata:
                if not isinstance(data, list):
                    raise TypeError("Metadata must be provided as a list of Metadata objects.")
                for d in data:
                    if not isinstance(d, Metadata):
                        raise TypeError("Metadata must be of type Metadata.")

        if multi_metadata and not len(multi_metadata) == len(assets):
            raise ValueError("The number of assets must match the number of metadatas.")
        
        if multi_metadata and not all(len(data) == len(multi_metadata[0]) for data in multi_metadata):
            raise ValueError("All metadatas must have the same length.")

        self.__assets = assets
        self.__multi_metadata = multi_metadata
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

    def _validation_set_id(self, validation_set_id: str) -> "RapidataOrderBuilder":
        """
        Set the validation set ID for the order.

        Args:
            validation_set_id (str): The validation set ID to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(validation_set_id, str):
            raise TypeError("Validation set ID must be of type str.")

        self.__validation_set_id = validation_set_id
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

    def _selections(self, selections: Sequence[RapidataSelection]) -> "RapidataOrderBuilder":
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

    def _priority(self, priority: int) -> "RapidataOrderBuilder":
        """
        Set the priority for the order.

        Args:
            priority (int): The priority to be set.

        Returns:
            RapidataOrderBuilder: The updated RapidataOrderBuilder instance.
        """
        if not isinstance(priority, int):
            raise TypeError("Priority must be of type int.")

        self.__priority = priority
        return self
