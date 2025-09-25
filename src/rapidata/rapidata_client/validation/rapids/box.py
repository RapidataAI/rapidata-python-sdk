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
            _t="BoxShape",
            xMin=self.x_min * 100,
            yMin=self.y_min * 100,
            xMax=self.x_max * 100,
            yMax=self.y_max * 100,
        )
