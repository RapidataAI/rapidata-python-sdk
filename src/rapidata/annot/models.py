import dataclasses
import enum
from typing import List, Union

from PIL import Image
from typing import Optional

from consts import DEFAULT_FILE


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


class RapidTypes(enum.Enum):
    LOCATE = 'Locate'
    LINE = 'Line'


class ValidationRapid:

    def __init__(self, name: str, image: Image.Image, rapid_id: int):
        self.annotation = dict()
        self.name = name
        self.image: Image.Image = image
        self.local_rapid_id = rapid_id
        self.prompt = ''


    def set_annotation(self, annotation: dict):
        self.annotation = annotation

    def is_done(self):
        return len(self.annotation.get('objects', [])) == 1 and len(self.prompt) >= 1

class ValidationRapidCollection:
    def __init__(self, starter_rapid: Optional[ValidationRapid] = None):
        self.rapids: List[ValidationRapid] = list()

        if starter_rapid is not None:
            self.rapids.append(starter_rapid)
        self.set_last()


    def add_rapids(self, rapids: Union[ValidationRapid, List[ValidationRapid]]):
        if not isinstance(rapids, list):
            rapids = [rapids]

        for r in rapids:
            self.rapids.append(r)
        self.set_last()

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
        filtered = [r for r in self.rapids if r.local_rapid_id == rapid_id]
        if filtered:
            return filtered[0]
        return None
    def set_current(self, rapid_id):
        r = self.get_by_id(rapid_id)
        if r is not None:
            self.current_rapid = r
