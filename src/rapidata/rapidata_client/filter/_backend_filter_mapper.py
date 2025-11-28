from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.and_filter_filters_inner import (
        AndFilterFiltersInner,
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

        from rapidata.api_client.models.and_filter import AndFilter
        from rapidata.api_client.models.campaign_filter import CampaignFilter
        from rapidata.api_client.models.country_filter import CountryFilter
        from rapidata.api_client.models.demographic_filter import DemographicFilter
        from rapidata.api_client.models.language_filter import LanguageFilter
        from rapidata.api_client.models.new_user_filter import NewUserFilter
        from rapidata.api_client.models.not_filter import NotFilter
        from rapidata.api_client.models.or_filter import OrFilter
        from rapidata.api_client.models.response_count_filter import ResponseCountFilter
        from rapidata.api_client.models.user_action_restriction_filter import (
            UserActionRestrictionFilter,
        )
        from rapidata.api_client.models.user_score_filter import UserScoreFilter
        from rapidata.api_client.models.user_state_filter import UserStateFilter

        cls._imported_backend_filters = {
            "AndFilter": AndFilter,
            "CampaignFilter": CampaignFilter,
            "CountryFilter": CountryFilter,
            "DemographicFilter": DemographicFilter,
            "LanguageFilter": LanguageFilter,
            "NewUserFilter": NewUserFilter,
            "NotFilter": NotFilter,
            "OrFilter": OrFilter,
            "ResponseCountFilter": ResponseCountFilter,
            "UserActionRestrictionFilter": UserActionRestrictionFilter,
            "UserScoreFilter": UserScoreFilter,
            "UserStateFilter": UserStateFilter,
        }

    @classmethod
    def _ensure_client_filters_imported(cls) -> None:
        """Lazy import all client filter models."""
        if cls._imported_client_filters:
            return

        from rapidata.rapidata_client.filter.and_filter import AndFilter
        from rapidata.rapidata_client.filter.campaign_filter import CampaignFilter
        from rapidata.rapidata_client.filter.country_filter import CountryFilter
        from rapidata.rapidata_client.filter.language_filter import LanguageFilter
        from rapidata.rapidata_client.filter.new_user_filter import NewUserFilter
        from rapidata.rapidata_client.filter.not_filter import NotFilter
        from rapidata.rapidata_client.filter.or_filter import OrFilter
        from rapidata.rapidata_client.filter.response_count_filter import (
            ResponseCountFilter,
        )
        from rapidata.rapidata_client.filter.user_score_filter import UserScoreFilter

        cls._imported_client_filters = {
            "AndFilter": AndFilter,
            "CampaignFilter": CampaignFilter,
            "CountryFilter": CountryFilter,
            "LanguageFilter": LanguageFilter,
            "NewUserFilter": NewUserFilter,
            "NotFilter": NotFilter,
            "OrFilter": OrFilter,
            "ResponseCountFilter": ResponseCountFilter,
            "UserScoreFilter": UserScoreFilter,
        }

    @classmethod
    def backend_filter_from_rapidata_filter(
        cls, filter: AndFilterFiltersInner
    ) -> RapidataFilter:
        """Convert a backend API filter model to a client-side RapidataFilter instance.

        Args:
            filter: Backend API filter wrapped in AndFilterFiltersInner

        Returns:
            RapidataFilter: Client-side filter instance
        """
        cls._ensure_backend_filters_imported()
        cls._ensure_client_filters_imported()

        actual_instance = filter.actual_instance
        if actual_instance is None:
            raise ValueError("Filter actual_instance is None")

        # Import backend models for isinstance checks
        BackendAndFilter = cls._imported_backend_filters["AndFilter"]
        BackendOrFilter = cls._imported_backend_filters["OrFilter"]
        BackendNotFilter = cls._imported_backend_filters["NotFilter"]
        BackendCampaignFilter = cls._imported_backend_filters["CampaignFilter"]
        BackendCountryFilter = cls._imported_backend_filters["CountryFilter"]
        BackendLanguageFilter = cls._imported_backend_filters["LanguageFilter"]
        BackendNewUserFilter = cls._imported_backend_filters["NewUserFilter"]
        BackendResponseCountFilter = cls._imported_backend_filters[
            "ResponseCountFilter"
        ]
        BackendUserScoreFilter = cls._imported_backend_filters["UserScoreFilter"]
        BackendDemographicFilter = cls._imported_backend_filters["DemographicFilter"]
        BackendUserActionRestrictionFilter = cls._imported_backend_filters[
            "UserActionRestrictionFilter"
        ]
        BackendUserStateFilter = cls._imported_backend_filters["UserStateFilter"]

        # Import client models
        ClientAndFilter = cls._imported_client_filters["AndFilter"]
        ClientOrFilter = cls._imported_client_filters["OrFilter"]
        ClientNotFilter = cls._imported_client_filters["NotFilter"]
        ClientCampaignFilter = cls._imported_client_filters["CampaignFilter"]
        ClientCountryFilter = cls._imported_client_filters["CountryFilter"]
        ClientLanguageFilter = cls._imported_client_filters["LanguageFilter"]
        ClientNewUserFilter = cls._imported_client_filters["NewUserFilter"]
        ClientResponseCountFilter = cls._imported_client_filters["ResponseCountFilter"]
        ClientUserScoreFilter = cls._imported_client_filters["UserScoreFilter"]

        # Handle recursive filters (AndFilter, OrFilter, NotFilter)
        if isinstance(actual_instance, BackendAndFilter):
            return ClientAndFilter(
                [
                    cls.backend_filter_from_rapidata_filter(child_filter)
                    for child_filter in actual_instance.filters  # type: ignore[attr-defined]
                ]
            )
        elif isinstance(actual_instance, BackendOrFilter):
            return ClientOrFilter(
                [
                    cls.backend_filter_from_rapidata_filter(child_filter)
                    for child_filter in actual_instance.filters  # type: ignore[attr-defined]
                ]
            )
        elif isinstance(actual_instance, BackendNotFilter):
            return ClientNotFilter(
                cls.backend_filter_from_rapidata_filter(actual_instance.filter)  # type: ignore[attr-defined]
            )

        # Handle simple filters with straightforward mappings
        elif isinstance(actual_instance, BackendCampaignFilter):
            return ClientCampaignFilter(actual_instance.campaign_ids)  # type: ignore[attr-defined]
        elif isinstance(actual_instance, BackendCountryFilter):
            return ClientCountryFilter(actual_instance.countries)  # type: ignore[attr-defined]
        elif isinstance(actual_instance, BackendLanguageFilter):
            return ClientLanguageFilter(actual_instance.languages)  # type: ignore[attr-defined]
        elif isinstance(actual_instance, BackendNewUserFilter):
            return ClientNewUserFilter()
        elif isinstance(actual_instance, BackendResponseCountFilter):
            return ClientResponseCountFilter(
                response_count=actual_instance.response_count,  # type: ignore[attr-defined]
                dimension=actual_instance.dimension,  # type: ignore[attr-defined]
                operator=actual_instance.operator,  # type: ignore[attr-defined]
            )
        elif isinstance(actual_instance, BackendUserScoreFilter):
            return ClientUserScoreFilter(
                lower_bound=actual_instance.lowerbound,  # type: ignore[attr-defined]
                upper_bound=actual_instance.upperbound,  # type: ignore[attr-defined]
                dimension=actual_instance.dimension,  # type: ignore[attr-defined]
            )

        # Filters that don't have direct client equivalents
        elif isinstance(
            actual_instance,
            (
                BackendDemographicFilter,
                BackendUserActionRestrictionFilter,
                BackendUserStateFilter,
            ),
        ):
            backend_type_name = type(actual_instance).__name__
            raise NotImplementedError(
                f"{backend_type_name} does not have a client-side equivalent yet"
            )

        else:
            backend_type_name = type(actual_instance).__name__
            raise ValueError(f"Unhandled filter type: {backend_type_name}")
