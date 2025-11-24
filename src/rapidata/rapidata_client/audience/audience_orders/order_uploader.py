from rapidata.rapidata_client.audience.audience_orders.audience_order import (
    AudienceOrder,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.order._rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.selection import (
    CappedSelection,
    ConditionalValidationSelection,
    LabelingSelection,
)


class OrderUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def upload_order(
        self, order: AudienceOrder, audience_id: str, validation_set_id: str
    ) -> RapidataOrder:
        order_builder = RapidataOrderBuilder(
            name=order.name,
            openapi_service=self.openapi_service,
        )
        order_builder._workflow(order.workflow)
        order_builder._datapoints(order.datapoints)
        order_builder._referee(NaiveReferee(responses=order.responses_per_datapoint))
        selections = [
            CappedSelection(
                selections=[
                    ConditionalValidationSelection(
                        validation_set_id=validation_set_id,
                        dimensions=[audience_id],
                        thresholds=[0, 0.5, 0.7],
                        chances=[1, 1, 0.2],
                        rapid_counts=[10, 1, 1],
                    ),
                    LabelingSelection(amount=1),
                ],
                max_rapids=3,
            )
        ]
        order_builder._selections(selections)
        order_builder._settings(order.settings or [])
        return order_builder._create()
