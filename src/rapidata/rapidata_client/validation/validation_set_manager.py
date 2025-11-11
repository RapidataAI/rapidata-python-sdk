import time
import urllib.parse
import webbrowser
from colorama import Fore
from typing import Literal
from rapidata.api_client import QueryModel
from rapidata.rapidata_client.validation.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.api_client.models.create_validation_set_model import (
    CreateValidationSetModel,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.validation.rapids.rapids_manager import RapidsManager
from rapidata.rapidata_client.validation.rapids.rapids import Rapid

from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion
from rapidata.api_client.models.sort_direction import SortDirection
from rapidata.api_client.models.filter_operator import FilterOperator

from rapidata.rapidata_client.validation.rapids.box import Box

from rapidata.rapidata_client.config import (
    logger,
    managed_print,
    rapidata_config,
    tracer,
)
from tqdm import tqdm
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting
from typing import Sequence


class ValidationSetManager:
    """
    Responsible for everything related to validation sets. From creation to retrieval.

    Attributes:
        rapid (RapidsManager): The RapidsManager instance.
    """

    def __init__(self, openapi_service: OpenAPIService) -> None:
        self._openapi_service = openapi_service
        self.rapid = RapidsManager(openapi_service)
        logger.debug("ValidationSetManager initialized")

    def _get_total_and_labeled_rapids_count(
        self, validation_set_id: str
    ) -> tuple[int, int]:
        uploaded_rapids = self._openapi_service.validation_api.validation_set_validation_set_id_rapids_get(
            validation_set_id=validation_set_id
        ).items
        return len(uploaded_rapids), sum(1 for rapid in uploaded_rapids if rapid.truth)

    def create_classification_set(
        self,
        name: str,
        instruction: str,
        answer_options: list[str],
        datapoints: list[str],
        truths: list[list[str]],
        data_type: Literal["media", "text"] = "media",
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        explanations: list[str | None] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a classification validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction by which the labeler will answer.
            answer_options (list[str]): The options to choose from when answering.
            datapoints (list[str]): The datapoints that will be used for validation.
            truths (list[list[str]]): The truths for each datapoint. Outer list is for each datapoint, inner list is for each truth.\n
                example:
                    options: ["yes", "no", "maybe"]
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [["yes"], ["no", "maybe"]] -> first datapoint correct answer is "yes", second datapoint is "no" or "maybe"
            data_type (str, optional): The type of data. Defaults to "media" (any form of image, video or audio). Other option: "text".
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and answer options. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts i.e. links to the images / videos for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            explanations (list[str | None], optional): The explanations for each datapoint. Will be given to the annotators in case the answer is wrong. Defaults to None.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.

        Example:
            ```python
            options: ["yes", "no", "maybe"]
            datapoints: ["datapoint1", "datapoint2"]
            truths: [["yes"], ["no", "maybe"]]
            ```
            This would mean: first datapoint correct answer is "yes", second datapoint is "no" or "maybe"
        """
        with tracer.start_as_current_span(
            "ValidationSetManager.create_classification_set"
        ):
            if not datapoints:
                raise ValueError("Datapoints cannot be empty")

            if len(datapoints) != len(truths):
                raise ValueError("The number of datapoints and truths must be equal")

            if not all([isinstance(truth, (list, tuple)) for truth in truths]):
                raise ValueError("Truths must be a list of lists or tuples")

            if contexts and len(contexts) != len(datapoints):
                raise ValueError("The number of contexts and datapoints must be equal")

            if media_contexts and len(media_contexts) != len(datapoints):
                raise ValueError(
                    "The number of media contexts and datapoints must be equal"
                )

            if explanations and len(explanations) != len(datapoints):
                raise ValueError(
                    "The number of explanations and datapoints must be equal, the index must align, but can be padded with None"
                )

            logger.debug("Creating classification rapids")
            rapids: list[Rapid] = []
            for i in range(len(datapoints)):
                rapids.append(
                    self.rapid.classification_rapid(
                        instruction=instruction,
                        answer_options=answer_options,
                        datapoint=datapoints[i],
                        truths=truths[i],
                        data_type=data_type,
                        context=contexts[i] if contexts != None else None,
                        media_context=(
                            media_contexts[i] if media_contexts != None else None
                        ),
                        explanation=explanations[i] if explanations != None else None,
                    )
                )

            logger.debug("Submitting classification rapids")
            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_compare_set(
        self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        truths: list[str],
        data_type: Literal["media", "text"] = "media",
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        explanation: list[str | None] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a comparison validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to compare against.
            truths (list[str]): The truths for each comparison. List is for each comparison.\n
                example:
                    instruction: "Which image has a cat?"
                    datapoints = [["image1.jpg", "image2.jpg"], ["image3.jpg", "image4.jpg"]]
                    truths: ["image1.jpg", "image4.jpg"] -> first comparison image1.jpg has a cat, second comparison image4.jpg has a cat
            datapoints (list[list[str]]): The compare datapoints to create the validation set with.
                Outer list is for each comparison, inner list the two images/texts that will be compared.
            data_type (str, optional): The type of data. Defaults to "media" (any form of image, video or audio). Other option: "text".
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and truth. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            media_contexts (list[str], optional): The list of media contexts i.e. links to the images / videos for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            explanation (list[str | None], optional): The explanations for each datapoint. Will be given to the annotators in case the answer is wrong. Defaults to None.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.

        Example:
            ```python
            instruction: "Which image has a cat?"
            datapoints = [["image1.jpg", "image2.jpg"], ["image3.jpg", "image4.jpg"]]
            truths: ["image1.jpg", "image4.jpg"]
            ```
            This would mean: first comparison image1.jpg has a cat, second comparison image4.jpg has a cat
        """
        with tracer.start_as_current_span("ValidationSetManager.create_compare_set"):
            if not datapoints:
                raise ValueError("Datapoints cannot be empty")

            if len(datapoints) != len(truths):
                raise ValueError("The number of datapoints and truths must be equal")

            if not all([isinstance(truth, str) for truth in truths]):
                raise ValueError("Truths must be a list of strings")

            if contexts and len(contexts) != len(datapoints):
                raise ValueError("The number of contexts and datapoints must be equal")

            if media_contexts and len(media_contexts) != len(datapoints):
                raise ValueError(
                    "The number of media contexts and datapoints must be equal"
                )

            if explanation and len(explanation) != len(datapoints):
                raise ValueError(
                    "The number of explanations and datapoints must be equal, the index must align, but can be padded with None"
                )

            logger.debug("Creating comparison rapids")
            rapids: list[Rapid] = []
            for i in range(len(datapoints)):
                rapids.append(
                    self.rapid.compare_rapid(
                        instruction=instruction,
                        truth=truths[i],
                        datapoint=datapoints[i],
                        data_type=data_type,
                        context=contexts[i] if contexts != None else None,
                        media_context=(
                            media_contexts[i] if media_contexts != None else None
                        ),
                        explanation=explanation[i] if explanation != None else None,
                    )
                )

            logger.debug("Submitting comparison rapids")
            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_select_words_set(
        self,
        name: str,
        instruction: str,
        truths: list[list[int]],
        datapoints: list[str],
        sentences: list[str],
        required_precision: float = 1.0,
        required_completeness: float = 1.0,
        explanation: list[str | None] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a select words validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[int]]): The truths for each datapoint. Outer list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    sentences: ["this example 1", "this example with another text"]
                    truths: [[0, 1], [2]] -> first datapoint correct words are "this" and "example", second datapoint is "with"
            datapoints (list[str]): The datapoints that will be used for validation.
            sentences (list[str]): The sentences that will be used for validation. The sentece will be split up by spaces to be selected by the labeler.
                Must be the same length as datapoints.
            required_precision (float, optional): The required precision for the labeler to get the rapid correct (minimum ratio of the words selected that need to be correct). Defaults to 1.0 (no wrong word can be selected).
            required_completeness (float, optional): The required completeness for the labeler to get the rapid correct (miminum ratio of total correct words selected). Defaults to 1.0 (all correct words need to be selected).
            explanation (list[str | None], optional): The explanations for each datapoint. Will be given to the annotators in case the answer is wrong. Defaults to None.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.

        Example:
            ```python
            datapoints: ["datapoint1", "datapoint2"]
            sentences: ["this example 1", "this example with another text"]
            truths: [[0, 1], [2]]
            ```
            This would mean: first datapoint the correct words are "this" and "example", second datapoint is "with"
        """
        with tracer.start_as_current_span(
            "ValidationSetManager.create_select_words_set"
        ):
            if not datapoints:
                raise ValueError("Datapoints cannot be empty")

            if not all([isinstance(truth, (list, tuple)) for truth in truths]):
                raise ValueError("Truths must be a list of lists or tuples")

            if len(datapoints) != len(truths) or len(datapoints) != len(sentences):
                raise ValueError(
                    "The number of datapoints, truths, and sentences must be equal"
                )

            if explanation and len(explanation) != len(datapoints):
                raise ValueError(
                    "The number of explanations and datapoints must be equal, the index must align, but can be padded with None"
                )

            logger.debug("Creating select words rapids")
            rapids: list[Rapid] = []
            for i in range(len(datapoints)):
                rapids.append(
                    self.rapid.select_words_rapid(
                        instruction=instruction,
                        truths=truths[i],
                        datapoint=datapoints[i],
                        sentence=sentences[i],
                        required_precision=required_precision,
                        required_completeness=required_completeness,
                        explanation=explanation[i] if explanation != None else None,
                    )
                )

            logger.debug("Submitting select words rapids")
            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_locate_set(
        self,
        name: str,
        instruction: str,
        truths: list[list[Box]],
        datapoints: list[str],
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        explanation: list[str | None] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a locate validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[Box]]): The truths for each datapoint. Outer list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [[Box(0, 0, 100, 100)], [Box(50, 50, 150, 150)]] -> first datapoint the object is in the top left corner, second datapoint the object is in the center
            datapoints (list[str]): The datapoints that will be used for validation.
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.
            media_contexts (list[str], optional): The list of media contexts i.e. links to the images / videos for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            explanation (list[str | None], optional): The explanations for each datapoint. Will be given to the annotators in case the answer is wrong. Defaults to None.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.

        Example:
            ```python
            datapoints: ["datapoint1", "datapoint2"]
            truths: [[Box(0, 0, 100, 100)], [Box(50, 50, 150, 150)]]
            ```
            This would mean: first datapoint the object is in the top left corner, second datapoint the object is in the center
        """
        with tracer.start_as_current_span("ValidationSetManager.create_locate_set"):
            if not datapoints:
                raise ValueError("Datapoints cannot be empty")

            if len(datapoints) != len(truths):
                raise ValueError("The number of datapoints and truths must be equal")

            if not all([isinstance(truth, (list, tuple)) for truth in truths]):
                raise ValueError("Truths must be a list of lists or tuples")

            if contexts and len(contexts) != len(datapoints):
                raise ValueError("The number of contexts and datapoints must be equal")

            if media_contexts and len(media_contexts) != len(datapoints):
                raise ValueError(
                    "The number of media contexts and datapoints must be equal"
                )

            if explanation and len(explanation) != len(datapoints):
                raise ValueError(
                    "The number of explanations and datapoints must be equal, the index must align, but can be padded with None"
                )

            logger.debug("Creating locate rapids")
            rapids = []
            rapids: list[Rapid] = []
            for i in range(len(datapoints)):
                rapids.append(
                    self.rapid.locate_rapid(
                        instruction=instruction,
                        truths=truths[i],
                        datapoint=datapoints[i],
                        context=contexts[i] if contexts != None else None,
                        media_context=(
                            media_contexts[i] if media_contexts != None else None
                        ),
                        explanation=explanation[i] if explanation != None else None,
                    )
                )

            logger.debug("Submitting locate rapids")
            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_draw_set(
        self,
        name: str,
        instruction: str,
        truths: list[list[Box]],
        datapoints: list[str],
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        explanation: list[str | None] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a draw validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[Box]]): The truths for each datapoint. Outer list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [[Box(0, 0, 100, 100)], [Box(50, 50, 150, 150)]] -> first datapoint the object is in the top left corner, second datapoint the object is in the center
            datapoints (list[str]): The datapoints that will be used for validation.
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.
            media_contexts (list[str], optional): The list of media contexts i.e. links to the images / videos for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            explanation (list[str | None], optional): The explanations for each datapoint. Will be given to the annotators in case the answer is wrong. Defaults to None.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.

        Example:
            ```python
            datapoints: ["datapoint1", "datapoint2"]
            truths: [[Box(0, 0, 100, 100)], [Box(50, 50, 150, 150)]]
            ```
            This would mean: first datapoint the object is in the top left corner, second datapoint the object is in the center
        """
        with tracer.start_as_current_span("ValidationSetManager.create_draw_set"):
            if not datapoints:
                raise ValueError("Datapoints cannot be empty")

            if len(datapoints) != len(truths):
                raise ValueError("The number of datapoints and truths must be equal")

            if not all([isinstance(truth, (list, tuple)) for truth in truths]):
                raise ValueError("Truths must be a list of lists or tuples")

            if contexts and len(contexts) != len(datapoints):
                raise ValueError("The number of contexts and datapoints must be equal")

            if media_contexts and len(media_contexts) != len(datapoints):
                raise ValueError(
                    "The number of media contexts and datapoints must be equal"
                )

            if explanation and len(explanation) != len(datapoints):
                raise ValueError(
                    "The number of explanations and datapoints must be equal, the index must align, but can be padded with None"
                )

            logger.debug("Creating draw rapids")
            rapids: list[Rapid] = []
            for i in range(len(datapoints)):
                rapids.append(
                    self.rapid.draw_rapid(
                        instruction=instruction,
                        truths=truths[i],
                        datapoint=datapoints[i],
                        context=contexts[i] if contexts != None else None,
                        media_context=(
                            media_contexts[i] if media_contexts != None else None
                        ),
                        explanation=explanation[i] if explanation != None else None,
                    )
                )

            logger.debug("Submitting draw rapids")
            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_timestamp_set(
        self,
        name: str,
        instruction: str,
        truths: list[list[tuple[int, int]]],
        datapoints: list[str],
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        explanation: list[str | None] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a timestamp validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[tuple[int, int]]]): The truths for each datapoint defined as start and endpoint based on miliseconds.
                Outer list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [[(0, 10)], [(20, 30)]] -> first datapoint the correct interval is from 0 to 10, second datapoint the correct interval is from 20 to 30
            datapoints (list[str]): The datapoints that will be used for validation.
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.
            media_contexts (list[str], optional): The list of media contexts i.e. links to the images / videos for the comparison. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction. (Therefore will be different for each datapoint)
                Will be matched up with the datapoints using the list index.
            explanation (list[str | None], optional): The explanations for each datapoint. Will be given to the annotators in case the answer is wrong. Defaults to None.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.

        Example:
            ```python
            datapoints: ["datapoint1", "datapoint2"]
            truths: [[(0, 10)], [(20, 30)]]
            ```
            This would mean: first datapoint the correct interval is from 0 to 10, second datapoint the correct interval is from 20 to 30
        """
        with tracer.start_as_current_span("ValidationSetManager.create_timestamp_set"):
            if not datapoints:
                raise ValueError("Datapoints cannot be empty")

            if len(datapoints) != len(truths):
                raise ValueError("The number of datapoints and truths must be equal")

            if not all([isinstance(truth, (list, tuple)) for truth in truths]):
                raise ValueError("Truths must be a list of lists or tuples")

            if contexts and len(contexts) != len(datapoints):
                raise ValueError("The number of contexts and datapoints must be equal")

            if media_contexts and len(media_contexts) != len(datapoints):
                raise ValueError(
                    "The number of media contexts and datapoints must be equal"
                )

            if explanation and len(explanation) != len(datapoints):
                raise ValueError(
                    "The number of explanations and datapoints must be equal, the index must align, but can be padded with None"
                )

            logger.debug("Creating timestamp rapids")
            rapids: list[Rapid] = []
            for i in range(len(datapoints)):
                rapids.append(
                    self.rapid.timestamp_rapid(
                        instruction=instruction,
                        truths=truths[i],
                        datapoint=datapoints[i],
                        context=contexts[i] if contexts != None else None,
                        media_context=(
                            media_contexts[i] if media_contexts != None else None
                        ),
                        explanation=explanation[i] if explanation != None else None,
                    )
                )

            logger.debug("Submitting timestamp rapids")
            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_mixed_set(
        self,
        name: str,
        rapids: list[Rapid],
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        """Create a validation set with a list of rapids.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            rapids (list[Rapid]): The list of rapids to add to the validation set.
            dimensions (list[str], optional): The dimensions to add to the validation set accross which users will be tracked. Defaults to [] which is the default dimension.
        """
        with tracer.start_as_current_span("ValidationSetManager.create_mixed_set"):
            if not rapids:
                raise ValueError("Rapids cannot be empty")

            return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def _submit(
        self, name: str, rapids: list[Rapid], dimensions: list[str]
    ) -> RapidataValidationSet:
        logger.debug("Creating validation set")
        validation_set_id = (
            self._openapi_service.validation_api.validation_set_post(
                create_validation_set_model=CreateValidationSetModel(name=name)
            )
        ).validation_set_id

        logger.debug("Validation set created with ID: %s", validation_set_id)

        if validation_set_id is None:
            raise ValueError("Failed to create validation set")

        logger.debug("Creating validation set instance")

        validation_set = RapidataValidationSet(
            name=name,
            validation_set_id=validation_set_id,
            dimensions=dimensions,
            openapi_service=self._openapi_service,
        )
        with tracer.start_as_current_span("Adding rapids to validation set"):
            logger.debug("Adding rapids to validation set")
            failed_rapids = []

            progress_bar = tqdm(
                total=len(rapids),
                desc="Uploading validation tasks",
                disable=rapidata_config.logging.silent_mode,
            )

            for rapid in rapids:
                try:
                    validation_set.add_rapid(rapid)
                    progress_bar.update(1)
                except Exception as e:
                    logger.error(
                        "Failed to add rapid %s to validation set.\nError: %s",
                        rapid.asset,
                        str(e),
                    )
                    failed_rapids.append(rapid.asset)

            progress_bar.close()

            if failed_rapids:
                logger.error(
                    "Failed to add %s datapoints to validation set: %s",
                    len(failed_rapids),
                    failed_rapids,
                )
                raise RuntimeError(
                    f"Failed to add {len(failed_rapids)} datapoints to validation set: {failed_rapids}"
                )

        managed_print()
        managed_print(
            f"Validation set '{name}' created with ID {validation_set_id}\n",
            f"Now viewable under: {validation_set.validation_set_details_page}",
            sep="",
        )

        if dimensions:
            validation_set.update_dimensions(dimensions)

        self._openapi_service.validation_api.validation_set_validation_set_id_update_labeling_hints_post(
            validation_set_id=validation_set_id
        )

        return validation_set

    def _create_order_validation_set(
        self,
        workflow: Workflow,
        name: str,
        datapoints: list[Datapoint],
        required_amount: int,
        settings: Sequence[RapidataSetting] | None = None,
        dimensions: list[str] = [],
    ) -> RapidataValidationSet:
        with tracer.start_as_current_span(
            "ValidationSetManager._create_order_validation_set"
        ):
            rapids: list[Rapid] = []
            for datapoint in workflow._format_datapoints(datapoints):
                rapids.append(
                    Rapid(
                        asset=datapoint.asset,
                        payload=workflow._to_payload(datapoint),
                        context=datapoint.context,
                        media_context=datapoint.media_context,
                        data_type=datapoint.data_type,
                        settings=settings,
                    )
                )
            validation_set = RapidataValidationSet(
                validation_set_id=self._openapi_service.validation_api.validation_set_post(
                    create_validation_set_model=CreateValidationSetModel(name=name)
                ).validation_set_id,
                name=name,
                dimensions=dimensions,
                openapi_service=self._openapi_service,
            )

            managed_print()
            managed_print(
                Fore.YELLOW
                + f"A new validation set was created. Please annotate {required_amount} datapoint{('s' if required_amount != 1 else '')} before the order can run."
                + Fore.RESET
            )

            link = f"https://app.{self._openapi_service.environment}/validation-set/detail/{validation_set.id}/annotate?maxSize={len(datapoints)}&required={required_amount}"
            could_open_browser = webbrowser.open(link)
            if not could_open_browser:
                encoded_url = urllib.parse.quote(link, safe="%/:=&?~#+!$,;'@()*[]")
                managed_print(
                    Fore.RED
                    + f"Please open this URL in your browser to annotate the validation set: '{encoded_url}'"
                    + Fore.RESET
                )
            else:
                managed_print(
                    Fore.YELLOW
                    + f"Please annotate the validation set. \n'{link}'"
                    + Fore.RESET
                )

            with tracer.start_as_current_span("Annotating validation set"):
                progress_bar = tqdm(
                    total=required_amount,
                    desc="Annotate the validation set",
                    disable=rapidata_config.logging.silent_mode,
                )

                rapid_index = 0
                while True:
                    total_rapids, labeled_rapids = (
                        self._get_total_and_labeled_rapids_count(validation_set.id)
                    )

                    progress_bar.n = labeled_rapids
                    progress_bar.refresh()

                    if labeled_rapids >= required_amount:
                        break

                    if total_rapids < required_amount and rapid_index >= len(rapids):
                        managed_print(
                            Fore.RED
                            + f"""Warning: An order can only be started with at least {required_amount} annotated validation tasks. But only {labeled_rapids}/{required_amount} were annotated.
Either add clearer examples or turn off the 'autoValidationSetCreation' with:

from rapidata import rapidata_config
rapidata_config.order.autoValidationSetCreation = False"""
                            + Fore.RESET
                        )
                        raise RuntimeError(
                            f"Not enough rapids annotated. Required: {required_amount}, Annotated: {labeled_rapids}")

                    if (
                        rapid_index < len(rapids)
                        and total_rapids - labeled_rapids <= required_amount * 2
                    ):
                        validation_set.add_rapid(rapids[rapid_index])
                        rapid_index += 1

                    time.sleep(2)

                progress_bar.close()

            return validation_set

    def get_validation_set_by_id(self, validation_set_id: str) -> RapidataValidationSet:
        """Get a validation set by ID.

        Args:
            validation_set_id (str): The ID of the validation set.

        Returns:
            RapidataValidationSet: The ValidationSet instance.
        """

        with tracer.start_as_current_span(
            "ValidationSetManager.get_validation_set_by_id"
        ):
            validation_set = self._openapi_service.validation_api.validation_set_validation_set_id_get(
                validation_set_id=validation_set_id
            )

            return RapidataValidationSet(
                validation_set_id,
                str(validation_set.name),
                validation_set.dimensions,
                self._openapi_service,
            )

    def find_validation_sets(
        self, name: str = "", amount: int = 10
    ) -> list[RapidataValidationSet]:
        """Find validation sets by name.

        Args:
            name (str, optional): The name to search for. Defaults to "" to match with any set.
            amount (int, optional): The amount of validation sets to return. Defaults to 10.

        Returns:
            list[RapidataValidationSet]: The list of validation sets.
        """
        with tracer.start_as_current_span("ValidationSetManager.find_validation_sets"):

            validation_page_result = (
                self._openapi_service.validation_api.validation_sets_get(
                    QueryModel(
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
                    )
                )
            )

            validation_sets = [
                self.get_validation_set_by_id(str(validation_set.id))
                for validation_set in validation_page_result.items
            ]
            return validation_sets

    def __str__(self) -> str:
        return "ValidationSetManager"

    def __repr__(self) -> str:
        return self.__str__()
