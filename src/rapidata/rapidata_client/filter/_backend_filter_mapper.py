from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_audience_filter import (
        IAudienceFilter,
    )
    from rapidata.rapidata_client.filter._base_filter import RapidataFilter


class BackendFilterMapper:
    """Maps backend API filter models to client-side RapidataFilter instances."""

    # Cache for imported modules to avoid repeated imports
    _imported_backend_filters: dict[str, Any] = {}
    _imported_client_filters: dict[str, Any] = {}

    @classmethod
    def _ensure_backend_filters_imported(cls) -> None:
        """Lazy import all backend filter models."""
        if cls._imported_backend_filters:
            return

        from rapidata.api_client.models.i_audience_filter_and_audience_filter import (
            IAudienceFilterAndAudienceFilter,
        )
        from rapidata.api_client.models.i_audience_filter_or_audience_filter import (
            IAudienceFilterOrAudienceFilter,
        )
        from rapidata.api_client.models.i_audience_filter_not_audience_filter import (
            IAudienceFilterNotAudienceFilter,
        )
        from rapidata.api_client.models.i_audience_filter_country_audience_filter import (
            IAudienceFilterCountryAudienceFilter,
        )
        from rapidata.api_client.models.i_audience_filter_language_audience_filter import (
            IAudienceFilterLanguageAudienceFilter,
        )

        cls._imported_backend_filters = {
            "AndAudienceFilter": IAudienceFilterAndAudienceFilter,
            "OrAudienceFilter": IAudienceFilterOrAudienceFilter,
            "NotAudienceFilter": IAudienceFilterNotAudienceFilter,
            "CountryAudienceFilter": IAudienceFilterCountryAudienceFilter,
            "LanguageAudienceFilter": IAudienceFilterLanguageAudienceFilter,
        }

    @classmethod
    def _ensure_client_filters_imported(cls) -> None:
        """Lazy import all client filter models."""
        if cls._imported_client_filters:
            return

        from rapidata.rapidata_client.filter.and_filter import AndFilter
        from rapidata.rapidata_client.filter.country_filter import CountryFilter
        from rapidata.rapidata_client.filter.language_filter import LanguageFilter
        from rapidata.rapidata_client.filter.not_filter import NotFilter
        from rapidata.rapidata_client.filter.or_filter import OrFilter

        cls._imported_client_filters = {
            "AndFilter": AndFilter,
            "CountryFilter": CountryFilter,
            "LanguageFilter": LanguageFilter,
            "NotFilter": NotFilter,
            "OrFilter": OrFilter,
        }

    @classmethod
    def backend_filter_from_rapidata_filter(
        cls, filter: IAudienceFilter
    ) -> RapidataFilter:
        """Convert a backend API filter model to a client-side RapidataFilter instance.

        Args:
            filter: Backend API filter wrapped in IAudienceFilter

        Returns:
            RapidataFilter: Client-side filter instance
        """
        cls._ensure_backend_filters_imported()
        cls._ensure_client_filters_imported()

        actual_instance = filter.actual_instance
        if actual_instance is None:
            raise ValueError("Filter actual_instance is None")

        # Import backend models for isinstance checks
        BackendAndAudienceFilter = cls._imported_backend_filters["AndAudienceFilter"]
        BackendOrAudienceFilter = cls._imported_backend_filters["OrAudienceFilter"]
        BackendNotAudienceFilter = cls._imported_backend_filters["NotAudienceFilter"]
        BackendCountryAudienceFilter = cls._imported_backend_filters[
            "CountryAudienceFilter"
        ]
        BackendLanguageAudienceFilter = cls._imported_backend_filters[
            "LanguageAudienceFilter"
        ]

        # Import client models
        ClientAndFilter = cls._imported_client_filters["AndFilter"]
        ClientOrFilter = cls._imported_client_filters["OrFilter"]
        ClientNotFilter = cls._imported_client_filters["NotFilter"]
        ClientCountryFilter = cls._imported_client_filters["CountryFilter"]
        ClientLanguageFilter = cls._imported_client_filters["LanguageFilter"]

        # Handle recursive filters (AndFilter, OrFilter, NotFilter)
        if isinstance(actual_instance, BackendAndAudienceFilter):
            return ClientAndFilter(
                [
                    cls.backend_filter_from_rapidata_filter(child_filter)
                    for child_filter in actual_instance.filters  # type: ignore[attr-defined]
                ]
            )
        elif isinstance(actual_instance, BackendOrAudienceFilter):
            return ClientOrFilter(
                [
                    cls.backend_filter_from_rapidata_filter(child_filter)
                    for child_filter in actual_instance.filters  # type: ignore[attr-defined]
                ]
            )
        elif isinstance(actual_instance, BackendNotAudienceFilter):
            return ClientNotFilter(
                cls.backend_filter_from_rapidata_filter(actual_instance.filter)  # type: ignore[attr-defined]
            )

        # Handle simple filters with straightforward mappings
        elif isinstance(actual_instance, BackendCountryAudienceFilter):
            return ClientCountryFilter(actual_instance.countries)  # type: ignore[attr-defined]
        elif isinstance(actual_instance, BackendLanguageAudienceFilter):
            return ClientLanguageFilter(actual_instance.languages)  # type: ignore[attr-defined]

        else:
            backend_type_name = type(actual_instance).__name__
            raise ValueError(f"Unhandled filter type: {backend_type_name}")
