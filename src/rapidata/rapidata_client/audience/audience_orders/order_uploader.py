from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.service.openapi_service import OpenAPIService


if TYPE_CHECKING:
    from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
    from rapidata.rapidata_client.audience.audience_orders.audience_order import (
        AudienceOrder,
    )


class OrderUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def upload_order(
        self,
        order: AudienceOrder,
        validation_set_id: str,
    ) -> RapidataOrder:
        from rapidata.rapidata_client.order._rapidata_order_builder import (
            RapidataOrderBuilder,
        )
        from rapidata.rapidata_client.referee._naive_referee import NaiveReferee

        order_builder = RapidataOrderBuilder(
            name=order.name,
            openapi_service=self.openapi_service,
        )
        order_builder._set_workflow(order.workflow)
        order_builder._set_datapoints(order.datapoints)
        order_builder._set_referee(
            NaiveReferee(responses=order.responses_per_datapoint)
        )
        order_builder._set_validation_set_id(
            validation_set_id
        )  # Will automatically add the filters to the order with the dimension of the validation set
        order_builder._set_settings(order.settings or [])
        return order_builder._create()
