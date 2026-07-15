from rapidata.api_client.models.locate_box_truth_box import (
    LocateBoxTruthBox,
)
from rapidata.api_client.models.example_box_shape import ExampleBoxShape
from pydantic import BaseModel, field_validator, model_validator


class Box(BaseModel):
    """
    Used in the Locate and Draw Validation sets. All coordinates are in ratio of the image size (0.0 to 1.0).

    Args:
        x_min (float): The minimum x value of the box in ratio of the image size.
        y_min (float): The minimum y value of the box in ratio of the image size.
        x_max (float): The maximum x value of the box in ratio of the image size.
        y_max (float): The maximum y value of the box in ratio of the image size.
    """

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @field_validator("x_min", "y_min", "x_max", "y_max")
    @classmethod
    def coordinates_between_zero_and_one(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Box coordinates must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def check_min_less_than_max(self) -> "Box":
        if self.x_min >= self.x_max:
            raise ValueError("x_min must be less than x_max")
        if self.y_min >= self.y_max:
            raise ValueError("y_min must be less than y_max")
        return self

    def to_model(self) -> LocateBoxTruthBox:
        return LocateBoxTruthBox(
            xMin=self.x_min * 100,
            yMin=self.y_min * 100,
            xMax=self.x_max * 100,
            yMax=self.y_max * 100,
        )

    def to_example_model(self) -> ExampleBoxShape:
        return ExampleBoxShape(
            xMin=self.x_min * 100,
            yMin=self.y_min * 100,
            xMax=self.x_max * 100,
            yMax=self.y_max * 100,
        )


def calculate_boxes_coverage(boxes: list[Box]) -> float:
    """Calculate the ratio of image area covered by a list of boxes.

    Args:
        boxes: List of Box objects with coordinates in range [0, 1].

    Returns:
        float: Coverage ratio between 0.0 and 1.0.
    """
    if not boxes:
        return 0.0

    # Sweep line over x: at each x-interval, sum the merged y-coverage of the
    # currently active boxes, weighted by the interval width.
    events: list[tuple[float, str, int]] = []
    for i, box in enumerate(boxes):
        events.append((box.x_min, "start", i))
        events.append((box.x_max, "end", i))

    events.sort(key=lambda e: (e[0], e[1] == "end"))

    total_area = 0.0
    active_boxes: set[int] = set()
    prev_x = 0.0

    for x, event_type, box_id in events:
        if active_boxes and x > prev_x:
            y_intervals = sorted((boxes[i].y_min, boxes[i].y_max) for i in active_boxes)
            merged: list[tuple[float, float]] = []
            for start, end in y_intervals:
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            y_coverage = sum(end - start for start, end in merged)
            total_area += (x - prev_x) * y_coverage

        if event_type == "start":
            active_boxes.add(box_id)
        else:
            active_boxes.discard(box_id)

        prev_x = x

    return total_area
