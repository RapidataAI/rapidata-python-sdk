from typing import Literal
from rapidata.api_client import QueryModel
from rapidata.rapidata_client.validation.rapidata_validation_set import RapidataValidationSet
from rapidata.api_client.models.create_validation_set_model import CreateValidationSetModel
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.validation.rapids.rapids_manager import RapidsManager
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.rapidata_client.datapoints.metadata import PromptMetadata, MediaAssetMetadata

from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion

from rapidata.rapidata_client.validation.rapids.box import Box

from rapidata.rapidata_client.logging import logger, managed_print, RapidataOutputManager
from tqdm import tqdm


class ValidationSetManager:
    """
    Responsible for everything related to validation sets. From creation to retrieval.

    Attributes:
        rapid (RapidsManager): The RapidsManager instance.
    """
    def __init__(self, openapi_service: OpenAPIService) -> None:
        self.__openapi_service = openapi_service
        self.rapid = RapidsManager()
        logger.debug("ValidationSetManager initialized")

    def create_classification_set(self,
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
        if not datapoints:
            raise ValueError("Datapoints cannot be empty")
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")

        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("The number of media contexts and datapoints must be equal")

        if(explanations and len(explanations) != len(datapoints)):
            raise ValueError("The number of explanations and datapoints must be equal, the index must align, but can be padded with None")

       
        logger.debug("Creating classification rapids")
        rapids: list[Rapid] = []
        for i in range(len(datapoints)):
            rapid_metadata = []
            if contexts:
                rapid_metadata.append(PromptMetadata(contexts[i]))
            if media_contexts:
                rapid_metadata.append(MediaAssetMetadata(media_contexts[i]))
            rapids.append(
                self.rapid.classification_rapid(
                    instruction=instruction,
                    answer_options=answer_options,
                    datapoint=datapoints[i],
                    truths=truths[i],
                    data_type=data_type,
                    metadata=rapid_metadata,
                    explanation=explanations[i] if explanations != None else None
                )
            )

        logger.debug("Submitting classification rapids")
        return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_compare_set(self,
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
        if not datapoints:
            raise ValueError("Datapoints cannot be empty")
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, str) for truth in truths]):
            raise ValueError("Truths must be a list of strings")

        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")

        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("The number of media contexts and datapoints must be equal")
 
        if(explanation and len(explanation) != len(datapoints)):
            raise ValueError("The number of explanations and datapoints must be equal, the index must align, but can be padded with None")
        
        logger.debug("Creating comparison rapids")
        rapids: list[Rapid] = []
        for i in range(len(datapoints)):
            rapid_metadata = []
            if contexts:
                rapid_metadata.append(PromptMetadata(contexts[i]))
            if media_contexts:
                rapid_metadata.append(MediaAssetMetadata(media_contexts[i]))
            rapids.append(
                self.rapid.compare_rapid(
                    instruction=instruction,
                    truth=truths[i],
                    datapoint=datapoints[i],
                    data_type=data_type,
                    metadata=rapid_metadata,
                    explanation=explanation[i] if explanation != None else None
                )
            )
        
        logger.debug("Submitting comparison rapids")
        return self._submit(name=name, rapids=rapids, dimensions=dimensions)
  
    def create_select_words_set(self,
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
        if not datapoints:
            raise ValueError("Datapoints cannot be empty")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")

        if len(datapoints) != len(truths) or len(datapoints) != len(sentences):
            raise ValueError("The number of datapoints, truths, and sentences must be equal")
 
        if(explanation and len(explanation) != len(datapoints)):
            raise ValueError("The number of explanations and datapoints must be equal, the index must align, but can be padded with None")

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
                    explanation=explanation[i] if explanation != None else None
                )
            )

        logger.debug("Submitting select words rapids")
        return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_locate_set(self,
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
        if not datapoints:
            raise ValueError("Datapoints cannot be empty")
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
 
        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("The number of media contexts and datapoints must be equal")

        if(explanation and len(explanation) != len(datapoints)):
            raise ValueError("The number of explanations and datapoints must be equal, the index must align, but can be padded with None")
        
        logger.debug("Creating locate rapids")
        rapids = []
        rapids: list[Rapid] = []
        for i in range(len(datapoints)):
            rapid_metadata = []
            if contexts:
                rapid_metadata.append(PromptMetadata(contexts[i]))
            if media_contexts:
                rapid_metadata.append(MediaAssetMetadata(media_contexts[i]))
            rapids.append(
                self.rapid.locate_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    metadata=rapid_metadata,
                    explanation=explanation[i] if explanation != None else None

                )
            )
        
        logger.debug("Submitting locate rapids")
        return self._submit(name=name, rapids=rapids, dimensions=dimensions)
    
    def create_draw_set(self,
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
        if not datapoints:
            raise ValueError("Datapoints cannot be empty")
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
 
        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("The number of media contexts and datapoints must be equal")

        if(explanation and len(explanation) != len(datapoints)):
            raise ValueError("The number of explanations and datapoints must be equal, the index must align, but can be padded with None")

        logger.debug("Creating draw rapids")
        rapids: list[Rapid] = []
        for i in range(len(datapoints)):
            rapid_metadata = []
            if contexts:
                rapid_metadata.append(PromptMetadata(contexts[i]))
            if media_contexts:
                rapid_metadata.append(MediaAssetMetadata(media_contexts[i]))
            rapids.append(
                self.rapid.draw_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    metadata=rapid_metadata,
                    explanation=explanation[i] if explanation != None else None

                )
            )

        logger.debug("Submitting draw rapids")
        return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def create_timestamp_set(self,
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
        if not datapoints:
            raise ValueError("Datapoints cannot be empty")
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
 
        if media_contexts and len(media_contexts) != len(datapoints):
            raise ValueError("The number of media contexts and datapoints must be equal")

        if(explanation and len(explanation) != len(datapoints)):
            raise ValueError("The number of explanations and datapoints must be equal, the index must align, but can be padded with None")
              
        logger.debug("Creating timestamp rapids")
        rapids: list[Rapid] = []
        for i in range(len(datapoints)):
            rapid_metadata = []
            if contexts:
                rapid_metadata.append(PromptMetadata(contexts[i]))
            if media_contexts:
                rapid_metadata.append(MediaAssetMetadata(media_contexts[i]))
            rapids.append(
                self.rapid.timestamp_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    metadata=rapid_metadata,
                    explanation=explanation[i] if explanation != None else None
                )
            )

        logger.debug("Submitting timestamp rapids")
        return self._submit(name=name, rapids=rapids, dimensions=dimensions)
    
    def create_mixed_set(self,
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
        if not rapids:
            raise ValueError("Rapids cannot be empty")

        return self._submit(name=name, rapids=rapids, dimensions=dimensions)

    def _submit(self, name: str, rapids: list[Rapid], dimensions: list[str] | None) -> RapidataValidationSet:
        logger.debug("Creating validation set")
        validation_set_id = (
            self.__openapi_service.validation_api.validation_set_post(
                create_validation_set_model=CreateValidationSetModel(
                    name=name
                )
            )
        ).validation_set_id

        logger.debug(f"Validation set created with ID: {validation_set_id}")

        if validation_set_id is None:
            raise ValueError("Failed to create validation set")

        logger.debug("Creating validation set instance")

        validation_set = RapidataValidationSet(
            name=name,
            validation_set_id=validation_set_id,
            openapi_service=self.__openapi_service
        )

        logger.debug("Adding rapids to validation set")
        failed_rapids = []
        for rapid in tqdm(rapids, desc="Uploading validation tasks", disable=RapidataOutputManager.silent_mode):
            try: 
                validation_set.add_rapid(rapid)
            except Exception:
                failed_rapids.append(rapid.asset)

        if failed_rapids:
            logger.error(f"Failed to add {len(failed_rapids)} datapoints to validation set: {failed_rapids}")
            raise RuntimeError(f"Failed to add {len(failed_rapids)} datapoints to validation set: {failed_rapids}")

        managed_print()
        managed_print(f"Validation set '{name}' created with ID {validation_set_id}\n",
                f"Now viewable under: https://app.{self.__openapi_service.environment}/validation-set/detail/{validation_set_id}",
                sep="")
        
        if dimensions:
            validation_set.update_dimensions(dimensions)
        
        return validation_set
    
    def get_validation_set_by_id(self, validation_set_id: str) -> RapidataValidationSet:
        """Get a validation set by ID.

        Args:
            validation_set_id (str): The ID of the validation set.

        Returns:
            RapidataValidationSet: The ValidationSet instance.
        """
        
        validation_set = self.__openapi_service.validation_api.validation_set_validation_set_id_get(validation_set_id=validation_set_id)
        
        return RapidataValidationSet(validation_set_id, str(validation_set.name), self.__openapi_service)


    def find_validation_sets(self, name: str = "", amount: int = 1) -> list[RapidataValidationSet]:
        """Find validation sets by name.

        Args:
            name (str, optional): The name to search for. Defaults to "" to match with any set.
            amount (int, optional): The amount of validation sets to return. Defaults to 1.

        Returns:
            list[RapidataValidationSet]: The list of validation sets.
        """

        validation_page_result = self.__openapi_service.validation_api.validation_sets_get(QueryModel(
            page=PageInfo(index=1, size=amount),
            filter=RootFilter(filters=[Filter(field="Name", operator="Contains", value=name)]),
            sortCriteria=[SortCriterion(direction="Desc", propertyName="CreatedAt")]
            ))

        validation_sets = [self.get_validation_set_by_id(str(validation_set.id)) for validation_set in validation_page_result.items]
        return validation_sets

