from enum import Enum


class DemographicIdentifier(Enum):
    """DemographicIdentifier Enum

    The demographic attribute a :class:`DemographicFilter` targets. Using the enum avoids
    hard-coding the backend identifier strings, which are not always guessable (the
    occupation identifier is versioned, for example).

    Attributes:
        AGE (DemographicIdentifier): The labeler's age bucket (e.g. ``"18-29"``).
        GENDER (DemographicIdentifier): The labeler's gender.
        OCCUPATION (DemographicIdentifier): The labeler's occupation.
    """

    AGE = "age"
    GENDER = "gender"
    OCCUPATION = "occupation-2026-07-01"

    def _to_backend_model(self) -> str:
        return self.value
