from rapidata.rapidata_client.filter import (
    AgeFilter, 
    CampaignFilter, 
    CountryFilter, 
    GenderFilter, 
    LanguageFilter, 
    UserScoreFilter,
    CustomFilter)

class RapidataFilters:
    """RapidataFilters Classes

    These filters can be added to the order to specifically target a certain group of users.

    Note that adding multiple filters to the same order will result in a logical AND operation between the filters.

    Warning: this might significantly slow down the number of responses you receive.
    
    Attributes:
        user_score (UserScoreFilter): The UserScoreFilter instance.
        age (AgeFilter): The AgeFilter instance.
        campaign (CampaignFilter): The CampaignFilter instance.
        country (CountryFilter): The CountryFilter instance.
        campaign (CampaignFilter): The CampaignFilter instance
        gender (GenderFilter): The GenderFilter instance.
        language (LanguageFilter): The LanguageFilter instance.
        custom_filter (CustomFilter): The CustomFilter instance.
    """
    user_score = UserScoreFilter
    age = AgeFilter 
    campaign = CampaignFilter
    country = CountryFilter
    gender = GenderFilter
    language = LanguageFilter
    custom_filter = CustomFilter
