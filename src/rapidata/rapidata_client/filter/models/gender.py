from enum import Enum
from rapidata.api_client.models.gender import Gender as BackendGenderModel

class Gender(Enum):
    """Gender Enum
    
    Represents the gender of a user. Used to filter who to target based on genders.
    
    Attributes:
        MALE (Gender): Represents the Male gender.
        FEMALE (Gender): Represents the Female gender.
        OTHER (Gender): Represents any other gender.
    """
    MALE = BackendGenderModel.MALE
    FEMALE = BackendGenderModel.FEMALE
    OTHER = BackendGenderModel.OTHER

    def _to_backend_model(self) -> BackendGenderModel:
        return BackendGenderModel(self.value)
