from rapidata.constants import MAX_TIME_IN_SECONDS_FOR_ONE_SESSION
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.metadata import Metadata, PromptMetadata
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.referee.early_stopping_referee import EarlyStoppingReferee
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.workflow.classify_workflow import ClassifyWorkflow
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, BaseAsset
from rapidata.rapidata_client.filter import Filter, CountryFilter, LanguageFilter
from rapidata.rapidata_client.settings import Settings, TranslationBehaviour
from deprecated import deprecated
from typing import Sequence

class ClassificationOrderBuilder:
    def __init__(self, 
                 name: str, 
                 question: str, 
                 options: list[str], 
                 media_assets: list[BaseAsset], 
                 openapi_service: OpenAPIService, 
                 time_effort: int):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._question = question
        self._options = options
        self._media_assets = media_assets
        self._responses_required = 10
        self._probability_threshold = None
        self._metadata = None
        self._validation_set_id = None
        self._filters: list[Filter] = []
        self._settings = Settings()
        self._time_effort = time_effort

    def prompts(self, prompts: list[str]) -> 'ClassificationOrderBuilder':
        """Set the prompts for the classification order. Has to be the same lenght as the media paths."""
        if len(prompts) != len(self._media_assets):
            raise ValueError("The number of prompts must be the same as the number of media paths")
        
        if self._metadata is not None:
            print("Warning: Metadata will be overwritten by prompts")

        self._metadata = [PromptMetadata(prompt) for prompt in prompts]
        return self

    @deprecated("Use prompts instead")
    def metadata(self, metadata: Sequence[Metadata]) -> 'ClassificationOrderBuilder':
        """Set the metadata for the classification order. Has to be the same lenght as the media paths."""
        self._metadata = metadata
        return self

    def responses(self, responses_required: int) -> 'ClassificationOrderBuilder':
        """Set the number of responses required per datapoint for the classification order. Will default to 10."""
        self._responses_required = responses_required
        return self

    def probability_threshold(self, probability_threshold: float) -> 'ClassificationOrderBuilder':
        """Set the probability threshold for early stopping."""
        self._probability_threshold = probability_threshold
        return self

    def validation_set(self, validation_set_id: str) -> 'ClassificationOrderBuilder':
        """Set the validation set for the classification order."""
        self._validation_set_id = validation_set_id
        return self
    
    def countries(self, country_codes: list[str]) -> 'ClassificationOrderBuilder':
        """Set the countries where order will be shown as country codes."""
        self._filters.append(CountryFilter(country_codes))
        return self
    
    def languages(self, language_codes: list[str]) -> 'ClassificationOrderBuilder':
        """Set the languages where order will be shown as language codes."""
        self._filters.append(LanguageFilter(language_codes))
        return self
    
    def translation(self, disable: bool = False, show_both: bool = False) -> 'ClassificationOrderBuilder':
        """Disable the translation of the order.
        Only the question and the options will be translated.
        
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

    @deprecated("Use .run instead.")
    def create(self, submit: bool = True, max_upload_workers: int = 10) -> 'RapidataOrder':
        """Create the classification order."""
        return self.run(submit=submit, disable_link=False)

    def run(self, submit: bool = True, disable_link: bool = False) -> 'RapidataOrder':
        """Run the classification order.
        
        Args:
            submit (bool): Whether to submit the order. Defaults to True. \
                Set this to False if you first want to see the order on your dashboard before running it.
            disable_link (bool): Whether to disable the printing of the link to the order. Defaults to False.
            
        Returns:
            RapidataOrder: The created classification order."""
                
        if self._probability_threshold and self._responses_required:
            referee = EarlyStoppingReferee(
                max_vote_count=self._responses_required,
                threshold=self._probability_threshold
            )

        else:
            referee = NaiveReferee(responses=self._responses_required)
        
        if (self._validation_set_id and MAX_TIME_IN_SECONDS_FOR_ONE_SESSION//self._time_effort - 1 < 1) or (MAX_TIME_IN_SECONDS_FOR_ONE_SESSION//self._time_effort < 1):
            raise ValueError(f"The Labelers only have {MAX_TIME_IN_SECONDS_FOR_ONE_SESSION} seconds to do the task. \
                             Your taks is too complex. Try to break it down into simpler tasks.\
                             {'Alternatively remove the validation task' if self._validation_set_id else ''}")

        selection: list[Selection] = ([ValidationSelection(amount=1, validation_set_id=self._validation_set_id), 
                                       LabelingSelection(amount=MAX_TIME_IN_SECONDS_FOR_ONE_SESSION//self._time_effort - 1)] 
                     if self._validation_set_id 
                     else [LabelingSelection(amount=MAX_TIME_IN_SECONDS_FOR_ONE_SESSION//self._time_effort)])

        order = (self._order_builder
            .workflow(
                ClassifyWorkflow(
                    question=self._question,
                    options=self._options
                )
            )
            .referee(referee)
            .media(self._media_assets, metadata=self._metadata)
            .selections(selection)
            .create(submit=submit, disable_link=disable_link))

        return order 


class ClassificationMediaBuilder:
    def __init__(self, name: str, question: str, options: list[str], openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._question = question
        self._options = options
        self._media_assets: list[BaseAsset] = []
        self._time_effort = 8

    def media(self, media_paths: list[str], time_effort: int = 8) -> ClassificationOrderBuilder:
        """Set the media assets for the classification order by providing the local paths to the files or a link.

        Args:
            media_paths (list[str]): Either a local file path or a link.
            time_effort (int): Estimated time in seconds to solve one classification task for the first time. Defaults to 8.
            
        Returns:
            ClassificationOrderBuilder: The classification order builder instance.
        
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
    
    def text(self, texts: list[str], time_effort: int = 10) -> ClassificationOrderBuilder:
        """Set the text assets for the classification order by providing the text to be classified.

        Args:
            texts (list[str]): The texts to be classified.
            time_effort (int): Estimated time in seconds to solve one classification task for the first time. Defaults to 10.
            
        Returns:
            ClassificationOrderBuilder: The classification order builder instance."""
        for text in texts:
            self._media_assets.append(TextAsset(text))
        self._time_effort = time_effort
        return self._build()

    def _build(self) -> ClassificationOrderBuilder:
        if not self._media_assets:
            raise ValueError("Please provide either a text or an media to classify")
        return ClassificationOrderBuilder(self._name, self._question, self._options, self._media_assets, openapi_service=self._openapi_service, time_effort=self._time_effort)


class ClassificationOptionsBuilder:
    def __init__(self, name: str, question: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._question = question
        self._options = None

    def options(self, options: list[str]) -> ClassificationMediaBuilder:
        """Set the answer options for the classification order."""
        self._options = options
        return self._build()

    def _build(self) -> ClassificationMediaBuilder:
        if self._options is None:
            raise ValueError("Options are required")
        return ClassificationMediaBuilder(self._name, self._question, self._options, self._openapi_service)


class ClassificationQuestionBuilder:
    def __init__(self, name: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._question = None

    def question(self, question: str) -> ClassificationOptionsBuilder:
        """Set the question for the classification order."""
        self._question = question
        return self._build()

    def _build(self) -> ClassificationOptionsBuilder:
        if self._question is None:
            raise ValueError("Question is required")
        return ClassificationOptionsBuilder(self._name, self._question, self._openapi_service)
