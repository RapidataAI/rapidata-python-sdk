from rapidata.rapidata_client.filter import (
    AgeFilter, 
    CountryFilter, 
    GenderFilter, 
    LanguageFilter, 
    UserScoreFilter,
    NotFilter,
    OrFilter)

class RapidataFilters:
    """RapidataFilters Classes

    These filters can be added to the order to specifically target a certain group of users.

    Note that adding multiple filters to the same order will result in a logical AND operation between the filters.

    Warning: 
        This might significantly slow down the number of responses you receive.
    
    Attributes:
        user_score (UserScoreFilter): The UserScoreFilter instance.
        age (AgeFilter): The AgeFilter instance.
        country (CountryFilter): The CountryFilter instance.
        gender (GenderFilter): The GenderFilter instance.
        language (LanguageFilter): The LanguageFilter instance.
        not_filter (NotFilter): The NotFilter instance.
        or_filter (OrFilter): The OrFilter instance.

    Example:
        ```python
        from rapidata import CountryFilter, LanguageFilter
        filters=[CountryFilter(["US", "DE"]), LanguageFilter(["en"])]
        ```

        This ensures the order is only shown to users in the US and Germany whose phones are set to English.

    Info:        
        The or and not filter support the | and ~ operators respectively.
        The and is given by the elements in the list.

        ```python
        from rapidata import AgeFilter, LanguageFilter, CountryFilter
        filters=[~AgeFilter([AgeGroup.UNDER_18]), CountryFilter(["US"]) | LanguageFilter(["en"])]
        ```

        This would return users who are not under 18 years old and are from the US or whose phones are set to English.
    """
    user_score = UserScoreFilter
    age = AgeFilter 
    country = CountryFilter
    gender = GenderFilter
    language = LanguageFilter
    not_filter = NotFilter
    or_filter = OrFilter
