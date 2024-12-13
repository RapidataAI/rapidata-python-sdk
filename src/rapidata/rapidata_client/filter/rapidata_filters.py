from rapidata.rapidata_client.filter import (
    AgeFilter, 
    CampaignFilter, 
    CountryFilter, 
    GenderFilter, 
    LanguageFilter, 
    UserScoreFilter)

class RapidataFilters:
    """RapidataFilters Classes
    
    Attributes:
        user_score (UserScoreFilter): The UserScoreFilter instance.
        age (AgeFilter): The AgeFilter instance.
        campaign (CampaignFilter): The CampaignFilter instance.
        country (CountryFilter): The CountryFilter instance.
        campaign (CampaignFilter): The CampaignFilter instance
        gender (GenderFilter): The GenderFilter instance.
        language (LanguageFilter): The LanguageFilter instance."""
    user_score = UserScoreFilter
    age = AgeFilter 
    campaign = CampaignFilter
    country = CountryFilter
    gender = GenderFilter
    language = LanguageFilter
