from enum import Enum
from rapidata.api_client.models.retrieval_mode import RetrievalMode


class RapidataRetrievalMode(Enum):
    """
    Enum for defining retrieval modes for datapoints.
    """

    Shuffled = RetrievalMode.SHUFFLED
    """
    Will shuffle the datapoints randomly for each user. The user will then see the datapoints in that order. This will take into account the "max_iterations" parameter.
    """
    Sequential = RetrievalMode.SEQUENTIAL
    """
    Will show the datapoints in the order they are in the dataset. This will take into account the "max_iterations" parameter.
    """
    Random = RetrievalMode.RANDOM
    """
    Will just randomly feed the datapoints to the annotators. This will NOT take into account the "max_iterations" parameter.
    """
