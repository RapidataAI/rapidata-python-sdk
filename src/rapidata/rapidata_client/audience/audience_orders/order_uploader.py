from rapidata.rapidata_client.audience.audience_orders.audience_order import (
    AudienceOrder,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.order._rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class OrderUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def upload_order(
        self, order: AudienceOrder, validation_set_id: str
    ) -> RapidataOrder:
        order_builder = RapidataOrderBuilder(
            name=order.name,
            openapi_service=self.openapi_service,
        )
        order_builder._workflow(order.workflow)
        order_builder._datapoints(order.datapoints)
        order_builder._referee(NaiveReferee(responses=order.responses_per_datapoint))
        order_builder._validation_set_id(validation_set_id)
        order_builder._settings(order.settings or [])
        return order_builder._create()
