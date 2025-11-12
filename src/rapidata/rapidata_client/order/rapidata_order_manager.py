from typing import Literal, Optional, Sequence, get_args

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config.tracer import tracer
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.filter.rapidata_filters import RapidataFilters
from rapidata.rapidata_client.order._rapidata_order_builder import (
    RapidataOrderBuilder,
    StickyStateLiteral,
)
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.referee._early_stopping_referee import (
    EarlyStoppingReferee,
)
from rapidata.rapidata_client.referee._naive_referee import NaiveReferee
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.selection.rapidata_selections import RapidataSelections
from rapidata.rapidata_client.settings import RapidataSetting, RapidataSettings
from rapidata.rapidata_client.workflow import (
    ClassifyWorkflow,
    CompareWorkflow,
    DrawWorkflow,
    FreeTextWorkflow,
    LocateWorkflow,
    MultiRankingWorkflow,
    SelectWordsWorkflow,
    TimestampWorkflow,
    Workflow,
)
from rapidata.api_client.models.existing_asset_input import ExistingAssetInput
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.filter_operator import FilterOperator
from rapidata.api_client.models.multi_asset_input_assets_inner import (
    MultiAssetInputAssetsInner,
)
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.sort_criterion import SortCriterion
from rapidata.api_client.models.sort_direction import SortDirection
from rapidata.service.openapi_service import OpenAPIService


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
        self.__sticky_state: StickyStateLiteral | None = None
        self._asset_uploader = AssetUploader(openapi_service)
        logger.debug("RapidataOrderManager initialized")

    def _create_general_order(
        self,
        name: str,
        workflow: Workflow,
        datapoints: list[Datapoint],
        responses_per_datapoint: int = 10,
        validation_set_id: str | None = None,
        confidence_threshold: float | None = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
    ) -> RapidataOrder:
        if filters is None:
            filters = []
        if settings is None:
            settings = []
        if selections is None:
            selections = []

        if not confidence_threshold:
            referee = NaiveReferee(responses=responses_per_datapoint)
        else:
            referee = EarlyStoppingReferee(
                threshold=confidence_threshold,
                max_vote_count=responses_per_datapoint,
            )

        logger.debug(
            "Creating order with parameters: name %s, workflow %s, datapoints %s, responses_per_datapoint %s, validation_set_id %s, confidence_threshold %s, filters %s, settings %s, selections %s",
            name,
            workflow,
            datapoints,
            responses_per_datapoint,
            validation_set_id,
            confidence_threshold,
            filters,
            settings,
            selections,
        )

        order_builder = RapidataOrderBuilder(
            name=name, openapi_service=self.__openapi_service
        )

        if selections and validation_set_id:
            logger.warning(
                "Warning: Both selections and validation_set_id provided. Ignoring validation_set_id."
            )

        order = (
            order_builder._workflow(workflow)
            ._datapoints(datapoints=datapoints)
            ._referee(referee)
            ._filters(filters)
            ._selections(selections)
            ._settings(settings)
            ._validation_set_id(validation_set_id if not selections else None)
            ._priority(self.__priority)
            ._sticky_state(self.__sticky_state)
            ._create()
        )
        logger.debug("Order created: %s", order)
        return order

    def _set_priority(self, priority: int | None):
        if priority is not None and not isinstance(priority, int):
            raise TypeError("Priority must be an integer or None")

        if priority is not None and priority < 0:
            raise ValueError("Priority must be greater than 0 or None")

        self.__priority = priority

    def _set_sticky_state(self, sticky_state: StickyStateLiteral | None):
        sticky_state_valid_values = get_args(StickyStateLiteral)

        if sticky_state is not None and sticky_state not in sticky_state_valid_values:
            raise ValueError(
                f"Sticky state must be one of {sticky_state_valid_values} or None"
            )

        self.__sticky_state = sticky_state

    def create_classification_order(
        self,
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
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
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
        with tracer.start_as_current_span(
            "RapidataOrderManager.create_classification_order"
        ):
            if not isinstance(datapoints, list) or not all(
                isinstance(datapoint, str) for datapoint in datapoints
            ):
                raise ValueError("Datapoints must be a list of strings")

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_notes=private_notes,
                data_type=data_type,
            )
            return self._create_general_order(
                name=name,
                workflow=ClassifyWorkflow(
                    instruction=instruction, answer_options=answer_options
                ),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                validation_set_id=validation_set_id,
                confidence_threshold=confidence_threshold,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_compare_order(
        self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        a_b_names: list[str] | None = None,
        validation_set_id: str | None = None,
        confidence_threshold: float | None = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
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
            a_b_names (list[str], optional): Custom naming for the two opposing models defined by the index in the datapoints list. Defaults to None.\n
                If provided has to be a list of exactly two strings.
                example:
                ```python
                datapoints = [["path_to_image_A", "path_to_image_B"], ["path_to_text_A", "path_to_text_B"]]
                a_b_naming = ["Model A", "Model B"]
                ```
                The results will then correctly show "Model A" and "Model B".
                If not provided, the results will be shown as "A" and "B".
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
        with tracer.start_as_current_span("RapidataOrderManager.create_compare_order"):
            if any(not isinstance(datapoint, list) for datapoint in datapoints):
                raise ValueError("Each datapoint must be a list of 2 paths/texts")

            if any(len(set(datapoint)) != 2 for datapoint in datapoints):
                raise ValueError(
                    "Each datapoint must contain exactly two unique options"
                )

            if a_b_names is not None and len(a_b_names) != 2:
                raise ValueError(
                    "A_B_naming must be a list of exactly two strings or None"
                )

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_notes=private_notes,
                data_type=data_type,
            )
            return self._create_general_order(
                name=name,
                workflow=CompareWorkflow(instruction=instruction, a_b_names=a_b_names),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                validation_set_id=validation_set_id,
                confidence_threshold=confidence_threshold,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_ranking_order(
        self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        comparison_budget_per_ranking: int,
        responses_per_comparison: int = 1,
        data_type: Literal["media", "text"] = "media",
        random_comparisons_ratio: float = 0.5,
        contexts: Optional[list[str]] = None,
        media_contexts: Optional[list[str]] = None,
        validation_set_id: Optional[str] = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
    ) -> RapidataOrder:
        """
        Create a ranking order.

        With this order you can have a multiple lists of datapoints (image, text, video, audio) be ranked based on the instruction.
        Each list will be ranked independently, based on comparison matchups.

        Args:
            name (str): The name of the order.
            instruction (str): The instruction for the ranking. Will be shown with each matchup.
            datapoints (list[list[str]]): The outer list is determines the independent rankings, the inner list is the datapoints for each ranking.
            comparison_budget_per_ranking (int): The number of comparisons that will be collected per ranking (outer list of datapoints).
            responses_per_comparison (int, optional): The number of responses that will be collected per comparison. Defaults to 1.
            data_type (str, optional): The data type of the datapoints. Defaults to "media" (any form of image, video or audio). \n
                Other option: "text".
            random_comparisons_ratio (float, optional): The ratio of random comparisons to the total number of comparisons. Defaults to 0.5.
            contexts (list[str], optional): The list of contexts for the ranking. Defaults to None.\n
                If provided has to be the same length as the outer list of datapoints and will be shown in addition to the instruction. (Therefore will be different for each ranking)
                Will be matched up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the ranking i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as the outer list of datapoints and will be shown in addition to the instruction. (Therefore will be different for each ranking)
                Will be matched up with the datapoints using the list index.
            validation_set_id (str, optional): The ID of the validation set. Defaults to None.\n
                If provided, one validation task will be shown infront of the datapoints that will be labeled.
            filters (Sequence[RapidataFilter], optional): The list of filters for the ranking. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the ranking. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the ranking. Defaults to []. Decides in what order the tasks should be shown.
        """
        with tracer.start_as_current_span("RapidataOrderManager.create_ranking_order"):
            if contexts and len(contexts) != len(datapoints):
                raise ValueError(
                    "Number of contexts must match the number of sets that will be ranked"
                )
            if media_contexts and len(media_contexts) != len(datapoints):
                raise ValueError(
                    "Number of media contexts must match the number of sets that will be ranked"
                )
            if not isinstance(datapoints, list) or not all(
                isinstance(dp, list) for dp in datapoints
            ):
                raise ValueError(
                    "Datapoints must be a list of lists. Outer list is the independent rankings, inner list is the datapoints for each ranking."
                )
            if not all(len(set(dp)) == len(dp) for dp in datapoints):
                raise ValueError("Each inner list must contain unique datapoints.")

            if not all(len(inner_list) >= 2 for inner_list in datapoints):
                raise ValueError(
                    "Each ranking must contain at least two unique datapoints."
                )

            datapoints_instances = []
            for i, datapoint in enumerate(datapoints):
                for d in datapoint:
                    datapoints_instances.append(
                        Datapoint(
                            asset=d,
                            data_type=data_type,
                            context=contexts[i] if contexts else None,
                            media_context=media_contexts[i] if media_contexts else None,
                            group=str(i),
                        )
                    )

            contexts_dict = (
                {str(i): context for i, context in enumerate(contexts)}
                if contexts
                else None
            )

            media_contexts_dict = (
                {
                    str(i): MultiAssetInputAssetsInner(
                        actual_instance=ExistingAssetInput(
                            _t="ExistingAssetInput",
                            name=self._asset_uploader.upload_asset(media_context),
                        ),
                    )
                    for i, media_context in enumerate(media_contexts)
                }
                if media_contexts
                else None
            )

            return self._create_general_order(
                name=name,
                workflow=MultiRankingWorkflow(
                    instruction=instruction,
                    comparison_budget_per_ranking=comparison_budget_per_ranking,
                    random_comparisons_ratio=random_comparisons_ratio,
                    contexts=contexts_dict,
                    media_contexts=media_contexts_dict,
                ),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_comparison,
                validation_set_id=validation_set_id,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_free_text_order(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
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
            contexts (list[str], optional): The list of contexts for the free text. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the free text i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            filters (Sequence[RapidataFilter], optional): The list of filters for the free text. Defaults to []. Decides who the tasks should be shown to.
            settings (Sequence[RapidataSetting], optional): The list of settings for the free text. Defaults to []. Decides how the tasks should be shown.
            selections (Sequence[RapidataSelection], optional): The list of selections for the free text. Defaults to []. Decides in what order the tasks should be shown.
            private_notes (list[str], optional): The list of private notes for the free text. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span(
            "RapidataOrderManager.create_free_text_order"
        ):
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_notes=private_notes,
                data_type=data_type,
            )
            return self._create_general_order(
                name=name,
                workflow=FreeTextWorkflow(instruction=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_select_words_order(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        sentences: list[str],
        responses_per_datapoint: int = 10,
        validation_set_id: str | None = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
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
        with tracer.start_as_current_span(
            "RapidataOrderManager.create_select_words_order"
        ):
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                sentences=sentences,
                private_notes=private_notes,
            )
            return self._create_general_order(
                name=name,
                workflow=SelectWordsWorkflow(
                    instruction=instruction,
                ),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                validation_set_id=validation_set_id,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_locate_order(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        validation_set_id: str | None = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
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
        with tracer.start_as_current_span("RapidataOrderManager.create_locate_order"):
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_notes=private_notes,
            )
            return self._create_general_order(
                name=name,
                workflow=LocateWorkflow(target=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                validation_set_id=validation_set_id,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_draw_order(
        self,
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
        with tracer.start_as_current_span("RapidataOrderManager.create_draw_order"):
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_notes=private_notes,
            )
            return self._create_general_order(
                name=name,
                workflow=DrawWorkflow(target=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                validation_set_id=validation_set_id,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def create_timestamp_order(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        validation_set_id: str | None = None,
        filters: Sequence[RapidataFilter] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        selections: Sequence[RapidataSelection] | None = None,
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

        with tracer.start_as_current_span(
            "RapidataOrderManager.create_timestamp_order"
        ):
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_notes=private_notes,
            )
            return self._create_general_order(
                name=name,
                workflow=TimestampWorkflow(instruction=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                validation_set_id=validation_set_id,
                filters=filters,
                selections=selections,
                settings=settings,
            )

    def get_order_by_id(self, order_id: str) -> RapidataOrder:
        """Get an order by ID.

        Args:
            order_id (str): The ID of the order.

        Returns:
            RapidataOrder: The Order instance.
        """
        with tracer.start_as_current_span("RapidataOrderManager.get_order_by_id"):
            order = self.__openapi_service.order_api.order_order_id_get(order_id)

            return RapidataOrder(
                order_id=order_id,
                name=order.order_name,
                openapi_service=self.__openapi_service,
            )

    def find_orders(self, name: str = "", amount: int = 10) -> list[RapidataOrder]:
        """Find your recent orders given criteria. If nothing is provided, it will return the most recent order.

        Args:
            name (str, optional): The name of the order - matching order will contain the name. Defaults to "" for any order.
            amount (int, optional): The amount of orders to return. Defaults to 10.

        Returns:
            list[RapidataOrder]: A list of RapidataOrder instances.
        """
        with tracer.start_as_current_span("RapidataOrderManager.find_orders"):
            order_page_result = self.__openapi_service.order_api.orders_get(
                QueryModel(
                    page=PageInfo(index=1, size=amount),
                    filter=RootFilter(
                        filters=[
                            Filter(
                                field="OrderName",
                                operator=FilterOperator.CONTAINS,
                                value=name,
                            )
                        ]
                    ),
                    sortCriteria=[
                        SortCriterion(
                            direction=SortDirection.DESC, propertyName="OrderDate"
                        )
                    ],
                )
            )

            orders = [
                self.get_order_by_id(order.id) for order in order_page_result.items
            ]
            return orders

    def __str__(self) -> str:
        return "RapidataOrderManager"

    def __repr__(self) -> str:
        return self.__str__()
