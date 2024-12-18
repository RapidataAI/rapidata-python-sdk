from rapidata.api_client.models.age_group import AgeGroup as BackendAgeGroupModel
from enum import Enum

class AgeGroup(Enum):
    """AgeGroup Enum
    
    Represents the age group of a user. Used to filter who to target based on age groups.
    
    Attributes:
        UNDER_18 (AgeGroup): Represents the age group of users under 18.
        BETWEEN_18_29 (AgeGroup): Represents the age group of users between 18 and 29.
        BETWEEN_30_39 (AgeGroup): Represents the age group of users between 30 and 39.
        BETWEEN_40_49 (AgeGroup): Represents the age group of users between 40 and 49.
        BETWEEN_50_64 (AgeGroup): Represents the age group of users between 50 and 64.
        OVER_65 (AgeGroup): Represents the age group of users over 65."""
    
    UNDER_18 = BackendAgeGroupModel.ENUM_0_MINUS_17
    BETWEEN_18_29 = BackendAgeGroupModel.ENUM_18_MINUS_29
    BETWEEN_30_39 = BackendAgeGroupModel.ENUM_30_MINUS_39
    BETWEEN_40_49 = BackendAgeGroupModel.ENUM_40_MINUS_49
    BETWEEN_50_64 = BackendAgeGroupModel.ENUM_50_MINUS_64
    OVER_65 = BackendAgeGroupModel.ENUM_65_PLUS

    def _to_backend_model(self) -> BackendAgeGroupModel:
        return BackendAgeGroupModel(self.value)

