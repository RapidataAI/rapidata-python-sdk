import dataclasses
from collections import deque
from PIL import Image

from consts import MAX_ANNOTATION_PER_RAPID, DEFAULT_FILE


@dataclasses.dataclass
class BBox:
    x: int
    y: int
    width: int
    height: int
    annotation_scale: float

    def get_scaled(self):
        return BBox(
            x=int(self.x * self.annotation_scale),
            y=int(self.y * self.annotation_scale),
            width=int(self.width * self.annotation_scale),
            height=int(self.height * self.annotation_scale),
            annotation_scale=1.0
        )


class ValidationRapid:
    RAPID_ID = 0

    def __init__(self, name: str, image: Image.Image):
        self.annotation = dict()
        self.name = name
        self.image = image
        self.rapid_id = self.RAPID_ID
        ValidationRapid.RAPID_ID += 1

    @staticmethod
    def clone(rapid: 'ValidationRapid') -> 'ValidationRapid':
        r = ValidationRapid(rapid.name, rapid.image)
        r.annotation = rapid.annotation
        return r

    def set_annotation(self, annotation: dict):
        self.annotation = annotation

    def is_done(self):
        return len(self.annotation.get('objects', [])) == 1

class ValidationRapidCollection:
    def __init__(self, add_default: bool = True):
        self.rapids = []

        if add_default:
            self.add_default()
        self.current_rapid = None
        self.set_last()

    def add_default(self):
        image = Image.open(DEFAULT_FILE)
        r = ValidationRapid(DEFAULT_FILE, image)
        self.rapids.append(r)

    def add_rapid(self, rapid: ValidationRapid):
        self.rapids.append(rapid)
        self.current_rapid = rapid

    def remove_rapid(self, rapid: ValidationRapid):
        self.rapids.remove(rapid)
        if rapid == self.current_rapid:
            self.set_last()

    def set_last(self):
        if self.rapids:
            self.current_rapid = self.rapids[-1]
        else:
            self.current_rapid = None

    def get_by_id(self, rapid_id):
        filtered = [r for r in self.rapids if r.rapid_id == rapid_id]
        if filtered:
            return filtered[0]
        return None
    def set_current(self, rapid_id):
        r = self.get_by_id(rapid_id)
        if r is not None:
            self.current_rapid = r