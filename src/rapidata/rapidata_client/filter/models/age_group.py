from rapidata.api_client.models.age_group import AgeGroup as BackendAgeGroupModel
from enum import Enum

class AgeGroup(Enum):
    """AgeGroup Enum
    
    Represents the age group of a user. Used to filter who to target based on age groups.
    
    Attributes:
        UNDER_18 (AgeGroup): Represents the age group of users under 18.
        BETWEEN_18_30 (AgeGroup): Represents the age group of users between 18 and 30.
        BETWEEN_31_50 (AgeGroup): Represents the age group of users between 31 and 50.
        BETWEEN_51_65 (AgeGroup): Represents the age group of users between 51 and 65.
        OVER_65 (AgeGroup): Represents the age group of users over 65."""
    
    UNDER_18 = BackendAgeGroupModel.ENUM_0_MINUS_18
    BETWEEN_18_30 = BackendAgeGroupModel.ENUM_19_MINUS_30
    BETWEEN_31_50 = BackendAgeGroupModel.ENUM_31_MINUS_50
    BETWEEN_51_65 = BackendAgeGroupModel.ENUM_51_MINUS_65
    OVER_65 = BackendAgeGroupModel.ENUM_65_PLUS

    def _to_backend_model(self) -> BackendAgeGroupModel:
        return BackendAgeGroupModel(self.value)

