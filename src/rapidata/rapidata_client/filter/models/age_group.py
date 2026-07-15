from rapidata.api_client.models.age_user_filter_age_group import (
    AgeUserFilterAgeGroup,
)
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

    UNDER_18 = AgeUserFilterAgeGroup.ENUM_0_MINUS_17
    BETWEEN_18_29 = AgeUserFilterAgeGroup.ENUM_18_MINUS_29
    BETWEEN_30_39 = AgeUserFilterAgeGroup.ENUM_30_MINUS_39
    BETWEEN_40_49 = AgeUserFilterAgeGroup.ENUM_40_MINUS_49
    BETWEEN_50_64 = AgeUserFilterAgeGroup.ENUM_50_MINUS_64
    OVER_65 = AgeUserFilterAgeGroup.ENUM_65_PLUS

    def _to_backend_model(self) -> AgeUserFilterAgeGroup:
        return AgeUserFilterAgeGroup(self.value)
