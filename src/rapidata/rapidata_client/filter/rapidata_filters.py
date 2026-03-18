from rapidata.rapidata_client.filter.country_filter import CountryFilter
from rapidata.rapidata_client.filter.language_filter import LanguageFilter
from rapidata.rapidata_client.filter.not_filter import NotFilter
from rapidata.rapidata_client.filter.or_filter import OrFilter
from rapidata.rapidata_client.filter.and_filter import AndFilter


class RapidataFilters:
    """RapidataFilters Classes

    These filters can be added to the order to specifically target a certain group of users.

    Note that adding multiple filters to the same order will result in a logical AND operation between the filters.

    Warning:
        This might significantly slow down the number of responses you receive.

    Attributes:
        Country (CountryFilter): Filters for users with a specific country.
        Language (LanguageFilter): Filters for users with a specific language.
        Not (NotFilter): Inverts the filter.
        Or (OrFilter): Combines multiple filters with a logical OR operation.
        And (AndFilter): Combines multiple filters with a logical AND operation.

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
        from rapidata import LanguageFilter, CountryFilter
        filters=[(CountryFilter(["US"]) & ~LanguageFilter(["fr"])) | (CountryFilter(["CA"]) & LanguageFilter(["en"]))]
        ```

        This would return users who are from the US and whose phones are not set to French or who are from Canada and whose phones are set to English.
    """

    Country = CountryFilter
    Language = LanguageFilter
    Not = NotFilter
    Or = OrFilter
    And = AndFilter
