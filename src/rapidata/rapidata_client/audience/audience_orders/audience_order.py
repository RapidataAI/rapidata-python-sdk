from pydantic import BaseModel, Field
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.settings import RapidataSetting
from typing import Sequence


class AudienceOrder(BaseModel):
    name: str
    workflow: Workflow
    datapoints: list[Datapoint]
    responses_per_datapoint: int = Field(default=10)
    settings: Sequence[RapidataSetting] | None = None

    class Config:
        arbitrary_types_allowed = True
