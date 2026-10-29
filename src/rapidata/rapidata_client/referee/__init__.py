from ._base_referee import Referee
from ._naive_referee import NaiveReferee  # as MaxVoteReferee
from ._early_stopping_referee import EarlyStoppingReferee
from ._quorum_referee import QuorumReferee
from ._adaptive_stopping_referee import AdaptiveStoppingReferee
from .stopping import AdaptiveStopping, QuorumStopping
