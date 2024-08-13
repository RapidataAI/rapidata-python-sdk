from rapidata.rapidata_client.workflow.referee.base_referee import Referee


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
