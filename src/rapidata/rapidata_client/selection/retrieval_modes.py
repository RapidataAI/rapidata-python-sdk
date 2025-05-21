from enum import Enum

class RetrievalMode(Enum):
    """
    Enum for defining retrieval modes for datapoints.
    """
    Shuffled = "Shuffled"
    """
    Will shuffle the datapoints randomly for each user. The user will then see the datapoints in that order. This will take into account the "max_iterations" parameter.
    """
    Sequential = "Sequential"
    """
    Will show the datapoints in the order they are in the dataset. This will take into account the "max_iterations" parameter.
    """
    Random = "Random"
    """
    Will just randomly feed the datapoints to the annotators. This will NOT take into account the "max_iterations" parameter.
    """
