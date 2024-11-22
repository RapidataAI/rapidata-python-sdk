from rapidata.constants import MAX_TIME_IN_SECONDS_FOR_ONE_SESSION
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.metadata import Metadata, PromptMetadata
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.workflow.compare_workflow import CompareWorkflow
from rapidata.rapidata_client.referee import NaiveReferee, EarlyStoppingReferee
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.assets import MultiAsset, MediaAsset, TextAsset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.filter import CountryFilter, Filter, LanguageFilter
from rapidata.rapidata_client.settings import Settings, TranslationBehaviour
from deprecated import deprecated
from typing import Sequence

class CompareOrderBuilder:
    def __init__(self, name:str, criteria: str, media_assets: list[MultiAsset], openapi_service: OpenAPIService, time_effort: int):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._name = name
        self._criteria = criteria
        self._media_assets = media_assets
        self._responses_required = 10
        self._metadata = None
        self._validation_set_id = None
        self._probability_threshold = None
        self._filters: list[Filter] = []
        self._settings = Settings()
        self._time_effort = time_effort

    def responses(self, responses_required: int) -> 'CompareOrderBuilder':
        """Set the number of resoonses required per matchup/pairing for the comparison order. Will default to 10."""
        self._responses_required = responses_required
        return self
    
    def prompts(self, prompts: list[str]) -> 'CompareOrderBuilder':
        """Set the prompts for the comparison order. Has to be the same shape as the media paths."""
        if len(prompts) != len(self._media_assets):
            raise ValueError("The number of prompts must match the number of media paths.")
        
        if self._metadata is not None:
            print("Warning: Metadata will be overwritten by prompts.")

        self._metadata = [PromptMetadata(prompt=prompt) for prompt in prompts]
        return self
    
    deprecated("Use prompts instead.")
    def metadata(self, metadata: Sequence[Metadata]) -> 'CompareOrderBuilder':
        """Set the metadata for the comparison order. Has to be the same shape as the media paths."""
        if len(metadata) != len(self._media_assets):
            raise ValueError("The number of metadata must match the number of media paths or image links.")
        
        if self._metadata is not None:
            print("Warning: Metadata will be overwritten by prompts.")

        self._metadata = metadata
        return self
    
    def validation_set(self, validation_set_id: str) -> 'CompareOrderBuilder':
        """Set the validation set for the comparison order."""
        self._validation_set_id = validation_set_id
        return self
    
    def probability_threshold(self, probability_threshold: float) -> 'CompareOrderBuilder':
        """Set the probability threshold for early stopping."""
        self._probability_threshold = probability_threshold
        return self
    
    def countries(self, country_codes: list[str]) -> 'CompareOrderBuilder':
        """Set the countries where order will be shown as country codes."""
        self._filters.append(CountryFilter(country_codes))
        return self
    
    def languages(self, language_codes: list[str]) -> 'CompareOrderBuilder':
        """Set the languages where order will be shown as language codes."""
        self._filters.append(LanguageFilter(language_codes))
        return self
    
    def translation(self, disable: bool = False, show_both: bool = False) -> 'CompareOrderBuilder':
        """Disable the translation of the order.
        Only the criteria will be translated.
        
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
    
    def run(self, submit: bool = True, disable_link: bool = False) -> RapidataOrder:
        """Run the compare order.
        
        Args:
            submit (bool): Whether to submit the order. Defaults to True. \
                Set this to False if you first want to see the order on your dashboard before running it.
            disable_link (bool): Whether to disable the printing of the link to the order. Defaults to False.
            
        Returns:
            RapidataOrder: The created compare order."""
        
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
                CompareWorkflow(
                    criteria=self._criteria
                )
            )
            .referee(referee)
            .media(self._media_assets, metadata=self._metadata)
            .selections(selection)
            .filters(self._filters)
            .create(submit=submit, disable_link=disable_link))
        
        return order

class CompareMediaBuilder:
    def __init__(self, name: str, criteria: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._criteria = criteria
        self._media_assets = []
        self._time_effort = 8

    def media(self, media_paths: list[list[str]], time_effort = 8) -> CompareOrderBuilder:
        """Set the media assets for the comparison order by providing the local paths to the files or a link.
        
        Args:
            media_paths (list[list[str]]): A list of lists of file paths. Each inner list is a pair of file paths that will be shown together in a matchup.
            time_effort (int): Estimated time in seconds to solve one comparison task for the first time. Defaults to 8.
            
        Returns:
            CompareOrderBuilder: The compare order builder instance.
            
        Raises:
            ValueError: If the media paths are not a list of lists of strings."""
        
        if not isinstance(media_paths, list) \
                or not all([isinstance(matchup_paths, list) for matchup_paths in media_paths]) \
                or not all([isinstance(path, str) for matchup_paths in media_paths for path in matchup_paths]):
            raise ValueError("Media paths must be a list of lists. \
                             \nThe inner list is a pair of file paths that will be shown together in a matchup.")
        
        invalid_paths = []
        for matchup_idx, matchup_paths in enumerate(media_paths):
            matchup_assets = []
            for path in matchup_paths:
                try:
                    matchup_assets.append(MediaAsset(path=path))
                except FileNotFoundError:
                    invalid_paths.append((matchup_idx, path))
            
            if not invalid_paths:
                self._media_assets.append(MultiAsset(matchup_assets))
                
        if invalid_paths:
            error_msg = "Could not find the following files:\n"
            for matchup_idx, path in invalid_paths:
                error_msg += f"  Matchup {matchup_idx + 1}: {path}\n"
            raise FileNotFoundError(error_msg.rstrip())
        
        self._time_effort = time_effort
        return self._build()
    
    def text(self, text_matchups: list[list[str]], time_effort = 10) -> CompareOrderBuilder:
        """Set the text assets for the comparison order by providing the texts.
        
        Args:
            text_matchups (list[list[str]]): A list of lists of texts. Each inner list is a pair of texts that will be shown together in a matchup.
            time_effort (int): Estimated time in seconds to solve one comparison task for the first time. Defaults to 10.
            
        Returns:
            CompareOrderBuilder: The compare order builder instance.
                
        Raises:
            ValueError: If the media paths are not a list of lists of strings."""
        if not isinstance(text_matchups, list) \
                or not all([isinstance(matchup_paths, list) for matchup_paths in text_matchups]) \
                or not all([isinstance(path, str) for matchup_paths in text_matchups for path in matchup_paths]):
            raise ValueError("Media paths must be a list of lists. \
                             \nThe inner list is a pair of file paths that will be shown together in a matchup.")
        
        for matchup_texts in text_matchups:
            matchup_assets = []
            for text in matchup_texts:
                matchup_assets.append(TextAsset(text=text))
            self._media_assets.append(MultiAsset(matchup_assets))

        self._time_effort = time_effort
        return self._build()
    
    def _build(self) -> CompareOrderBuilder:
        if not self._media_assets:
            raise ValueError("Media paths are required")
        return CompareOrderBuilder(self._name, self._criteria, self._media_assets, self._openapi_service, time_effort=self._time_effort)

class CompareCriteriaBuilder:
    def __init__(self, name: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._criteria = None

    def criteria(self, criteria: str) -> CompareMediaBuilder:
        """Set the criteria how the images should be compared."""
        self._criteria = criteria
        return self._build()
    
    def _build(self) -> CompareMediaBuilder:
        if self._criteria is None:
            raise ValueError("Criteria are required")
        return CompareMediaBuilder(self._name, self._criteria, self._openapi_service)

