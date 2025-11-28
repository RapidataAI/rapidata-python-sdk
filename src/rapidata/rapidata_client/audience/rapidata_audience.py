from __future__ import annotations

from typing import TYPE_CHECKING
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config import tracer
from rapidata.rapidata_client.config import rapidata_config

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.rapidata_client.validation.rapids.rapids import Rapid
    from rapidata.rapidata_client.audience.audience_orders.audience_order import (
        AudienceOrder,
    )
    from rapidata.rapidata_client.validation.rapidata_validation_set import (
        RapidataValidationSet,
    )
    from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class RapidataAudience:
    def __init__(
        self,
        id: str,
        name: str,
        filters: list[RapidataFilter],
        validation_set: RapidataValidationSet,
        openapi_service: OpenAPIService,
    ):
        from rapidata.rapidata_client.audience.audience_orders.order_uploader import (
            OrderUploader,
        )

        self.id = id
        self.name = name
        self.filters = filters
        self._openapi_service = openapi_service
        self._validation_set = validation_set
        self._order_uploader = OrderUploader(openapi_service)

    def update_filters(self, filters: list[RapidataFilter]) -> RapidataAudience:
        # will update the filters for the audience as soon as endpoint is ready
        with tracer.start_as_current_span("RapidataAudience.update_filters"):
            from rapidata.api_client.models.update_audience_request import (
                UpdateAudienceRequest,
            )

            logger.debug(f"Updating filters for audience: {self.id} to {filters}")
            self._openapi_service.audience_api.audience_audience_id_patch(
                audience_id=self.id,
                update_audience_request=UpdateAudienceRequest(
                    filters=[filter._to_model() for filter in filters],
                ),
            )
            self.filters = filters
            return self

    def update_name(self, name: str) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudience.update_name"):
            from rapidata.api_client.models.update_audience_request import (
                UpdateAudienceRequest,
            )

            logger.debug(f"Updating name for audience: {self.id} to {name}")
            self._openapi_service.audience_api.audience_audience_id_patch(
                audience_id=self.id,
                update_audience_request=UpdateAudienceRequest(name=name),
            )
            self.name = name
            return self

    def add_validation_rapid(self, rapid: Rapid) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudience.add_validation_rapid"):
            logger.debug(f"Adding validation rapid: {rapid} to audience: {self.id}")
            self._validation_set.add_rapid(rapid)
            return self

    def start_recruiting(self) -> RapidataAudience:
        # will start the recruiting for the audience as soon as endpoint is ready
        with tracer.start_as_current_span("RapidataAudience.start_recruiting"):
            from rapidata.rapidata_client.order._rapidata_order_builder import (
                RapidataOrderBuilder,
            )
            from rapidata.rapidata_client.datapoints._datapoint import Datapoint
            from rapidata.rapidata_client.workflow import ClassifyWorkflow
            from rapidata.rapidata_client.filter import UserScoreFilter
            from rapidata.rapidata_client.selection import (
                ValidationSelection,
                CappedSelection,
                LabelingSelection,
            )

            if self._validation_set._get_total_and_labeled_rapids_count()[1] < 3:
                raise ValueError(
                    "Add at least 3 validation rapids in order to start recruiting"
                )

            logger.debug(f"Starting recruiting for audience: {self.id}")
            # will start the recruiting for the audience as soon as endpoint is ready
            self._validation_set.update_should_alert(False)
            self._validation_set.update_can_be_flagged(False)
            order_builder = RapidataOrderBuilder(
                name=self.name + " Audience Recruiting Order",
                openapi_service=self._openapi_service,
            )
            order_builder._datapoints(
                [Datapoint(asset="won't be shown", data_type="text")]
            )
            order_builder._workflow(
                ClassifyWorkflow(
                    instruction="Check the preview to see the validation tasks",
                    answer_options=["Yes", "No"],
                )
            )
            order_builder._filters(
                self.filters
                + [UserScoreFilter(lower_bound=0.3, upper_bound=0.5, dimension=self.id)]
            )
            order_builder._selections(
                [
                    CappedSelection(
                        selections=[
                            ValidationSelection(
                                validation_set_id=self._validation_set.id, amount=3
                            ),
                            LabelingSelection(amount=1),
                        ],
                        max_rapids=3,
                    )
                ]
            )
            order_builder._create().run()
            return self

    def assign_order(self, order: AudienceOrder) -> RapidataOrder:
        with tracer.start_as_current_span("RapidataAudience.assign_order"):
            logger.debug(f"Assigning order to audience: {self.id}")
            if not rapidata_config.order.autoValidationSetCreation:
                raise ValueError(
                    "Auto validation set creation must be enabled in order to assign an order to an audience"
                )
            if (
                rapidata_config.order.minOrderDatapointsForValidation
                > len(order.datapoints)
            ) and (self._validation_set._get_total_and_labeled_rapids_count()[1] < 3):
                raise ValueError(
                    f"Not enough annotated validation rapids. Required: 3, Annotated: {self._validation_set._get_total_and_labeled_rapids_count()[1]}\nUse the `add_validation_rapid` method to add more validation rapids."
                )
            return self._order_uploader.upload_order(order, self._validation_set.id)

    def __str__(self) -> str:
        return (
            f"RapidataAudience(id={self.id}, name={self.name}, filters={self.filters})"
        )

    def __repr__(self) -> str:
        return self.__str__()
