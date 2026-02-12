from __future__ import annotations

from typing import TYPE_CHECKING, Any
from time import sleep
from rapidata.rapidata_client.config import logger, tracer
from rapidata.service.openapi_service import OpenAPIService


if TYPE_CHECKING:
    from rapidata.api_client.models.flow_item_state import FlowItemState
    from rapidata.api_client.models.get_flow_item_by_id_endpoint_output import (
        GetFlowItemByIdEndpointOutput,
    )
    import pandas as pd


class RapidataFlowItem:
    def __init__(self, id: str, flow_id: str, openapi_service: OpenAPIService):
        self.id = id
        self.flow_id = flow_id
        self._openapi_service = openapi_service
        self._response_count: float | int | None = None

    @property
    def response_count(self) -> float | int:
        if self._response_count is None:
            self.get_win_loss_matrix()
        assert self._response_count is not None
        return self._response_count

    def get_status(self) -> FlowItemState:
        """Get the current state of this flow item.

        Returns:
            FlowItemState: The current state (Pending, Running, Completed, Failed, Stopped).
        """
        with tracer.start_as_current_span("RapidataFlowItem.get_status"):
            logger.debug("Getting status for flow item '%s'", self.id)
            details = self._get_details()
            return details.state

    def get_results(self) -> dict[str, int]:
        """Get the results of this flow item from the API.

        Returns:
            dict[str, int]: A mapping of asset identifier to elo score.
                The key is the source URL if available, otherwise the original filename.
        """
        with tracer.start_as_current_span("RapidataFlowItem.get_results"):
            from rapidata.api_client.models.flow_item_state import FlowItemState

            logger.debug("Getting results for flow item '%s'", self.id)
            self._wait_for_state(
                target_states=[
                    FlowItemState.COMPLETED,
                    FlowItemState.FAILED,
                    FlowItemState.STOPPED,
                    FlowItemState.INCOMPLETE,
                ],
                check_interval=1,
                status_message="Flow item '%s' is in state %s, waiting for completion...",
            )

            results = self._openapi_service.ranking_flow_item_api.flow_ranking_item_flow_item_id_results_get(
                flow_item_id=self.id,
            )

            return {
                self._extract_asset_key(dp): dp.get("elo", 0)
                for dp in (datapoint.to_dict() for datapoint in results.datapoints)
            }

    def get_win_loss_matrix(self) -> pd.DataFrame:
        """Get the win/loss matrix of this flow item from the API.

        The win/loss matrix shows pairwise comparison counts where ``data[i][j]`` is
        the number of times row ``i`` was preferred over column ``j``.

        Returns:
            pd.DataFrame: A DataFrame where rows and columns are asset identifiers,
                and values are win/loss counts.
        """
        with tracer.start_as_current_span("RapidataFlowItem.get_win_loss_matrix"):
            import pandas as pd
            from rapidata.api_client.models.flow_item_state import FlowItemState

            logger.debug("Getting win/loss matrix for flow item '%s'", self.id)
            self._wait_for_state(
                target_states=[
                    FlowItemState.COMPLETED,
                    FlowItemState.FAILED,
                    FlowItemState.STOPPED,
                    FlowItemState.INCOMPLETE,
                ],
                check_interval=1,
                status_message="Flow item '%s' is in state %s, waiting for completion...",
            )

            result = self._openapi_service.ranking_flow_item_api.flow_ranking_item_flow_item_id_vote_matrix_get(
                flow_item_id=self.id,
            )
            self._response_count = sum(sum(row) for row in result.data)

            return pd.DataFrame(
                data=result.data,
                index=pd.Index(result.index),
                columns=pd.Index(result.columns),
            )

    @staticmethod
    def _extract_asset_key(datapoint: dict[str, Any]) -> str:
        """Extract a human-readable key from a datapoint dict.

        Uses the source URL if available, otherwise the original filename,
        falling back to the asset identifier or datapoint id.
        """
        asset = datapoint.get("asset", {})
        metadata = asset.get("metadata", {})

        source_url = metadata.get("sourceUrl", {}).get("url")
        original_filename = metadata.get("originalFilename", {}).get("originalFilename")

        return (
            source_url
            or original_filename
            or asset.get("identifier", datapoint.get("id", "unknown"))
        )

    def _wait_for_state(
        self,
        target_states: list[FlowItemState],
        check_interval: float = 1,
        status_message: str | None = None,
    ) -> str:
        """
        Wait until the flow item reaches one of the target states.

        Args:
            target_states: List of states to wait for
            check_interval: How often to check the state in seconds
            status_message: Optional message to display while waiting

        Returns:
            The final state reached
        """
        while (current_state := self.get_status()) not in target_states:
            if status_message:
                logger.debug(status_message, self, current_state)
            sleep(check_interval)

        return current_state

    def _get_details(self) -> GetFlowItemByIdEndpointOutput:
        """Fetch the full details of this flow item from the API."""
        return self._openapi_service.ranking_flow_item_api.flow_ranking_item_flow_item_id_get(
            flow_item_id=self.id,
        )

    def __str__(self) -> str:
        return f"FlowItem(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
