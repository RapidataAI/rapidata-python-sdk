from rapidata.constants import MAX_TIME_IN_SECONDS_FOR_ONE_SESSION
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.workflow import SelectWordsWorkflow
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset, BaseAsset
from rapidata.rapidata_client.filter import Filter, CountryFilter, LanguageFilter
from rapidata.rapidata_client.metadata import SelectWordsMetadata
from rapidata.rapidata_client.settings import Settings, TranslationBehaviour

class SelectWordsOrderBuilder:
    def __init__(self, 
                 name: str, 
                 instruction: str, 
                 media_assets: list[BaseAsset], 
                 texts: list[SelectWordsMetadata],
                 openapi_service: OpenAPIService, 
                 time_effort: int):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._instruction = instruction
        self._media_assets = media_assets
        self._texts = texts
        self._validation_set_id = None
        self._referee = NaiveReferee()
        self._settings = Settings()
        self._filters: list[Filter] = []
        self._time_effort = time_effort

    def responses(self, responses_required: int) -> 'SelectWordsOrderBuilder':
        """Set the number of responses required per datapoint for the order. Will default to 10."""
        self._referee = NaiveReferee(responses=responses_required)
        return self

    def validation_set(self, validation_set_id: str) -> 'SelectWordsOrderBuilder':
        """Set the validation set for the order."""
        self._validation_set_id = validation_set_id
        return self
    
    def countries(self, country_codes: list[str]) -> 'SelectWordsOrderBuilder':
        """Set the countries where order will be shown as country codes."""
        self._filters.append(CountryFilter(country_codes))
        return self
    
    def languages(self, language_codes: list[str]) -> 'SelectWordsOrderBuilder':
        """Set the languages where order will be shown as language codes."""
        self._filters.append(LanguageFilter(language_codes))
        return self
    
    def wait_for_video_to_finish(self, offset: int = 0) -> 'SelectWordsOrderBuilder':
        """Allows labeler to only answer once the video has finished playing.
        The offset gets added on top. Can be negative to allow answers before the video ends."""
        self._settings.play_video_until_the_end(offset)
        return self
    
    def translation(self, disable: bool = False, show_both: bool = False) -> 'SelectWordsOrderBuilder':
        """Disable the translation of the order.
        Only the instruction will be translated.
        
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
        """Run the order.
        
        Args:
            submit (bool): Whether to submit the order. Defaults to True. \
                Set this to False if you first want to see the order on your dashboard before running it.
            disable_link (bool): Whether to disable the printing of the link to the order. Defaults to False."""
        
        return self.submit(submit=submit, disable_link=disable_link)

    def submit(self, submit: bool = True, disable_link: bool = False) -> 'RapidataOrder':
        """Submit the order to be labeled.
        
        Args:
            submit (bool): Whether to submit the order. Defaults to True. \
                Set this to False if you first want to see the order on your dashboard before running it.
            disable_link (bool): Whether to disable the printing of the link to the order. Defaults to False."""
        
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
                SelectWordsWorkflow(
                    instruction=self._instruction
                )
            )
            .referee(self._referee)
            .media(self._media_assets, metadata=self._texts)
            .selections(selection)
            .settings(self._settings)
            .filters(self._filters)
            .create(submit=submit, disable_link=disable_link))

        return order 


class SelectWordsMediaBuilder:
    def __init__(self, name: str, instruction: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._instruction = instruction
        self._media_assets: list[BaseAsset] = []
        self._texts: list[SelectWordsMetadata] = []
        self._time_effort = 10

    def media(self, media_paths: list[str], texts: list[str], time_effort: int = 10) -> SelectWordsOrderBuilder:
        """Set the media assets for the order by providing the local paths to the audio / video files.

        Args:
            media_paths (list[str]): A local file path.
            texts (list[str]): The text will be split up by spaces and the labeler will be able to select the words.
            time_effort (int): Estimated time in seconds to solve one task for the first time. Defaults to 10."""
        
        if not isinstance(media_paths, list) or not all(isinstance(path, str) for path in media_paths):
            raise ValueError("Media paths must be a list of strings, the strings being file paths.")
        
        if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
            raise ValueError("texts must be a list of strings.")
        
        if not len(media_paths) == len(texts):
            raise ValueError("The number of media paths and texts must be the same.")

        invalid_paths: list[str] = []
        for path in media_paths:
            try:
                self._media_assets.append(MediaAsset(path))
            except FileNotFoundError:
                invalid_paths.append(path)

        if invalid_paths:
            raise FileNotFoundError(f"Could not find the following files: {invalid_paths}")
        
        self._texts = [SelectWordsMetadata(text) for text in texts]

        self._time_effort = time_effort
        return self._build()

    def _build(self) -> SelectWordsOrderBuilder:
        if not self._media_assets:
            raise ValueError("Please provide either a text or an media to be shown with the question")
        return SelectWordsOrderBuilder(self._name, 
                                         self._instruction, 
                                         self._media_assets, 
                                         self._texts, 
                                         openapi_service=self._openapi_service, 
                                         time_effort=self._time_effort)


class SelectWordsInstructionBuilder:
    def __init__(self, name: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._instruction = None

    def instruction(self, instruction: str) -> SelectWordsMediaBuilder:
        """Set the instruction for the order."""
        self._instruction = instruction
        return self._build()

    def _build(self) -> SelectWordsMediaBuilder:
        if self._instruction is None:
            raise ValueError("Instruction is required")
        return SelectWordsMediaBuilder(self._name, self._instruction, self._openapi_service)
