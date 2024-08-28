from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.models.aggregator_type import AggregatorType
from rapidata.api_client.models.create_order_model import CreateOrderModel
from rapidata.api_client.models.create_order_model_referee import CreateOrderModelReferee
from rapidata.api_client.models.create_order_model_workflow import CreateOrderModelWorkflow
from rapidata.rapidata_client.feature_flags import FeatureFlags
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.rapidata_client.order.dataset.rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee import Referee
from rapidata.service.openapi_service import OpenAPIService


class RapidataOrderBuilder:
    """
    Builder object for creating Rapidata orders.

    Use the fluent interface to set the desired configuration. Add a workflow to the order using `.workflow()` and finally call `.create()` to create the order.

    :param rapidata_service: The RapidataService instance.
    :type rapidata_service: RapidataService
    :param name: The name of the order.
    :type name: str
    """

    def __init__(
        self,
        openapi_service: OpenAPIService,
        name: str,
    ):
        self._name = name
        self._openapi_service = openapi_service
        self._workflow: Workflow | None = None
        self._referee: Referee | None = None
        self._media_paths: list[str] = []
        self._metadata: list[Metadata] | None = None 
        self._aggregator: AggregatorType | None = None
        self._validation_set_id: str | None = None
        self._feature_flags: FeatureFlags | None = None

    def create(self, submit=True) -> RapidataOrder:
        """
        Actually makes the API calls to create the order based on how the order builder was configures. Returns a RapidataOrder instance based on the created order with order_id and dataset_id.

        :return: The created RapidataOrder instance.
        :rtype: RapidataOrder
        :raises ValueError: If no workflow is provided.
        """
        if self._workflow is None:
            raise ValueError("You must provide a blueprint to create an order.")

        if self._referee is None:
            print("No referee provided, using default NaiveReferee.")
            self._referee = NaiveReferee()

        order_model = CreateOrderModel(
            orderName=self._name,
            workflow=CreateOrderModelWorkflow(self._workflow.to_model()),
            userFilters=[],
            referee=CreateOrderModelReferee(self._referee.to_model()),
            validationSetId=self._validation_set_id,
            featureFlags=self._feature_flags.to_list() if self._feature_flags is not None else None,
        )

        result = self._openapi_service.order_api.order_create_post(
            create_order_model=order_model
        )

        self.order_id = result.order_id
        self._dataset = RapidataDataset(result.dataset_id, self._openapi_service)
        order = RapidataOrder(order_id=self.order_id, dataset=self._dataset, openapi_service=self._openapi_service)

        order.dataset.add_media_from_paths(self._media_paths, self._metadata)

        if submit:
            order.submit()

        return order

    def workflow(self, workflow: Workflow):
        """
        Set the workflow for the order.

        :param workflow: The workflow to be set.
        :type workflow: Workflow
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._workflow = workflow
        return self

    def referee(self, referee: Referee):
        """
        Set the referee for the order.

        :param referee: The referee to be set.
        :type referee: Referee
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._referee = referee
        return self

    def media(
        self, media_paths: list[str], metadata: list[Metadata] | None = None):
        """
        Set the media assets for the order.

        :param media_paths: The paths of the media assets to be set.
        :type media_paths: list[str]
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._media_paths = media_paths
        self._metadata = metadata
        return self

    def feature_flags(self, feature_flags: FeatureFlags):
        """
        Set the feature flags for the order.

        :param feature_flags: The feature flags to be set.
        :type feature_flags: FeatureFlags
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._feature_flags = feature_flags
        return self

    def target_country_codes(self, country_codes: list[str]):
        """
        Set the target country codes for the order.

        :param country_codes: The country codes to be set.
        :type country_codes: list[str]
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        if self._workflow is None:
            raise ValueError(
                "You must set the workflow before setting the target country codes."
            )

        self._workflow.target_country_codes(country_codes)
        return self

    def aggregator(self, aggregator: AggregatorType):
        """
        Set the aggregator for the order.

        :param aggregator: The aggregator to be set.
        :type aggregator: AggregatorType
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._aggregator = aggregator
        return self
    
    def validation_set(self, validation_set_id: str):
        """
        Set the validation set for the order.

        :param validation_set_id: The validation set ID to be set.
        :type validation_set_id: str
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._validation_set_id = validation_set_id
        return self
