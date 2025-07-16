from rapidata.rapidata_client.filter import (
    AgeFilter, 
    CountryFilter, 
    GenderFilter, 
    LanguageFilter, 
    UserScoreFilter,
    NotFilter,
    OrFilter,
    AndFilter)

class RapidataFilters:
    """RapidataFilters Classes

    These filters can be added to the order to specifically target a certain group of users.

    Note that adding multiple filters to the same order will result in a logical AND operation between the filters.

    Warning: 
        This might significantly slow down the number of responses you receive.
    
    Attributes:
        user_score (UserScoreFilter): Filters for users with a specific user score.
        age (AgeFilter): Filters for users with a specific age.
        country (CountryFilter): Filters for users with a specific country.
        gender (GenderFilter): Filters for users with a specific gender.
        language (LanguageFilter): Filters for users with a specific language.
        not_filter (NotFilter): Inverts the filter.
        or_filter (OrFilter): Combines multiple filters with a logical OR operation.
        and_filter (AndFilter): Combines multiple filters with a logical AND operation.

    Example:
        ```python
        from rapidata import CountryFilter, LanguageFilter
        filters=[CountryFilter(["US", "DE"]), LanguageFilter(["en"])]
        ```

        This ensures the order is only shown to users in the US and Germany whose phones are set to English.

    Info:        
        The OR, AND and NOT filter support the |, & and ~ operators respectively.
        The AND is additionally given by the elements in the list.

        ```python
        from rapidata import AgeFilter, LanguageFilter, CountryFilter
        filters=[~AgeFilter([AgeGroup.UNDER_18]), CountryFilter(["US"]) | (CountryFilter(["CA"]) & LanguageFilter(["en"]))]
        ```

        This would return users who are not under 18 years old and are from the US or who are from Canada and whose phones are set to English.
    """
    user_score = UserScoreFilter
    age = AgeFilter 
    country = CountryFilter
    gender = GenderFilter
    language = LanguageFilter
    not_filter = NotFilter
    or_filter = OrFilter
    and_filter = AndFilter
