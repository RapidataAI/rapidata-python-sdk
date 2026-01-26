from __future__ import annotations

from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.settings import RapidataSetting
from rapidata.rapidata_client.job.job_definition import JobDefinition
from typing import Sequence, Literal, TYPE_CHECKING
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)

if TYPE_CHECKING:
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob


class JobManager:
    """
    A manager for job definitions.
    Used to create and retrieve job definitions.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

        self.__priority: int | None = None
        self._asset_uploader = AssetUploader(openapi_service)
        logger.debug("JobManager initialized")

    def _create_general_job_definition(
        self,
        name: str,
        workflow: Workflow,
        datapoints: list[Datapoint],
        responses_per_datapoint: int = 10,
        confidence_threshold: float | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> JobDefinition:
        if settings is None:
            settings = []

        if not confidence_threshold:
            from rapidata.rapidata_client.referee._naive_referee import NaiveReferee

            referee = NaiveReferee(responses=responses_per_datapoint)
        else:
            from rapidata.rapidata_client.referee._early_stopping_referee import (
                EarlyStoppingReferee,
            )

            referee = EarlyStoppingReferee(
                threshold=confidence_threshold,
                max_responses=responses_per_datapoint,
            )

        logger.debug(
            "Creating job with parameters: name %s, workflow %s, datapoints %s, responses_per_datapoint %s, confidence_threshold %s, settings %s",
            name,
            workflow,
            datapoints,
            responses_per_datapoint,
            confidence_threshold,
            settings,
        )
        from rapidata.api_client.models.create_dataset_endpoint_input import (
            CreateDatasetEndpointInput,
        )
        from rapidata.api_client.models.create_job_definition_endpoint_input import (
            CreateJobDefinitionEndpointInput,
        )

        dataset = self._openapi_service.dataset_api.dataset_post(
            create_dataset_endpoint_input=CreateDatasetEndpointInput(
                name=name + "_dataset"
            )
        )
        rapidata_dataset = RapidataDataset(dataset.dataset_id, self._openapi_service)

        with tracer.start_as_current_span("add_datapoints"):
            _, failed_uploads = rapidata_dataset.add_datapoints(datapoints)

        job_definition_response = self._openapi_service.job_api.job_definition_post(
            create_job_definition_endpoint_input=CreateJobDefinitionEndpointInput(
                definitionName=name,
                workflow=workflow._to_model(),
                datasetId=rapidata_dataset.id,
                referee=referee._to_model(),
                featureFlags=(
                    [s._to_feature_flag() for s in settings] if settings else None
                ),
            )
        )
        job_model = JobDefinition(
            id=job_definition_response.definition_id,
            name=name,
            openapi_service=self._openapi_service,
        )

        if failed_uploads:
            raise FailedUploadException(rapidata_dataset, failed_uploads, job=job_model)

        return job_model

    def create_classification_job_definition(
        self,
        name: str,
        instruction: str,
        answer_options: list[str],
        datapoints: list[str],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        confidence_threshold: float | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a classification job definition.

        With this order you can have a datapoint (image, text, video, audio) be classified into one of the answer options.
        Each response will be exactly one of the answer options.

        Args:
            name (str): The name of the job. (Will not be shown to the labeler)
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
            confidence_threshold (float, optional): The probability threshold for the classification. Defaults to None.\n
                If provided, the classification datapoint will stop after the threshold is reached or at the number of responses, whatever happens first.
            settings (Sequence[RapidataSetting], optional): The list of settings for the classification. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_classification_job"):
            if not isinstance(datapoints, list) or not all(
                isinstance(datapoint, str) for datapoint in datapoints
            ):
                raise ValueError("Datapoints must be a list of strings")

            from rapidata.rapidata_client.workflow import ClassifyWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_metadata=private_metadata,
                data_type=data_type,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=ClassifyWorkflow(
                    instruction=instruction, answer_options=answer_options
                ),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                confidence_threshold=confidence_threshold,
                settings=settings,
            )

    def create_compare_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        a_b_names: list[str] | None = None,
        confidence_threshold: float | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a compare job definition.

        With this order you compare two datapoints (image, text, video, audio) and the annotators will choose one of the two based on the instruction.

        Args:
            name (str): The name of the job. (Will not be shown to the labeler)
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
            confidence_threshold (float, optional): The probability threshold for the comparison. Defaults to None.\n
                If provided, the comparison datapoint will stop after the threshold is reached or at the number of responses, whatever happens first.
            settings (Sequence[RapidataSetting], optional): The list of settings for the comparison. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_compare_job"):
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

            from rapidata.rapidata_client.workflow import CompareWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_metadata=private_metadata,
                data_type=data_type,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=CompareWorkflow(instruction=instruction, a_b_names=a_b_names),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                confidence_threshold=confidence_threshold,
                settings=settings,
            )

    def _create_ranking_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        comparison_budget_per_ranking: int,
        responses_per_comparison: int = 1,
        data_type: Literal["media", "text"] = "media",
        random_comparisons_ratio: float = 0.5,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> JobDefinition:
        """
        Create a ranking job definition.

        With this order you can have a multiple lists of datapoints (image, text, video, audio) be ranked based on the instruction.
        Each list will be ranked independently, based on comparison matchups.

        Args:
            name (str): The name of the job.
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
            settings (Sequence[RapidataSetting], optional): The list of settings for the ranking. Defaults to []. Decides how the tasks should be shown.
        """
        with tracer.start_as_current_span("JobManager.create_ranking_job"):
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

            from rapidata.rapidata_client.workflow import MultiRankingWorkflow
            from rapidata.api_client.models.i_asset_input import IAssetInput
            from rapidata.api_client.models.i_asset_input_existing_asset_input import (
                IAssetInputExistingAssetInput,
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
                    str(i): IAssetInput(
                        actual_instance=IAssetInputExistingAssetInput(
                            _t="ExistingAssetInput",
                            name=self._asset_uploader.upload_asset(media_context),
                        )
                    )
                    for i, media_context in enumerate(media_contexts)
                }
                if media_contexts
                else None
            )

            return self._create_general_job_definition(
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
                settings=settings,
            )

    def _create_free_text_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a free text job definition.

        With this order you can have a datapoint (image, text, video, audio) be labeled with free text.
        The annotators will be shown a datapoint and will be asked to answer a question with free text.

        Args:
            name (str): The name of the job.
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
            settings (Sequence[RapidataSetting], optional): The list of settings for the free text. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_free_text_job"):
            from rapidata.rapidata_client.workflow import FreeTextWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_metadata=private_metadata,
                data_type=data_type,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=FreeTextWorkflow(instruction=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                settings=settings,
            )

    def _create_select_words_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        sentences: list[str],
        responses_per_datapoint: int = 10,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a select words job definition.

        With this order you can have a datapoint (image, text, video, audio) be labeled with a list of words.
        The annotators will be shown a datapoint as well as a list of sentences split up by spaces.
        They will then select specific words based on the instruction.

        Args:
            name (str): The name of the job.
            instruction (str): The instruction for how the words should be selected. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the select words - each datapoint will be labeled.
            sentences (list[str]): The list of sentences for the select words - Will be split up by spaces and shown along side each datapoint.\n
                Must be the same length as datapoints.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            settings (Sequence[RapidataSetting], optional): The list of settings for the select words. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_select_words_job"):
            from rapidata.rapidata_client.workflow import SelectWordsWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                sentences=sentences,
                private_metadata=private_metadata,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=SelectWordsWorkflow(
                    instruction=instruction,
                ),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                settings=settings,
            )

    def _create_locate_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a locate job definition.

        With this order you can have people locate specific objects in a datapoint (image, text, video, audio).
        The annotators will be shown a datapoint and will be asked to select locations based on the instruction.

        Args:
            name (str): The name of the job. (Will not be shown to the labeler)
            instruction (str): The instruction what should be located. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the locate - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the locate. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the locate i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
            settings (Sequence[RapidataSetting], optional): The list of settings for the locate. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_locate_job"):
            from rapidata.rapidata_client.workflow import LocateWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_metadata=private_metadata,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=LocateWorkflow(target=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                settings=settings,
            )

    def _create_draw_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a draw job definition.

        With this order you can have people draw lines on a datapoint (image, text, video, audio).
        The annotators will be shown a datapoint and will be asked to draw lines based on the instruction.

        Args:
            name (str): The name of the job. (Will not be shown to the labeler)
            instruction (str): The instruction for how the lines should be drawn. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the draw lines - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the draw lines i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
            settings (Sequence[RapidataSetting], optional): The list of settings for the draw lines. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_draw_job"):
            from rapidata.rapidata_client.workflow import DrawWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_metadata=private_metadata,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=DrawWorkflow(target=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                settings=settings,
            )

    def _create_timestamp_job_definition(
        self,
        name: str,
        instruction: str,
        datapoints: list[str],
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Create a timestamp job definition.

        Warning:
            This job is currently not fully supported and may give unexpected results.

        With this order you can have people mark specific timestamps in a datapoint (video, audio).
        The annotators will be shown a datapoint and will be asked to select a timestamp based on the instruction.

        Args:
            name (str): The name of the job. (Will not be shown to the labeler)
            instruction (str): The instruction for the timestamp task. Will be shown along side each datapoint.
            datapoints (list[str]): The list of datapoints for the timestamp - each datapoint will be labeled.
            responses_per_datapoint (int, optional): The number of responses that will be collected per datapoint. Defaults to 10.
            contexts (list[str], optional): The list of contexts for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts for the timestamp i.e links to the images / videos. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
            settings (Sequence[RapidataSetting], optional): The list of settings for the timestamp. Defaults to []. Decides how the tasks should be shown.
            private_metadata (list[dict[str, str]], optional): Key-value string pairs for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints.\n
                This will NOT be shown to the labelers but will be included in the result purely for your own reference.
        """
        with tracer.start_as_current_span("JobManager.create_timestamp_job"):
            from rapidata.rapidata_client.workflow import TimestampWorkflow

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                private_metadata=private_metadata,
            )
            return self._create_general_job_definition(
                name=name,
                workflow=TimestampWorkflow(instruction=instruction),
                datapoints=datapoints_instances,
                responses_per_datapoint=responses_per_datapoint,
                settings=settings,
            )

    def get_job_definition_by_id(self, job_definition_id: str) -> JobDefinition:
        """Get a job definition by ID.

        Args:
            job_definition_id (str): The ID of the job definition.

        Returns:
            JobDefinition: The JobDefinition instance.
        """
        with tracer.start_as_current_span("JobManager.get_job_definition_by_id"):

            job_definition = (
                self._openapi_service.job_api.job_definition_definition_id_get(
                    definition_id=job_definition_id,
                )
            )

            return JobDefinition(
                id=job_definition.definition_id,
                name=job_definition.name,
                openapi_service=self._openapi_service,
            )

    def find_job_definitions(
        self, name: str = "", amount: int = 10
    ) -> list[JobDefinition]:
        """Find your recent jobs given criteria. If nothing is provided, it will return the most recent job definitions.

        Args:
            name (str, optional): The name of the job definition - matching job definition will contain the name. Defaults to "" for any job definition.
            amount (int, optional): The amount of job definitions to return. Defaults to 10.

        Returns:
            list[JobDefinition]: A list of JobDefinition instances.
        """
        with tracer.start_as_current_span("JobManager.find_job_definitions"):
            from rapidata.api_client.models.page_info import PageInfo
            from rapidata.api_client.models.query_model import QueryModel
            from rapidata.api_client.models.root_filter import RootFilter
            from rapidata.api_client.models.filter import Filter
            from rapidata.api_client.models.filter_operator import FilterOperator
            from rapidata.api_client.models.sort_criterion import SortCriterion
            from rapidata.api_client.models.sort_direction import SortDirection

            job_definition_page_result = (
                self._openapi_service.job_api.job_definitions_get(
                    request=QueryModel(
                        page=PageInfo(index=1, size=amount),
                        filter=RootFilter(
                            filters=[
                                Filter(
                                    field="Name",
                                    operator=FilterOperator.CONTAINS,
                                    value=name,
                                )
                            ]
                        ),
                        sortCriteria=[
                            SortCriterion(
                                direction=SortDirection.DESC, propertyName="CreatedAt"
                            )
                        ],
                    ),
                )
            )

            jobs = [
                JobDefinition(
                    id=job_def.definition_id,
                    name=job_def.name,
                    openapi_service=self._openapi_service,
                )
                for job_def in job_definition_page_result.items
            ]
            return jobs

    def get_job_by_id(self, job_id: str) -> RapidataJob:
        """Get a job by ID.

        Args:
            job_id (str): The ID of the job.

        Returns:
            RapidataJob: The Job instance.
        """
        with tracer.start_as_current_span("JobManager.get_job_by_id"):
            from rapidata.rapidata_client.job.rapidata_job import RapidataJob

            job_response = self._openapi_service.job_api.job_job_id_get(
                job_id=job_id,
            )
            return RapidataJob(
                job_id=job_response.job_id,
                name=job_response.name,
                audience_id=job_response.audience_id,
                created_at=job_response.created_at,
                definition_id=job_response.definition_id,
                openapi_service=self._openapi_service,
                pipeline_id=job_response.pipeline_id,
            )

    def find_jobs(self, name: str = "", amount: int = 10) -> list[RapidataJob]:
        """Find your recent jobs given criteria. If nothing is provided, it will return the most recent jobs.

        Args:
            name (str, optional): The name of the job - matching job will contain the name. Defaults to "" for any job.
            amount (int, optional): The amount of jobs to return. Defaults to 10.

        Returns:
            list[RapidataJob]: A list of RapidataJob instances.
        """
        with tracer.start_as_current_span("JobManager.find_jobs"):
            from rapidata.api_client.models.query_model import QueryModel
            from rapidata.api_client.models.root_filter import RootFilter
            from rapidata.api_client.models.filter import Filter
            from rapidata.api_client.models.filter_operator import FilterOperator
            from rapidata.api_client.models.page_info import PageInfo
            from rapidata.api_client.models.sort_criterion import SortCriterion
            from rapidata.api_client.models.sort_direction import SortDirection
            from rapidata.rapidata_client.job.rapidata_job import RapidataJob

            response = self._openapi_service.job_api.jobs_get(
                request=QueryModel(
                    page=PageInfo(index=1, size=amount),
                    filter=RootFilter(
                        filters=[
                            Filter(
                                field="Name",
                                operator=FilterOperator.CONTAINS,
                                value=name,
                            )
                        ]
                    ),
                    sortCriteria=[
                        SortCriterion(
                            direction=SortDirection.DESC, propertyName="CreatedAt"
                        )
                    ],
                ),
            )
            jobs = [
                RapidataJob(
                    job_id=job.job_id,
                    name=job.name,
                    audience_id=job.audience_id,
                    created_at=job.created_at,
                    definition_id=job.definition_id,
                    openapi_service=self._openapi_service,
                    pipeline_id=job.pipeline_id,
                )
                for job in response.items
            ]
            return jobs

    def __str__(self) -> str:
        return "JobManager"

    def __repr__(self) -> str:
        return self.__str__()
