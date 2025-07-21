from typing import Sequence, Optional, Literal
from itertools import zip_longest

from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.order._rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.datapoints.metadata import PromptMetadata, SelectWordsMetadata, PrivateTextMetadata, MediaAssetMetadata, Metadata
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.referee._early_stopping_referee import EarlyStoppingReferee
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.workflow import (
    Workflow,
    ClassifyWorkflow,
    CompareWorkflow,
    FreeTextWorkflow,
    SelectWordsWorkflow,
    LocateWorkflow,
    DrawWorkflow,
    TimestampWorkflow,
    RankingWorkflow
)
from rapidata.rapidata_client.datapoints.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.datapoints.datapoint import Datapoint
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.filter.rapidata_filters import RapidataFilters
from rapidata.rapidata_client.settings import RapidataSettings, RapidataSetting
from rapidata.rapidata_client.selection.rapidata_selections import RapidataSelections
from rapidata.rapidata_client.logging import logger, RapidataOutputManager

from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion

from tqdm import tqdm


class RapidataOrderManager:
    """
    Handels everything regarding the orders from creation to retrieval.
    
    Attributes:
        filters (RapidataFilters): The RapidataFilters instance.
        settings (RapidataSettings): The RapidataSettings instance.
        selections (RapidataSelections): The RapidataSelections instance."""

    def __init__(self, openapi_service: OpenAPIService):
        self.__openapi_service = openapi_service
        self.filters = RapidataFilters
        self.settings = RapidataSettings
        self.selections = RapidataSelections
        self.__priority: int | None = None
        logger.debug("RapidataOrderManager initialized")
    
    def _create_general_order(self,
            name: str,
            workflow: Workflow,
            assets: list[MediaAsset] | list[TextAsset] | list[MultiAsset],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            media_contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            confidence_threshold: float | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            sentences: list[str] | None = None,
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:

        if not assets:
            raise ValueError("No datapoints provided")
        
        if contexts and len(contexts) != len(assets):
            raise ValueError("Number of contexts must match number of datapoints")
        
        if media_contexts and len(media_contexts) != len(assets):
            raise ValueError("Number of media contexts must match number of datapoints")
        
        if sentences and len(sentences) != len(assets):
            raise ValueError("Number of sentences must match number of datapoints")

        if private_notes and len(private_notes) != len(assets):
            raise ValueError("Number of private notes must match number of datapoints")
        
        if sentences and contexts:
            raise ValueError("You can only use contexts or sentences, not both")

        if not confidence_threshold:
            referee = NaiveReferee(responses=responses_per_datapoint)
        else:
            referee = EarlyStoppingReferee(
                threshold=confidence_threshold,
                max_vote_count=responses_per_datapoint,
            )

        order_builder = RapidataOrderBuilder(name=name, openapi_service=self.__openapi_service)

        if selections and validation_set_id:
            logger.warning("Warning: Both selections and validation_set_id provided. Ignoring validation_set_id.")

        prompts_metadata = [PromptMetadata(prompt=prompt) for prompt in contexts] if contexts else None
        sentence_metadata = [SelectWordsMetadata(select_words=sentence) for sentence in sentences] if sentences else None

        if prompts_metadata and sentence_metadata:
            raise ValueError("You can only use contexts or sentences, not both")
        
        asset_metadata: Sequence[Metadata] = [MediaAssetMetadata(url=context) for context in media_contexts] if media_contexts else []
        prompt_metadata: Sequence[Metadata] = prompts_metadata or sentence_metadata or []
        private_notes_metadata: Sequence[Metadata] = [PrivateTextMetadata(text=text) for text in private_notes] if private_notes else []

        multi_metadata = [[item for item in items if item is not None] 
                     for items in zip_longest(prompt_metadata, asset_metadata, private_notes_metadata)]

        order = (order_builder
                 ._workflow(workflow)
                 ._datapoints(
                     datapoints=[Datapoint(asset=asset, metadata=metadata) for asset, metadata in zip_longest(assets, multi_metadata)]
                     )
                 ._referee(referee)
                 ._filters(filters)
                 ._selections(selections) 
                 ._settings(settings)
                 ._validation_set_id(validation_set_id if not selections else None)
                 ._priority(self.__priority)
                 ._create()
                 )
        return order
    
    def _set_priority(self, priority: int):
        self.__priority = priority
        
    def create_classification_order(self,
            name: str,
            instruction: str,
            answer_options: list[str],
            datapoints: list[str],
            data_type: Literal["media", "text"] = "media",
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            media_contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            confidence_threshold: float | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a classification order.

        With this order you can have a datapoint (image, text, video, audio) be classified into one of the answer options.
        Each response will be exactly one of the answer options.

        Args:
            name (str): The name of the order. (Will not be shown to the labeler)
            instruction (str): The instruction for how the data should be classified.
            answer_options (list[str]): The list of options for the classification.
            datapoints (list[str]): The list of datapoints for the classification - each datapoint will be labeled.
            data_type (str, optional): The data type of the datapoints. Defaults to "media" (any form of image, video or audio). \n
                Other option: "text".
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the classification. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and options. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the classification i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and options. (Therefore will be different for each datapoint)
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            confidence_threshold (float, optional): The probability threshold for the classification. Defaults to None.\n
                If provided, the classification datapoint will stop after the threshold is reached or at the number of responses, whatever happens first.
            filters (Sequence[RapidataFilter], optional): The list of filters for the classification. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the classification. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the classification. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the classification. Defaults to None.
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        
        if data_type == "media":
            assets = [MediaAsset(path=path) for path in datapoints]
        elif data_type == "text":
            assets = [TextAsset(text=text) for text in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of 'media' or 'text'")
        
        return self._create_general_order(
            name=name,
            workflow=ClassifyWorkflow(
                instruction=instruction,
                answer_options=answer_options
            ),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            media_contexts=media_contexts,
            validation_set_id=validation_set_id,
            confidence_threshold=confidence_threshold,
            filters=filters,
            selections=selections,
            settings=settings,
            private_notes=private_notes
        )
    
    def create_compare_order(self,
            name: str,
            instruction: str,
            datapoints: list[list[str]],
            data_type: Literal["media", "text"] = "media",
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            media_contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            confidence_threshold: float | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a compare order.

        With this order you compare two datapoints (image, text, video, audio) and the annotators will choose one of the two based on the instruction.

        Args:
            name (str): The name of the order. (Will not be shown to the labeler)
            instruction (str): The instruction for the comparison. Will be shown along side each datapoint.
            datapoints (list[list[str]]): Outher list is the datapoints, inner list is the options for the comparison - each datapoint will be labeled.
            data_type (str, optional): The data type of the datapoints. Defaults to "media" (any form of image, video or audio). \n
                Other option: "text".
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts i.e. links to the images / videos for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            confidence_threshold (float, optional): The probability threshold for the comparison. Defaults to None.\n
                If provided, the comparison datapoint will stop after the threshold is reached or at the number of responses, whatever happens first.
            filters (Sequence[RapidataFilter], optional): The list of filters for the comparison. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the comparison. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the comparison. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """

        if any(type(datapoint) != list for datapoint in datapoints):
            raise ValueError("Each datapoint must be a list of 2 paths/texts")

        if any(len(datapoint) != 2 for datapoint in datapoints):
            raise ValueError("Each datapoint must contain exactly two options")

        if data_type == "media":
            assets = [MultiAsset([MediaAsset(path=path) for path in datapoint]) for datapoint in datapoints]
        elif data_type == "text":
            assets = [MultiAsset([TextAsset(text=text) for text in datapoint]) for datapoint in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of 'media' or 'text'")
        
        return self._create_general_order(
            name=name,
            workflow=CompareWorkflow(
                instruction=instruction
            ),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            media_contexts=media_contexts,
            validation_set_id=validation_set_id,
            confidence_threshold=confidence_threshold,
            filters=filters,
            selections=selections,
            settings=settings,
            private_notes=private_notes
        )

    def create_ranking_order(self,
                             name: str,
                             instruction: str,
                             datapoints: list[str],
                             total_comparison_budget: int,
                             responses_per_comparison: int = 1,
                             data_type: Literal["media", "text"] = "media",
                             random_comparisons_ratio: float = 0.5,
                             context: Optional[str] = None,
                             validation_set_id: Optional[str] = None,
                             filters: Sequence[RapidataFilter] = [],
                             settings: Sequence[RapidataSetting] = [],
                             selections: Sequence[RapidataSelection] = []
                             ) -> RapidataOrder:
        """
        Create a ranking order.

        With this order you can rank a list of datapoints (image, text, video, audio) based on the instruction.
        The annotators will be shown two datapoints at a time. The ranking happens in terms of an elo system based on the matchup results.

        Args:
            name (str): The name of the order.
            instruction (str): The question asked from People when They see two datapoints.
            datapoints (list[str]): A list of datapoints that will participate in the ranking.
            total_comparison_budget (int): The total number of (pairwise-)comparisons that can be made.
            responses_per_comparison (int, optional): The number of responses collected per comparison. Defaults to 1.
            data_type (str, optional): The data type of the datapoints. Defaults to "media" (any form of image, video or audio). \n
                Other option: "text".
            random_comparisons_ratio (float, optional): The fraction of random comparisons in the ranking process.
                The rest will focus on pairing similarly ranked datapoints. Defaults to 0.5 and can be left untouched.
            context (str, optional): The context for all the comparison. Defaults to None.\n
                If provided will be shown in addition to the instruction for all the matchups.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the order. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the order. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the order. Defaults to []. Decides in what order the tasks should be shown.
        """

        if data_type == "media":
            assets = [MediaAsset(path=path) for path in datapoints]
        elif data_type == "text":
            assets = [TextAsset(text=text) for text in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of 'media' or 'text'")

        return self._create_general_order(
            name=name,
            workflow=RankingWorkflow(
                criteria=instruction,
                total_comparison_budget=total_comparison_budget,
                random_comparisons_ratio=random_comparisons_ratio,
                context=context
            ),
            assets=assets,
            responses_per_datapoint=responses_per_comparison,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings,
        )

    def create_free_text_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            data_type: Literal["media", "text"] = "media",
            responses_per_datapoint: int = 10,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a free text order.

        With this order you can have a datapoint (image, text, video, audio) be labeled with free text.
        The annotators will be shown a datapoint and will be asked to answer a question with free text.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction to answer with free text. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the free text - each datapoint will be labeled.
            data_type (str, optional): The data type of the datapoints. Defaults to "media" (any form of image, video or audio). \n
                Other option: "text".
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            filters (Sequence[RapidataFilter], optional): The list of filters for the free text. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the free text. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the free text. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the free text. Defaults to None.\n
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """

        if data_type == "media":
            assets = [MediaAsset(path=path) for path in datapoints]
        elif data_type == "text":
            assets = [TextAsset(text=text) for text in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of 'media' or 'text'")

        return self._create_general_order(
            name=name,
            workflow=FreeTextWorkflow(
                instruction=instruction
            ),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            filters=filters,
            selections=selections,
            settings=settings,
            private_notes=private_notes
        )
    
    def create_select_words_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            sentences: list[str],
            responses_per_datapoint: int = 10,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a select words order.

        With this order you can have a datapoint (image, text, video, audio) be labeled with a list of words.
        The annotators will be shown a datapoint as well as a list of sentences split up by spaces.
        They will then select specific words based on the instruction.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction for how the words should be selected. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the select words - each datapoint will be labeled.
            sentences (list[str]): The list of sentences for the select words - Will be split up by spaces and shown along side each datapoint.\n
                Must be the same length as datapoints.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the select words. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the select words. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the select words. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the select words. Defaults to None.\n
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """

        assets = [MediaAsset(path=path) for path in datapoints]
        
        return self._create_general_order(
            name=name,
            workflow=SelectWordsWorkflow(
                instruction=instruction
            ),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings,
            sentences=sentences,
            private_notes=private_notes
        )
    
    def create_locate_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            media_contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a locate order.

        With this order you can have people locate specific objects in a datapoint (image, text, video, audio).
        The annotators will be shown a datapoint and will be asked to select locations based on the instruction.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction what should be located. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the locate - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the locate. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the locate i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the locate. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the locate. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the locate. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the locate. Defaults to None.\n
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """

        assets = [MediaAsset(path=path) for path in datapoints]

        return self._create_general_order(
            name=name,
            workflow=LocateWorkflow(target=instruction),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            media_contexts=media_contexts,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings,
            private_notes=private_notes
        )

    def create_draw_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            media_contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a draw order.

        With this order you can have people draw lines on a datapoint (image, text, video, audio).
        The annotators will be shown a datapoint and will be asked to draw lines based on the instruction.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction for how the lines should be drawn. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the draw lines - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the draw lines i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the draw lines. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the draw lines. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the draw lines. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the draw lines. Defaults to None.\n
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """

        assets = [MediaAsset(path=path) for path in datapoints]

        return self._create_general_order(
            name=name,
            workflow=DrawWorkflow(target=instruction),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            media_contexts=media_contexts,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings,
            private_notes=private_notes
        )
    
    def create_timestamp_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            media_contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] = [],
            private_notes: list[str] | None = None,
        ) -> RapidataOrder:
        """Create a timestamp order.

        Warning: 
            This order is currently not fully supported and may give unexpected results.

        With this order you can have people mark specific timestamps in a datapoint (video, audio).
        The annotators will be shown a datapoint and will be asked to select a timestamp based on the instruction.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction for the timestamp task. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the timestamp - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the timestamp i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the timestamp. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the timestamp. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the timestamp. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the timestamp. Defaults to None.\n
                If provided has to be the same length as datapoints.\n 
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """

        assets = [MediaAsset(path=path) for path in datapoints]

        for asset in tqdm(assets, desc="Downloading assets and checking duration", disable=RapidataOutputManager.silent_mode):
            if not asset.get_duration():
                raise ValueError("The datapoints for this order must have a duration. (e.g. video or audio)")

        return self._create_general_order(
            name=name,
            workflow=TimestampWorkflow(
                instruction=instruction
            ),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            media_contexts=media_contexts,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings,
            private_notes=private_notes
        )

    def get_order_by_id(self, order_id: str) -> RapidataOrder:
        """Get an order by ID.

        Args:
            order_id (str): The ID of the order.

        Returns:
            RapidataOrder: The Order instance.
        """
        
        order = self.__openapi_service.order_api.order_order_id_get(order_id)

        return RapidataOrder(
            order_id=order_id, 
            name=order.order_name,
            openapi_service=self.__openapi_service)

    def find_orders(self, name: str = "", amount: int = 10) -> list[RapidataOrder]:
        """Find your recent orders given criteria. If nothing is provided, it will return the most recent order.

        Args:
            name (str, optional): The name of the order - matching order will contain the name. Defaults to "" for any order.
            amount (int, optional): The amount of orders to return. Defaults to 10.

        Returns:
            list[RapidataOrder]: A list of RapidataOrder instances.
        """
        order_page_result = self.__openapi_service.order_api.orders_get(QueryModel(
            page=PageInfo(index=1, size=amount),
            filter=RootFilter(filters=[Filter(field="OrderName", operator="Contains", value=name)]),
            sortCriteria=[SortCriterion(direction="Desc", propertyName="OrderDate")]
            ))

        orders = [self.get_order_by_id(order.id) for order in order_page_result.items]
        return orders
