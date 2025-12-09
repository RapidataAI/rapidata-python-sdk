from pydantic import BaseModel, ConfigDict
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.referee import Referee
from rapidata.rapidata_client.settings import RapidataSetting
from typing import Sequence


class JobDefinition(BaseModel):
    name: str
    workflow: Workflow
    datasetId: str
    referee: Referee
    settings: Sequence[RapidataSetting] | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True, populate_by_name=True, extra="allow"
    )

    def preview(self) -> None:
        """Will open the browser where you can preview the job definition before giving it to an audience."""
        raise NotImplementedError("Not implemented")
