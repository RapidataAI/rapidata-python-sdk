from rapidata.rapidata_client.dataset.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.dataset.validation_set_builder import ValidationSetBuilder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.dataset.rapidata_dataset import RapidataDataset

from rapidata.rapidata_client.simple_builders.simple_classification_builders import ClassificationQuestionBuilder
from rapidata.rapidata_client.simple_builders.simple_compare_builders import CompareCriteriaBuilder

from rapidata.api_client.exceptions import BadRequestException
from urllib3._collections import HTTPHeaderDict

from rapidata.api_client.models.query_orders_model import QueryOrdersModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion

from rapidata.api_client.models.query_validation_set_model import QueryValidationSetModel


class RapidataClient:
    """The Rapidata client is the main entry point for interacting with the Rapidata API. It allows you to create orders and validation sets. For creating a new order, check out `new_order()`. For creating a new validation set, check out `new_validation_set()`."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://api.rapidata.ai",
        token_url: str = "https://auth.rapidata.ai/connect/token",
        oauth_scope: str = "openid",
        cert_path: str | None = None,
    ):
        """Initialize the RapidataClient. Best practice is to store the client ID and client secret in environment variables. Ask your Rapidata representative for the client ID and client secret.

        Args:
            client_id (str): The client ID for authentication.
            client_secret (str): The client secret for authentication.
            endpoint (str, optional): The API endpoint URL.
        """
        self.openapi_service = OpenAPIService(
            client_id=client_id,
            client_secret=client_secret,
            endpoint=endpoint,
            token_url=token_url,
            oauth_scope=oauth_scope,
            cert_path=cert_path
        )

    def new_order(self, name: str) -> RapidataOrderBuilder:
        """Create a new order using a RapidataOrderBuilder instance.

        Args:
            name (str): The name of the order.

        Returns:
            RapidataOrderBuilder: A RapidataOrderBuilder instance.
        """
        return RapidataOrderBuilder(openapi_service=self.openapi_service, name=name)

    def new_validation_set(self, name: str) -> ValidationSetBuilder:
        """Create a new validation set using a ValidationDatasetBuilder instance.

        Args:
            name (str): The name of the validation set.

        Returns:
            ValidationSetBuilder: A ValidationDatasetBuilder instance.
        """
        return ValidationSetBuilder(name=name, openapi_service=self.openapi_service)

    def get_order(self, order_id: str) -> RapidataOrder:
        """Get an order by ID.

        Args:
            order_id (str): The ID of the order.

        Returns:
            RapidataOrder: The Order instance.
        """

        # TODO: check the pipeline for the dataset id - not really necessary atm
        # order = self.openapi_service.order_api.order_get_by_id_get(order_id)
        # pipeline = self.openapi_service..pipeline_get_by_id_get(order.pipeline_id)
        try:
            order = self.openapi_service.order_api.order_get_by_id_get(order_id)
        except Exception:
            raise ValueError(f"Order with ID {order_id} not found.")

        temp_dataset = RapidataDataset("temp", self.openapi_service)
        return RapidataOrder(
            dataset=temp_dataset, 
            order_id=order_id, 
            name=order.order_name,
            openapi_service=self.openapi_service)

    def find_orders(self, name: str = "", amount: int = 1) -> list[RapidataOrder]:
        """Find your recent orders given criteria. If nothing is provided, it will return the most recent order.

        Args:
            name (str, optional): The name of the order - matching order will contain the name. Defaults to "" for any order.
            amount (int, optional): The amount of orders to return. Defaults to 1.

        Returns:
            list[RapidataOrder]: A list of RapidataOrder instances.
        """
        try:
            order_page_result = self.openapi_service.order_api.order_query_get(QueryOrdersModel(
                page=PageInfo(index=1, size=amount),
                filter=RootFilter(filters=[Filter(field="OrderName", operator="Contains", value=name)]),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="OrderDate")]
                ))

        except BadRequestException as e:
            raise ValueError(f"Error occured during request. \nError: {e.body} \nTraceid: {e.headers.get('X-Trace-Id') if isinstance(e.headers, HTTPHeaderDict) else 'Unknown'}")

        except Exception as e:
            raise ValueError(f"Unknown error occured: {e}")

        orders = [self.get_order(order.id) for order in order_page_result.items]
        return orders
    
    def get_validation_set(self, validation_set_id: str) -> RapidataValidationSet:
        """Get a validation set by ID.

        Args:
            validation_set_id (str): The ID of the validation set.

        Returns:
            RapidataValidationSet: The ValidationSet instance.
        """
        try:
            validation_set = self.openapi_service.validation_api.validation_get_by_id_get(id=validation_set_id)
        except Exception:
            raise ValueError(f"ValidationSet with ID {validation_set_id} not found.")
        
        return RapidataValidationSet(validation_set_id, self.openapi_service, validation_set.name)
    
    def find_validation_sets(self, name: str = "", amount: int = 1) -> list[RapidataValidationSet]:
        try:
            validation_page_result = self.openapi_service.validation_api.validation_query_validation_sets_get(QueryValidationSetModel(
                pageInfo=PageInfo(index=1, size=amount),
                filter=RootFilter(filters=[Filter(field="Name", operator="Contains", value=name)]),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="CreatedAt")]
                ))

        except BadRequestException as e:
            raise ValueError(f"Error occured during request. \nError: {e.body} \nTraceid: {e.headers.get('X-Trace-Id') if isinstance(e.headers, HTTPHeaderDict) else 'Unknown'}")

        except Exception as e:
            raise ValueError(f"Unknown error occured: {e}")

        orders = [self.get_validation_set(validation_set.id) for validation_set in validation_page_result.items] # type: ignore # will be fixed with the next backend deployment
        return orders

    def create_classify_order(self, name: str) -> ClassificationQuestionBuilder:
        """Create a new classification order where people are asked to classify an image.

        Args:
            name (str): The name of the order.

        Returns:
            ClassificationQuestionBuilder: A ClassificationQuestionBuilder instance.
        """
        return ClassificationQuestionBuilder(name=name, openapi_service=self.openapi_service)

    def create_compare_order(self, name: str) -> CompareCriteriaBuilder:
        """Create a new comparison order where people are asked to compare two images.

        Args:
            name (str): The name of the order.

        Returns:
            CompareQuestionBuilder: A CompareQuestionBuilder instance.
        """
        return CompareCriteriaBuilder(name=name, openapi_service=self.openapi_service)
