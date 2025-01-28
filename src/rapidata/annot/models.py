import dataclasses
import enum
from collections import deque
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
        return len(self.annotation.get('objects', [])) == 1

class ValidationRapidCollection:
    def __init__(self, starter_rapid: Optional[ValidationRapid] = None):
        self.rapids: List[ValidationRapid] = list()

        self.previous_rapids = []
        self.current_rapid = None

        if starter_rapid is not None:
            self.rapids.append(starter_rapid)
        self.set_first_as_current()



    def add_rapids(self, rapids: Union[ValidationRapid, List[ValidationRapid]]):
        if not isinstance(rapids, list):
            rapids = [rapids]

        for r in rapids:
            self.rapids.append(r)
        self.set_first_as_current()

    def all_done(self):
        return all(r.is_done() for r in self.rapids)

    def remove_rapid(self, rapid: ValidationRapid):
        self.rapids.remove(rapid)
        if rapid in self.previous_rapids:
            self.previous_rapids.remove(rapid)
        if rapid == self.current_rapid:
            self.set_first_as_current()

    def set_first_as_current(self):
        if self.rapids:
            self.set_current(self.rapids[0].local_rapid_id)
        else:
            self.current_rapid = None

    def get_by_id(self, rapid_id):
        filtered = [r for r in self.rapids if r.local_rapid_id == rapid_id]
        if filtered:
            return filtered[0]
        return None

    def set_next_unannotated_as_current(self):
        for r in self.rapids:
            if not r.is_done():
                self.set_current(r.local_rapid_id)
                return
        self.set_current(None)


    def set_current(self, rapid_id):
        r = self.get_by_id(rapid_id)
        if r is not None: #noqa xdd
            if self.current_rapid is not None:
                if self.current_rapid in self.previous_rapids:
                    self.previous_rapids.remove(self.current_rapid)
                self.previous_rapids.append(self.current_rapid)
            self.current_rapid = r
