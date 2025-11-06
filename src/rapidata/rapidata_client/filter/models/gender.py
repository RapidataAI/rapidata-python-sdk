from enum import Enum
from rapidata.api_client.models.gender_user_filter_model_gender import (
    GenderUserFilterModelGender,
)


class Gender(Enum):
    """Gender Enum

    Represents the gender of a user. Used to filter who to target based on genders.

    Attributes:
        MALE (Gender): Represents the Male gender.
        FEMALE (Gender): Represents the Female gender.
        OTHER (Gender): Represents any other gender.
    """

    MALE = GenderUserFilterModelGender.MALE
    FEMALE = GenderUserFilterModelGender.FEMALE
    OTHER = GenderUserFilterModelGender.OTHER

    def _to_backend_model(self) -> GenderUserFilterModelGender:
        return GenderUserFilterModelGender(self.value)
