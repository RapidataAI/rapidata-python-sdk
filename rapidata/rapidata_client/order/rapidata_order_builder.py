from openapi_client.api_client import ApiClient
from rapidata.rapidata_client.feature_flags import FeatureFlags
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from openapi_client import ApiClient
from rapidata.rapidata_client.referee import Referee


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
        api_client: ApiClient,
        name: str,
    ):
        self._name = name
        self._api_client = api_client
        self._workflow: Workflow | None = None
        self._referee: Referee | None = None
        self._media_paths: list[str] = []
        self._feature_flags = FeatureFlags()

    def create(self) -> RapidataOrder:
        """
        Create a RapidataOrder instance based on the configured settings.

        :return: The created RapidataOrder instance.
        :rtype: RapidataOrder
        :raises ValueError: If no workflow is provided.
        """
        if self._workflow is None:
            raise ValueError("You must provide a blueprint to create an order.")

        if self._referee is None:
            print("No referee provided, using default NaiveReferee.")
            self._referee = NaiveReferee()

        order = RapidataOrder(
            name=self._name,
            workflow=self._workflow,
            referee=self._referee,
            api_client=self._api_client,
        ).create()

        order.dataset.add_media_from_paths(self._media_paths)

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

    def media(self, media_paths: list[str]):
        """
        Set the media assets for the order.

        :param media_paths: The paths of the media assets to be set.
        :type media_paths: list[str]
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._media_paths = media_paths
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
