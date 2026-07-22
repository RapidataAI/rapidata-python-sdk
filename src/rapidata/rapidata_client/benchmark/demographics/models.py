from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)

from rapidata.api_client.models.confidence_interval import ConfidenceInterval
from rapidata.api_client.models.standing_status import StandingStatus

# The field names of the demographic dimensions. Age, gender and occupation are
# *estimated* (inferred from behaviour), not self-declared by the annotator;
# country and language are observed. Kept faithful to what the API returns.
DemographicDimension = str


class DemographicBucket(BaseModel):
    """One value of a demographic dimension and its share of the votes.

    `value` is the bucket label (e.g. "18-24", "US", "Male"). The literal
    `"unknown"` bucket carries the votes whose attribute could not be
    determined; it is always present and never dropped.
    """

    model_config = ConfigDict(populate_by_name=True)

    value: StrictStr
    votes: StrictInt
    # Fraction of the dimension's votes in [0, 1]; the shares of a dimension
    # (including "unknown") sum to 1.
    share: Union[StrictFloat, StrictInt]


class BenchmarkDemographics(BaseModel):
    """Voter composition of a benchmark, broken down by demographic dimension.

    `dimensions` maps a dimension name (`ageBucket`, `gender`, `occupation`,
    `country`, `language`) to its buckets. Each dimension includes an
    `"unknown"` bucket and its shares sum to 1. Age, gender and occupation are
    estimated (inferred), not self-declared.
    """

    model_config = ConfigDict(populate_by_name=True)

    total_votes: StrictInt = Field(alias="totalVotes")
    dimensions: Dict[DemographicDimension, List[DemographicBucket]]


class BenchmarkStandingItem(BaseModel):
    """A single model's standing within a benchmark.

    `score`/`wins`/`total_matches` are raw vote counts. Mirrors the standings
    item shape returned by the benchmark standings endpoints.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: StrictStr
    name: StrictStr
    family: Optional[StrictStr] = None
    proprietary_name: Optional[StrictStr] = Field(default=None, alias="proprietaryName")
    logo: Optional[StrictStr] = None
    status: StandingStatus
    score: Optional[Union[StrictFloat, StrictInt]] = None
    wins: Union[StrictFloat, StrictInt]
    total_matches: Union[StrictFloat, StrictInt] = Field(alias="totalMatches")
    is_disabled: StrictBool = Field(alias="isDisabled")
    confidence_interval: Optional[ConfidenceInterval] = Field(
        default=None, alias="confidenceInterval"
    )


class BenchmarkStandingsSegment(BaseModel):
    """Standings restricted to voters in one bucket of a demographic dimension.

    `value` is the bucket label (including `"unknown"`), `votes` is the raw
    number of votes contributed by that segment, and `items` are that segment's
    standings.
    """

    model_config = ConfigDict(populate_by_name=True)

    value: StrictStr
    votes: StrictInt
    items: List[BenchmarkStandingItem]


class BenchmarkStandingsBreakdown(BaseModel):
    """Per-segment standings for one demographic dimension of a benchmark.

    `global_standings` is the overall standings across all voters; `segments`
    holds one entry per bucket of `dimension` (including `"unknown"`). Segments
    are raw vote counts. Age, gender and occupation dimensions are estimated
    (inferred), not self-declared.
    """

    model_config = ConfigDict(populate_by_name=True)

    dimension: StrictStr
    # `global` is a Python keyword, so the attribute is exposed as
    # `global_standings` while still (de)serializing to the API's `global` key.
    global_standings: List[BenchmarkStandingItem] = Field(alias="global")
    segments: List[BenchmarkStandingsSegment]
