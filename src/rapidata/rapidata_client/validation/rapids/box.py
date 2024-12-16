from rapidata.api_client.models.box_shape import BoxShape

class Box:
    """
    Used in the Locate and Draw Validation sets. All coordinates are in pixels.
    
    Args:
        x_min (float): The minimum x value of the box.
        y_min (float): The minimum y value of the box.
        x_max (float): The maximum x value of the box.
        y_max (float): The maximum y value of the box.
    """
    def __init__(self, x_min: float, y_min: float, x_max: float, y_max: float):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
