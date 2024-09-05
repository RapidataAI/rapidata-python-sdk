from rapidata.api_client.models.naive_referee_model import NaiveRefereeModel
from rapidata.rapidata_client.referee.base_referee import Referee


class NaiveReferee(Referee):
    """A simple referee that completes a task after a fixed number of guesses.

    This referee implements a straightforward approach to task completion,
    where the task is considered finished after a predetermined number of
    guesses have been made, regardless of the content or quality of those guesses.

    Attributes:
        required_guesses (int): The number of guesses required to complete the task.
    """

    def __init__(self, required_guesses: int = 10):
        """Initialize the NaiveReferee.

        Args:
            required_guesses (int, optional): The number of guesses required
                to complete the task. Defaults to 10.
        """
        super().__init__()
        self.required_guesses = required_guesses

    def to_dict(self):
        return {
            "_t": "NaiveRefereeConfig",
            "guessesRequired": self.required_guesses,
        }

    def to_model(self):
        return NaiveRefereeModel(_t="NaiveReferee", totalVotes=self.required_guesses)
