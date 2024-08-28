from rapidata.api_client.models.naive_referee_model import NaiveRefereeModel
from rapidata.rapidata_client.referee.base_referee import Referee


class NaiveReferee(Referee):
    """
    The referee defines when a task is considered complete.
    The SimpleReferee is the simplest referee, requiring a fixed number of guesses.
    """

    def __init__(self, required_guesses: int = 10):
        super().__init__()
        self.required_guesses = required_guesses

    def to_dict(self):
        return {
            "_t": "NaiveRefereeConfig",
            "guessesRequired": self.required_guesses,
        }

    def to_model(self):
        return NaiveRefereeModel(_t="NaiveReferee", totalVotes=self.required_guesses)
