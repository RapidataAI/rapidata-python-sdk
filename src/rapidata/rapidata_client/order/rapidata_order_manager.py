from typing import Sequence
from urllib3._collections import HTTPHeaderDict

from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.order._rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.metadata import PromptMetadata, SelectWordsMetadata
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.referee._early_stopping_referee import EarlyStoppingReferee
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.rapidata_client.workflow import (
    Workflow,
    ClassifyWorkflow,
    CompareWorkflow,
    FreeTextWorkflow,
    SelectWordsWorkflow,
    LocateWorkflow,
    DrawWorkflow,
    TimestampWorkflow)
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.filter.rapidata_filters import RapidataFilters
from rapidata.rapidata_client.settings import RapidataSettings, RapidataSetting
from rapidata.rapidata_client.selection.rapidata_selections import RapidataSelections

from rapidata.api_client.exceptions import BadRequestException
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion


class RapidataOrderManager:
    """
    Handels everything regarding the orders from creation to retrieval.
    
    Attributes:
        filters (RapidataFilters): The RapidataFilters instance.
        settings (RapidataSettings): The RapidataSettings instance.
        selections (RapidataSelections): The RapidataSelections instance."""

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self.filters = RapidataFilters
        self.settings = RapidataSettings
        self.selections = RapidataSelections
        self.__priority = 50

    def __get_selections(self, validation_set_id: str | None, labeling_amount=3) -> Sequence[RapidataSelection]:
        if validation_set_id:
            return [ValidationSelection(validation_set_id=validation_set_id), LabelingSelection(amount=labeling_amount-1)]
        return [LabelingSelection(amount=labeling_amount)]
    
    def __create_general_order(self,
            name: str,
            workflow: Workflow,
            assets: list[MediaAsset] | list[TextAsset] | list[MultiAsset],
            data_type: str = RapidataDataTypes.MEDIA,
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            confidence_threshold: float | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            sentences: list[str] | None = None,
            selections: Sequence[RapidataSelection] | None = None,
            default_labeling_amount: int = 3
        ) -> RapidataOrder:
        
        if contexts and len(contexts) != len(assets):
            raise ValueError("Number of contexts must match number of datapoints")
        
        if sentences and len(sentences) != len(assets):
            raise ValueError("Number of sentences must match number of datapoints")
        
        if sentences and contexts:
            raise ValueError("You can only use contexts or sentences, not both")
        
        if contexts and data_type == RapidataDataTypes.TEXT:
            print("Warning: Contexts are not supported for text data type. Ignoring contexts.")

        if not confidence_threshold:
            referee = NaiveReferee(responses=responses_per_datapoint)
        else:
            referee = EarlyStoppingReferee(
                threshold=confidence_threshold,
                max_vote_count=responses_per_datapoint,
            )

        order_builder = RapidataOrderBuilder(name=name, openapi_service=self._openapi_service)

        if selections and validation_set_id:
            print("Warning: You provided both selections and validation_set_id. Ignoring validation_set_id.")
        
        if selections is None:
            selections = self.__get_selections(validation_set_id, labeling_amount=default_labeling_amount)

        prompts_metadata = [PromptMetadata(prompt=prompt) for prompt in contexts] if contexts else None
        sentence_metadata = [SelectWordsMetadata(select_words=sentence) for sentence in sentences] if sentences else None

        metadata = prompts_metadata or sentence_metadata or None

        order = (order_builder
                 ._workflow(workflow)
                 ._media(
                     asset=assets,
                     metadata=metadata
                     )
                 ._referee(referee)
                 ._filters(filters)
                 ._selections(selections) 
                 ._settings(settings)
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
            data_type: str = RapidataDataTypes.MEDIA,
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            confidence_threshold: float | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a classification order.
        
        Args:
            name (str): The name of the order. (Will not be shown to the labeler)
            instruction (str): The instruction for how the data should be classified.
            answer_options (list[str]): The list of options for the classification.
            datapoints (list[str]): The list of datapoints for the classification - each datapoint will be labeled.
            data_type (str, optional): The data type of the datapoints. Defaults to RapidataDataTypes.MEDIA. \n
                Other option: RapidataDataTypes.TEXT ("text").
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the classification. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and options. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            confidence_threshold (float, optional): The probability threshold for the classification. Defaults to None.\n
                If provided, the classification datapoint will stop after the threshold is reached or at the number of responses, whatever happens first.
            filters (Sequence[RapidataFilter], optional): The list of filters for the classification. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the classification. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the classification. Defaults to None. Decides in what order the tasks should be shown.
        """
        
        if data_type == RapidataDataTypes.MEDIA:
            assets = [MediaAsset(path=path) for path in datapoints]
        elif data_type == RapidataDataTypes.TEXT:
            assets = [TextAsset(text=text) for text in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of {RapidataDataTypes._possible_values()}")
        
        return self.__create_general_order(
            name=name,
            workflow=ClassifyWorkflow(
                instruction=instruction,
                answer_options=answer_options
            ),
            assets=assets,
            data_type=data_type,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            validation_set_id=validation_set_id,
            confidence_threshold=confidence_threshold,
            filters=filters,
            selections=selections,
            settings=settings
        )
    
    def create_compare_order(self,
            name: str,
            instruction: str,
            datapoints: list[list[str]],
            data_type: str = RapidataDataTypes.MEDIA,
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            confidence_threshold: float | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a compare order.

        Args:
            name (str): The name of the order. (Will not be shown to the labeler)
            instruction (str): The instruction for the comparison. Will be shown along side each datapoint.
            datapoints (list[list[str]]): Outher list is the datapoints, inner list is the options for the comparison - each datapoint will be labeled.
            data_type (str, optional): The data type of the datapoints. Defaults to RapidataDataTypes.MEDIA. \n
                Other option: RapidataDataTypes.TEXT ("text").
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            confidence_threshold (float, optional): The probability threshold for the comparison. Defaults to None.\n
                If provided, the comparison datapoint will stop after the threshold is reached or at the number of responses, whatever happens first.
            filters (Sequence[RapidataFilter], optional): The list of filters for the comparison. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the comparison. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the comparison. Defaults to None. Decides in what order the tasks should be shown.
        """

        if data_type == RapidataDataTypes.MEDIA:
            assets = [MultiAsset([MediaAsset(path=path) for path in datapoint]) for datapoint in datapoints]
        elif data_type == RapidataDataTypes.TEXT:
            assets = [MultiAsset([TextAsset(text=text) for text in datapoint]) for datapoint in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of {RapidataDataTypes._possible_values()}")
        
        return self.__create_general_order(
            name=name,
            workflow=CompareWorkflow(
                instruction=instruction
            ),
            assets=assets,
            data_type=data_type,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            validation_set_id=validation_set_id,
            confidence_threshold=confidence_threshold,
            filters=filters,
            selections=selections,
            settings=settings
        )
    
    def create_free_text_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            data_type: str = RapidataDataTypes.MEDIA,
            responses_per_datapoint: int = 10,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a free text order.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction to answer with free text. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the free text - each datapoint will be labeled.
            data_type (str, optional): The data type of the datapoints. Defaults to RapidataDataTypes.MEDIA. \n
                Other option: RapidataDataTypes.TEXT ("text").
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            filters (Sequence[RapidataFilter], optional): The list of filters for the free text. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the free text. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the free text. Defaults to None. Decides in what order the tasks should be shown.
        """

        if data_type == RapidataDataTypes.MEDIA:
            assets = [MediaAsset(path=path) for path in datapoints]
        elif data_type == RapidataDataTypes.TEXT:
            assets = [TextAsset(text=text) for text in datapoints]
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of {RapidataDataTypes._possible_values()}")

        return self.__create_general_order(
            name=name,
            workflow=FreeTextWorkflow(
                instruction=instruction
            ),
            assets=assets,
            data_type=data_type,
            responses_per_datapoint=responses_per_datapoint,
            filters=filters,
            selections=selections,
            settings=settings,
            default_labeling_amount=1
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
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a select words order.

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
            selections (Sequence[RapidataSelection], optional): The list of selections for the select words. Defaults to None. Decides in what order the tasks should be shown.
        """

        assets = [MediaAsset(path=path) for path in datapoints]
        
        return self.__create_general_order(
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
            default_labeling_amount=2
        )
    
    def create_locate_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a locate order.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction what should be located. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the locate - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the locate. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the locate. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the locate. Defaults to None. Decides in what order the tasks should be shown.
        """

        assets = [MediaAsset(path=path) for path in datapoints]

        return self.__create_general_order(
            name=name,
            workflow=LocateWorkflow(target=instruction),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings
        )

    def create_draw_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a draw order.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction for how the lines should be drawn. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the draw lines - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the draw lines. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the draw lines. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the draw lines. Defaults to None. Decides in what order the tasks should be shown.
        """

        assets = [MediaAsset(path=path) for path in datapoints]

        return self.__create_general_order(
            name=name,
            workflow=DrawWorkflow(target=instruction),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings
        )
    
    def create_timestamp_order(self,
            name: str,
            instruction: str,
            datapoints: list[str],
            responses_per_datapoint: int = 10,
            contexts: list[str] | None = None,
            validation_set_id: str | None = None,
            filters: Sequence[RapidataFilter] = [],
            settings: Sequence[RapidataSetting] = [],
            selections: Sequence[RapidataSelection] | None = None,
        ) -> RapidataOrder:
        """Create a timestamp order.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction for the timestamp task. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the timestamp - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
            filters (Sequence[RapidataFilter], optional): The list of filters for the timestamp. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the timestamp. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the timestamp. Defaults to None. Decides in what order the tasks should be shown.
        """

        assets = [MediaAsset(path=path) for path in datapoints]

        for asset in assets:
            if not asset.get_duration():
                raise ValueError("The datapoints for this order must have a duration. (e.g. video or audio)")

        return self.__create_general_order(
            name=name,
            workflow=TimestampWorkflow(
                instruction=instruction
            ),
            assets=assets,
            responses_per_datapoint=responses_per_datapoint,
            contexts=contexts,
            validation_set_id=validation_set_id,
            filters=filters,
            selections=selections,
            settings=settings,
            default_labeling_amount=2
        )

    def get_order_by_id(self, order_id: str) -> RapidataOrder:
        """Get an order by ID.

        Args:
            order_id (str): The ID of the order.

        Returns:
            RapidataOrder: The Order instance.
        """

        try:
            order = self._openapi_service.order_api.order_get_by_id_get(order_id)
        except Exception:
            raise ValueError(f"Order with ID {order_id} not found.")

        return RapidataOrder(
            order_id=order_id, 
            name=order.order_name,
            openapi_service=self._openapi_service)

    def find_orders(self, name: str = "", amount: int = 1) -> list[RapidataOrder]:
        """Find your recent orders given criteria. If nothing is provided, it will return the most recent order.

        Args:
            name (str, optional): The name of the order - matching order will contain the name. Defaults to "" for any order.
            amount (int, optional): The amount of orders to return. Defaults to 1.

        Returns:
            list[RapidataOrder]: A list of RapidataOrder instances.
        """
        try:
            order_page_result = self._openapi_service.order_api.order_query_get(QueryModel(
                page=PageInfo(index=1, size=amount),
                filter=RootFilter(filters=[Filter(field="OrderName", operator="Contains", value=name)]),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="OrderDate")]
                ))

        except BadRequestException as e:
            raise ValueError(f"Error occured during request. \nError: {e.body} \nTraceid: {e.headers.get('X-Trace-Id') if isinstance(e.headers, HTTPHeaderDict) else 'Unknown'}")

        except Exception as e:
            raise ValueError(f"Unknown error occured: {e}")

        orders = [self.get_order_by_id(order.id) for order in order_page_result.items]
        return orders
