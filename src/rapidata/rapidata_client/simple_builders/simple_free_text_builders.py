from rapidata.constants import MAX_TIME_IN_SECONDS_FOR_ONE_SESSION
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.workflow import FreeTextWorkflow
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, BaseAsset
from rapidata.rapidata_client.filter import Filter, CountryFilter, LanguageFilter
from rapidata.rapidata_client.settings import Settings, TranslationBehaviour

class FreeTextOrderBuilder:
    def __init__(self, 
                 name: str, 
                 question: str, 
                 media_assets: list[BaseAsset], 
                 openapi_service: OpenAPIService, 
                 time_effort: int):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._question = question
        self._media_assets = media_assets
        self._referee = NaiveReferee()
        self._settings = Settings()
        self._filters: list[Filter] = []
        self._time_effort = time_effort

    def responses(self, responses_required: int) -> 'FreeTextOrderBuilder':
        """Set the number of responses required per datapoint for the free text order. Will default to 10."""
        self._referee = NaiveReferee(responses=responses_required)
        return self
    
    def minimum_characters(self, minimum_characters: int) -> 'FreeTextOrderBuilder':
        """Set the minimum number of characters for the free text."""
        self._settings.free_text_minimum_characters(minimum_characters)
        return self
    
    def countries(self, country_codes: list[str]) -> 'FreeTextOrderBuilder':
        """Set the countries where order will be shown as country codes."""
        self._filters.append(CountryFilter(country_codes))
        return self
    
    def languages(self, language_codes: list[str]) -> 'FreeTextOrderBuilder':
        """Set the languages where order will be shown as language codes."""
        self._filters.append(LanguageFilter(language_codes))
        return self
    
    def translation(self, disable: bool = False, show_both: bool = False) -> 'FreeTextOrderBuilder':
        """Disable the translation of the order.
        Only the question will be translated.
        
        Args:
            disable (bool): Whether to disable the translation. Defaults to False.
            show_both (bool): Whether to show the original text alongside the translation. Defaults to False.
                ATTENTION: this can lead to cluttering of the UI if the texts are long, leading to bad results."""

        if not isinstance(disable, bool) or not isinstance(show_both, bool):
            raise ValueError("disable and show_both must be booleans.")
        
        if disable and show_both:
            raise ValueError("You can't disable the translation and show both at the same time.")
        
        if show_both:
            self._settings.translation_behaviour(TranslationBehaviour.BOTH)
            return self
        
        if disable:
            self._settings.translation_behaviour(TranslationBehaviour.ONLY_ORIGINAL)

        else:
            self._settings.translation_behaviour(TranslationBehaviour.ONLY_TRANSLATED)

        return self

    def run(self, submit: bool = True, disable_link: bool = False) -> 'RapidataOrder':
        """Run the free text order.
        
        Args:
            submit (bool): Whether to submit the order. Defaults to True. \
                Set this to False if you first want to see the order on your dashboard before running it.
            disable_link (bool): Whether to disable the printing of the link to the order. Defaults to False.
            
        Returns:
            RapidataOrder: The created free text order."""
        
        if MAX_TIME_IN_SECONDS_FOR_ONE_SESSION//self._time_effort < 1:
            raise ValueError(f"The Labelers only have {MAX_TIME_IN_SECONDS_FOR_ONE_SESSION} seconds to do the task. \
                             Your taks is too complex. Try to break it down into simpler tasks.")

        selection: list[Selection] = [LabelingSelection(amount=MAX_TIME_IN_SECONDS_FOR_ONE_SESSION//self._time_effort)]

        order = (self._order_builder
            .workflow(
                FreeTextWorkflow(
                    question=self._question
                )
            )
            .referee(self._referee)
            .media(self._media_assets)
            .selections(selection)
            .settings(self._settings)
            .filters(self._filters)
            .create(submit=submit, disable_link=disable_link))

        return order 


class FreeTextMediaBuilder:
    def __init__(self, name: str, question: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._question = question
        self._media_assets: list[BaseAsset] = []
        self._time_effort = 20

    def media(self, media_paths: list[str], time_effort: int = 20) -> FreeTextOrderBuilder:
        """Set the media assets for the free text order by providing the local paths to the files or a link.

        Args:
            media_paths (list[str]): Either a local file path or a link.
            time_effort (int): Estimated time in seconds to solve one free text task for the first time. Defaults to 20.
            
        Returns:
            FreeTextOrderBuilder: The free text order builder instance.
        
        Raises:
            ValueError: If the media paths are not a list of strings."""
        
        if not isinstance(media_paths, list) or not all(isinstance(path, str) for path in media_paths):
            raise ValueError("Media paths must be a list of strings, the strings being file paths or image links.")
        
        invalid_paths: list[str] = []
        for path in media_paths:
            try:
                self._media_assets.append(MediaAsset(path))
            except FileNotFoundError:
                invalid_paths.append(path)

        if invalid_paths:
            raise FileNotFoundError(f"Could not find the following files: {invalid_paths}")
        
        self._time_effort = time_effort
        return self._build()
    
    def text(self, texts: list[str], time_effort: int = 20) -> FreeTextOrderBuilder:
        """Set the text assets for the free text order by.

        Args:
            texts (list[str]): The texts to be shown.
            time_effort (int): Estimated time in seconds to solve one free text task for the first time. Defaults to 20.
            
        Returns:
            FreeTextOrderBuilder: The free text order builder instance."""
        for text in texts:
            self._media_assets.append(TextAsset(text))
        self._time_effort = time_effort
        return self._build()

    def _build(self) -> FreeTextOrderBuilder:
        if not self._media_assets:
            raise ValueError("Please provide either a text or an media to be shown with the question")
        return FreeTextOrderBuilder(self._name, self._question, self._media_assets, openapi_service=self._openapi_service, time_effort=self._time_effort)


class FreeTextQuestionBuilder:
    def __init__(self, name: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._question = None

    def question(self, question: str) -> FreeTextMediaBuilder:
        """Set the question for the free text order."""
        self._question = question
        return self._build()

    def _build(self) -> FreeTextMediaBuilder:
        if self._question is None:
            raise ValueError("Question is required")
        return FreeTextMediaBuilder(self._name, self._question, self._openapi_service)
