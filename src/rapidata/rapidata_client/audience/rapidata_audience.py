from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Sequence
from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
from rapidata.rapidata_client.audience.audience_example_handler import (
    AudienceExampleHandler,
)
from rapidata.rapidata_client.datapoints._datapoint import coerce_media_context

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.audience.rapidata_filtered_audience import (
        RapidataFilteredAudience,
    )
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.rapidata_client.validation.rapids.rapids import Rapid
    from rapidata.rapidata_client.validation.rapids.box import Box
    from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting
    import pandas as pd


class RapidataAudience(RapidataAudienceBase):
    """A Rapidata dimension audience.

    A dimension audience is a group of annotators recruited via qualification examples
    and (optionally) recruitment filters. Use :py:meth:`filter` to derive a
    :class:`RapidataFilteredAudience` — a lightweight slice that reuses the same pool
    without new recruiting.
    """

    def __init__(
        self,
        id: str,
        name: str,
        filters: list[RapidataFilter],
        openapi_service: OpenAPIService,
    ):
        super().__init__(
            id=id, name=name, filters=filters, openapi_service=openapi_service
        )
        self._example_handler = AudienceExampleHandler(openapi_service, id)
        self._recruiting_started = False

    def delete(self) -> None:
        """Deletes the audience."""
        with tracer.start_as_current_span("RapidataAudience.delete"):
            logger.info("Deleting audience '%s'", self)
            self._openapi_service.audience.audience_api.audience_audience_id_delete(
                self.id
            )
            logger.debug("Audience '%s' has been deleted.", self)
            managed_print(f"Audience '{self}' has been deleted.")

    def filter(self, filters: list[RapidataFilter]) -> RapidataFilteredAudience:
        """Derive a filtered audience from this audience.

        Applies the given filters on top of this audience's graduated annotators and returns
        a lightweight, filtered audience. The filtered audience reuses this audience's pool of
        qualified annotators — no new recruiting or onboarding takes place. The returned id can
        be passed to job and leaderboard creation in place of a regular audience id.

        Supported filter types: ``CountryFilter``, ``LanguageFilter``, ``DemographicFilter``,
        and the combinators ``AndFilter`` / ``OrFilter`` / ``NotFilter`` (also via the
        ``&`` / ``|`` / ``~`` operators).

        Args:
            filters (list[RapidataFilter]): One or more filters to apply. Multiple filters are
                combined with a logical AND. Pass a single ``AndFilter`` / ``OrFilter`` /
                ``NotFilter`` if you need a different combinator at the top level.

        Returns:
            RapidataFilteredAudience: A slim audience handle representing the filtered view.
            Only exposes operations that make sense for a filtered audience
            (``assign_job``, ``find_jobs``, ``delete``); methods like
            ``add_classification_example`` are intentionally absent because the filtered
            audience reuses the base's qualified pool.

        Example:
            ```python
            from rapidata import CountryFilter, DemographicFilter

            base = client.audience.get_audience_by_id("aud_...")
            us_under_30 = base.filter(
                [CountryFilter(["US"]), DemographicFilter("age", ["18-29"])]
            )
            benchmark.create_leaderboard(
                name="my-leaderboard",
                instruction="Pick the better image",
                audience_id=us_under_30.id,
            )
            ```
        """
        with tracer.start_as_current_span("RapidataAudience.filter"):
            from rapidata.api_client.models.create_filtered_audience_endpoint_input import (
                CreateFilteredAudienceEndpointInput,
            )
            from rapidata.rapidata_client.audience.rapidata_filtered_audience import (
                RapidataFilteredAudience,
            )
            from rapidata.rapidata_client.filter.and_filter import AndFilter

            if not filters:
                raise ValueError("At least one filter must be provided.")

            top_level = filters[0] if len(filters) == 1 else AndFilter(filters)

            logger.debug(
                f"Creating filtered audience from {self.id} with filters: {filters}"
            )
            response = self._openapi_service.audience.audience_api.audience_base_audience_id_filter_post(
                base_audience_id=self.id,
                create_filtered_audience_endpoint_input=CreateFilteredAudienceEndpointInput(
                    filter=top_level._to_audience_model(),
                ),
            )
            logger.info(
                f"Created filtered audience {response.audience_id} from base {self.id}"
            )
            return RapidataFilteredAudience(
                id=response.audience_id,
                name=self._name,
                filters=list(filters),
                openapi_service=self._openapi_service,
            )

    def update_filters(self, filters: list[RapidataFilter]) -> RapidataAudience:
        """Update the filters for this audience.

        Args:
            filters (list[RapidataFilter]): The new list of filters to apply to the audience.

        Returns:
            RapidataAudience: The updated audience instance (self) for method chaining.
        """
        with tracer.start_as_current_span("RapidataAudience.update_filters"):
            from rapidata.api_client.models.update_audience_endpoint_input import (
                UpdateAudienceEndpointInput,
            )

            logger.debug(f"Updating filters for audience: {self.id} to {filters}")
            self._openapi_service.audience.audience_api.audience_audience_id_patch(
                audience_id=self.id,
                update_audience_endpoint_input=UpdateAudienceEndpointInput(
                    filters=[filter._to_audience_model() for filter in filters],
                ),
            )
            self._filters = filters
            return self

    def update_name(self, name: str) -> RapidataAudience:
        """Update the name of this audience.

        Args:
            name (str): The new name for the audience.

        Returns:
            RapidataAudience: The updated audience instance (self) for method chaining.
        """
        with tracer.start_as_current_span("RapidataAudience.update_name"):
            from rapidata.api_client.models.update_audience_endpoint_input import (
                UpdateAudienceEndpointInput,
            )

            logger.debug(f"Updating name for audience: {self.id} to {name}")
            self._openapi_service.audience.audience_api.audience_audience_id_patch(
                audience_id=self.id,
                update_audience_endpoint_input=UpdateAudienceEndpointInput(name=name),
            )
            self._name = name
            return self

    def add_classification_example(
        self,
        instruction: str,
        answer_options: list[str],
        datapoint: str,
        truth: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: list[str] | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> RapidataAudience:
        """Add a classification training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample datapoint with the correct answer before they start labeling.

        Args:
            instruction (str): The instruction for how the data should be classified.
            answer_options (list[str]): The list of possible answer options for the classification.
            datapoint (str): The datapoint (URL or path) to use as the training example.
            truth (list[str]): The correct answer(s) for this training example.
            data_type (Literal["media", "text"], optional): The data type of the datapoint. Defaults to "media".
            context (str, optional): Additional text context to display with the example. Defaults to None.
            media_context (list[str], optional): Additional image URLs / paths to display with the example. Pass a single-element list for one image, or multiple to display several images. Defaults to None.
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature flags on this example. Use the same ``RapidataSetting`` subclasses available on jobs/orders (e.g. ``NoShuffleSetting``, ``MarkdownSetting``) so the qualification example matches how the actual task will be rendered. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        media_context = coerce_media_context(media_context)
        with tracer.start_as_current_span(
            "RapidataAudience.add_classification_example"
        ):
            logger.debug(
                f"Adding classification example to audience: {self.id} with instruction: {instruction}, answer_options: {answer_options}, datapoint: {datapoint}, truths: {truth}, data_type: {data_type}, context: {context}, media_context: {media_context}, explanation: {explanation}, settings: {settings}"
            )
            self._example_handler.add_classification_example(
                instruction,
                answer_options,
                datapoint,
                truth,
                data_type,
                context,
                media_context,
                explanation,
                settings,
            )
            self._try_start_recruiting()
            return self

    def add_compare_example(
        self,
        instruction: str,
        truth: str,
        datapoint: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: list[str] | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> RapidataAudience:
        """Add a comparison training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample comparison with the correct answer before they start labeling.

        Args:
            instruction (str): The instruction for the comparison task.
            truth (str): The correct answer for this training example (which option should be selected).
            datapoint (list[str]): A list of exactly two datapoints (URLs or paths) to compare.
            data_type (Literal["media", "text"], optional): The data type of the datapoints. Defaults to "media".
            context (str, optional): Additional text context to display with the example. Defaults to None.
            media_context (list[str], optional): Additional image URLs / paths to display with the example. Pass a single-element list for one image, or multiple to display several images. Defaults to None.
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature flags on this example. Use the same ``RapidataSetting`` subclasses available on jobs/orders (e.g. ``AllowNeitherBothSetting``, ``ComparePanoramaSetting``) so the qualification example matches how the actual task will be rendered. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        media_context = coerce_media_context(media_context)
        with tracer.start_as_current_span("RapidataAudience.add_compare_example"):
            logger.debug(
                f"Adding compare example to audience: {self.id} with instruction: {instruction}, truth: {truth}, datapoint: {datapoint}, data_type: {data_type}, context: {context}, media_context: {media_context}, explanation: {explanation}, settings: {settings}"
            )
            self._example_handler.add_compare_example(
                instruction,
                truth,
                datapoint,
                data_type,
                context,
                media_context,
                explanation,
                settings,
            )
            self._try_start_recruiting()
            return self

    def add_locate_example(
        self,
        instruction: str,
        datapoint: str,
        truths: list[Box],
        context: str | None = None,
        media_context: list[str] | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> RapidataAudience:
        """Add a locate training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample datapoint with the correct regions before they start labeling.

        Args:
            instruction (str): The instruction telling annotators what to locate.
            datapoint (str): The media datapoint (URL or path) to use as the training example.
            truths (list[Box]): The bounding boxes covering the correct regions to tap, as :class:`Box` objects with coordinates in image ratios (0.0 to 1.0).
            context (str, optional): Additional text context to display with the example. Defaults to None.
            media_context (list[str], optional): Additional image URLs / paths to display with the example. Pass a single-element list for one image, or multiple to display several images. Defaults to None.
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature flags on this example so the qualification example matches how the actual task will be rendered. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        media_context = coerce_media_context(media_context)
        with tracer.start_as_current_span("RapidataAudience.add_locate_example"):
            logger.debug(
                f"Adding locate example to audience: {self.id} with instruction: {instruction}, datapoint: {datapoint}, truths: {truths}, context: {context}, media_context: {media_context}, explanation: {explanation}, settings: {settings}"
            )
            self._example_handler.add_locate_example(
                instruction,
                datapoint,
                truths,
                context,
                media_context,
                explanation,
                settings,
            )
            self._try_start_recruiting()
            return self

    def add_draw_example(
        self,
        instruction: str,
        datapoint: str,
        truths: list[Box],
        context: str | None = None,
        media_context: list[str] | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> RapidataAudience:
        """Add a draw training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample datapoint with the correct regions before they start labeling.

        Args:
            instruction (str): The instruction telling annotators what to draw.
            datapoint (str): The media datapoint (URL or path) to use as the training example.
            truths (list[Box]): The bounding boxes covering the correct regions — annotators are graded on whether their drawn lines fall within any of these boxes. :class:`Box` coordinates are image ratios (0.0 to 1.0).
            context (str, optional): Additional text context to display with the example. Defaults to None.
            media_context (list[str], optional): Additional image URLs / paths to display with the example. Pass a single-element list for one image, or multiple to display several images. Defaults to None.
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature flags on this example so the qualification example matches how the actual task will be rendered. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        media_context = coerce_media_context(media_context)
        with tracer.start_as_current_span("RapidataAudience.add_draw_example"):
            logger.debug(
                f"Adding draw example to audience: {self.id} with instruction: {instruction}, datapoint: {datapoint}, truths: {truths}, context: {context}, media_context: {media_context}, explanation: {explanation}, settings: {settings}"
            )
            self._example_handler.add_draw_example(
                instruction,
                datapoint,
                truths,
                context,
                media_context,
                explanation,
                settings,
            )
            self._try_start_recruiting()
            return self

    def add_select_words_example(
        self,
        instruction: str,
        datapoint: str,
        sentence: str,
        truths: list[int],
        required_precision: float = 1,
        required_completeness: float = 1,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> RapidataAudience:
        """Add a select words training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample datapoint with the correct words before they start labeling.

        Args:
            instruction (str): The instruction telling annotators which words to select.
            datapoint (str): The media datapoint (URL or path) to use as the training example.
            sentence (str): The sentence the annotators will be selecting words from. (split up by spaces)
            truths (list[int]): The indices of the words that are the correct answers.
            required_precision (float): The required precision for the annotator to get the example correct (minimum ratio of the words selected that need to be correct). Defaults to 1. (no wrong words can be selected)
            required_completeness (float): The required completeness for the annotator to get the example correct (minimum ratio of total correct words selected). Defaults to 1. (all correct words need to be selected)
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature flags on this example so the qualification example matches how the actual task will be rendered. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        with tracer.start_as_current_span("RapidataAudience.add_select_words_example"):
            logger.debug(
                f"Adding select words example to audience: {self.id} with instruction: {instruction}, datapoint: {datapoint}, sentence: {sentence}, truths: {truths}, explanation: {explanation}, settings: {settings}"
            )
            self._example_handler.add_select_words_example(
                instruction,
                datapoint,
                sentence,
                truths,
                required_precision,
                required_completeness,
                explanation,
                settings,
            )
            self._try_start_recruiting()
            return self

    def get_examples(
        self,
        amount: int = 10,
        page: int = 1,
    ) -> pd.DataFrame:
        """Get the examples for this audience as a DataFrame.

        Returns a DataFrame with columns: asset, truth, context, contextAsset.
        Asset URLs are fully qualified with the environment's asset host.

        Args:
            amount: Number of examples per page.
            page: Page number.

        Returns:
            A DataFrame containing the examples.
        """
        with tracer.start_as_current_span("RapidataAudience.get_examples"):
            import pandas as pd

            from rapidata.rapidata_client.audience.example_formatter import (
                ExampleFormatter,
            )

            response = self._openapi_service.audience.examples_api.audience_audience_id_examples_get(
                audience_id=self.id,
                page=page,
                page_size=amount,
            )
            asset_url_prefix = f"https://assets.{self._openapi_service.environment}/"
            rows = ExampleFormatter.format_to_csv_rows(response.items, asset_url_prefix)
            return pd.DataFrame(rows)

    def _add_rapid_example(self, rapid: Rapid) -> RapidataAudience:
        """Add a rapid example to this audience (private method).

        Args:
            rapid (Rapid): The rapid object created via RapidsManager to add as an example.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        with tracer.start_as_current_span("RapidataAudience._add_rapid_example"):
            logger.debug(f"Adding rapid example to audience: {self.id}")
            self._example_handler._add_rapid_example(rapid)
            self._try_start_recruiting()
            return self

    def _try_start_recruiting(self) -> None:
        """Try to start recruiting annotators for this audience.

        This will begin the process of onboarding annotators for this audience.
        If the recruiting has already started, it will do nothing.
        """
        from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError

        if self._recruiting_started:
            logger.debug(f"Recruiting already started for audience: {self.id}")
            return

        with tracer.start_as_current_span("RapidataAudience._try_start_recruiting"):
            from rapidata.rapidata_client.api.rapidata_api_client import (
                suppress_rapidata_error_logging,
            )

            logger.debug(f"Sending request to start recruiting for audience: {self.id}")
            with suppress_rapidata_error_logging():
                try:
                    self._openapi_service.audience.audience_api.audience_audience_id_recruit_post(
                        audience_id=self.id,
                    )
                    logger.info(f"Started recruiting for audience: {self.id}")
                    self._recruiting_started = True
                except RapidataError as e:
                    logger.debug(
                        f"Error starting recruiting for audience: {self.id} - {e}"
                    )
