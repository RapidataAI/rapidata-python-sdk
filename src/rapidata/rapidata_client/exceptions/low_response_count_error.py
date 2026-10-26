from __future__ import annotations

MIN_RESPONSES_PER_DATAPOINT = 10
LOW_RESPONSE_COUNT_MESSAGE = (
    "At least 10 responses per datapoint are required. To collect fewer, email "
    "info@rapidata.ai with your use case and we will enable it for your organization."
)


class LowResponseCountError(ValueError):
    """Raised before any upload when a job asks for fewer than 10 responses per
    datapoint and the organization has not been enabled for it.

    Attributes:
        requested (int): The responses per datapoint that were asked for.
        minimum (int): The minimum without the capability (10).
    """

    def __init__(self, requested: int):
        self.requested = requested
        self.minimum = MIN_RESPONSES_PER_DATAPOINT
        super().__init__(
            f"Requested {requested} responses per datapoint (minimum {self.minimum}). "
            f"{LOW_RESPONSE_COUNT_MESSAGE}"
        )
