from rapidata.api_client.models.box_shape import BoxShape
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

    def to_model(self) -> BoxShape:
        return BoxShape(
            xMin=self.x_min * 100,
            yMin=self.y_min * 100,
            xMax=self.x_max * 100,
            yMax=self.y_max * 100,
        )


def calculate_boxes_coverage(boxes: list[Box]) -> float:
    """Compute the union area of ``boxes`` as a 0–1 ratio of the asset.

    Used as the ``random_correct_probability`` baseline when boxes are the
    ground truth (Locate / Line audience examples, Locate / Line rapids).

    Coordinates are in [0, 1] image-ratio space (matching ``Box``); overlaps
    are not double-counted.

    Args:
        boxes: Boxes to union. Empty list returns 0.

    Returns:
        Coverage ratio in [0.0, 1.0].
    """
    if not boxes:
        return 0.0

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
            y_intervals = [(boxes[i].y_min, boxes[i].y_max) for i in active_boxes]
            y_intervals.sort()

            merged_intervals: list[tuple[float, float]] = []
            for start, end in y_intervals:
                if merged_intervals and start <= merged_intervals[-1][1]:
                    merged_intervals[-1] = (
                        merged_intervals[-1][0],
                        max(merged_intervals[-1][1], end),
                    )
                else:
                    merged_intervals.append((start, end))

            y_coverage = sum(end - start for start, end in merged_intervals)
            total_area += (x - prev_x) * y_coverage

        if event_type == "start":
            active_boxes.add(box_id)
        else:
            active_boxes.discard(box_id)

        prev_x = x

    return total_area
