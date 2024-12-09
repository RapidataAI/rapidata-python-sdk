import base64
from io import BytesIO

from PIL import Image

from consts import CANVAS_WIDTH
from models import ValidationRapid, BBox


def resize_image(image: Image, target_width=CANVAS_WIDTH) -> Image:
    scale = calc_image_scale(image)
    height = int(scale * image.height)

    return image.resize((target_width, height))


def calc_image_scale(image: Image):
    return CANVAS_WIDTH / image.width

def calc_relative_bbox_area(bbox: BBox, image: Image):
    image_area = image.height * image.width
    bbox_area = bbox.width * bbox.height
    return bbox_area / image_area

def image_to_base64(img):
    with BytesIO() as buffer:
        img.save(buffer, "png")
        raw_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{raw_base64}"
