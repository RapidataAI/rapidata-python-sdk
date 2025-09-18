from typing import Literal, Sequence

from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata

from pydantic import BaseModel


class Datapoint(BaseModel):
    assets: str | list[str]
    data_type: Literal["text", "media"]
    metadata: Sequence[Metadata]
