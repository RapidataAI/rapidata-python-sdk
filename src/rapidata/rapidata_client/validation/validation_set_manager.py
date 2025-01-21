from rapidata.rapidata_client.validation._validation_set_builder import ValidationSetBuilder
from rapidata.rapidata_client.validation.rapidata_validation_set import RapidataValidationSet
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.validation.rapids.rapids_manager import RapidsManager
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.rapidata_client.metadata import PromptMetadata

from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion
from rapidata.api_client.exceptions import BadRequestException
from urllib3._collections import HTTPHeaderDict

from rapidata.rapidata_client.validation.rapids.box import Box

from rapidata.api_client.models.query_validation_set_model import QueryValidationSetModel

from typing import Sequence


class ValidationSetManager:
    """
    Responsible for everything related to validation sets. From creation to retrieval.

    Attributes:
        rapid (RapidsManager): The RapidsManager instance.
    """
    def __init__(self, openapi_service: OpenAPIService) -> None:
        self.__openapi_service = openapi_service
        self.rapid = RapidsManager()

    def create_classification_set(self,
        name: str,
        instruction: str,
        answer_options: list[str],
        datapoints: list[str],
        truths: list[list[str]],
        data_type: str = RapidataDataTypes.MEDIA,
        contexts: list[str] | None = None,
        print_confirmation: bool = True
    ) -> RapidataValidationSet:
        """Create a classification validation set.
        
        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction by which the labeler will answer.
            answer_options (list[str]): The options to choose from when answering.
            datapoints (list[str]): The datapoints that will be used for validation.
            truths (list[list[str]]): The truths for each datapoint. Outher list is for each datapoint, inner list is for each truth.\n
                example:
                    options: ["yes", "no", "maybe"]
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [["yes"], ["no", "maybe"]] -> first datapoint correct answer is "yes", second datapoint is "no" or "maybe"
            data_type (str, optional): The type of data. Defaults to RapidataDataTypes.MEDIA. Other option: RapidataDataTypes.TEXT ("text").
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and answer options. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
        """
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
        
        rapids = []
        for i in range(len(datapoints)):
            rapids.append(
                self.rapid.classification_rapid(
                    instruction=instruction,
                    answer_options=answer_options,
                    datapoint=datapoints[i],
                    truths=truths[i],
                    data_type=data_type,
                    metadata=[PromptMetadata(contexts[i])] if contexts else []
                )
            )

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    
    def create_compare_set(self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        truths: list[str],
        data_type: str = RapidataDataTypes.MEDIA,
        contexts: list[str] | None = None,
        print_confirmation: bool = True
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
            data_type (str, optional): The type of data. Defaults to RapidataDataTypes.MEDIA. Other option: RapidataDataTypes.TEXT ("text").
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.\n
                If provided has to be the same length as datapoints and will be shown in addition to the instruction and truth. (Therefore will be different for each datapoint)
                Will be match up with the datapoints using the list index.
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
        """
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, str) for truth in truths]):
            raise ValueError("Truths must be a list of strings")

        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
        
        rapids = []
        for i in range(len(datapoints)):
            rapids.append(
                self.rapid.compare_rapid(
                    instruction=instruction,
                    truth=truths[i],
                    datapoint=datapoints[i],
                    data_type=data_type,
                    metadata=[PromptMetadata(contexts[i])] if contexts else []
                )
            )

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    
    def create_select_words_set(self,
        name: str,
        instruction: str,
        truths: list[list[int]],
        datapoints: list[str],
        sentences: list[str],
        strict_grading: bool = True,
        print_confirmation: bool = True
    ) -> RapidataValidationSet:
        """Create a select words validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[int]]): The truths for each datapoint. Outher list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    sentences: ["this example 1", "this example 2"]
                    truths: [[0, 1], [2]] -> first datapoint correct words are "this" and "example", second datapoint is "2"
            datapoints (list[str]): The datapoints that will be used for validation.
            sentences (list[str]): The sentences that will be used for validation. The sentece will be split up by spaces to be selected by the labeler.
                Must be the same length as datapoints.
            strict_grading (bool, optional): Whether to grade strictly. Defaults to True.\n
                If True, the labeler must select all correct words to be graded as correct. (and no wrong words)
                If False, the labeler must select at least one correct word to be graded as correct. (and no wrong words)
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
            """
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")

        if len(datapoints) != len(truths) or len(datapoints) != len(sentences):
            raise ValueError("The number of datapoints, truths, and sentences must be equal")
        
        rapids = []
        for i in range(len(datapoints)):
            rapids.append(
                self.rapid.select_words_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    sentence=sentences[i],
                    strict_grading=strict_grading
                )
            )

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    
    def create_locate_set(self,
        name: str,
        instruction: str,
        truths: list[list[Box]],
        datapoints: list[str],
        contexts: list[str] | None = None,
        print_confirmation: bool = True
    ) -> RapidataValidationSet:
        """Create a locate validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[Box]]): The truths for each datapoint. Outher list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [[Box(0, 0, 100, 100)], [Box(50, 50, 150, 150)]] -> first datapoint the object is in the top left corner, second datapoint the object is in the center
            datapoints (list[str]): The datapoints that will be used for validation.
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
        """
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
        
        rapids = []
        for i in range(len(datapoints)):
            rapids.append(
                self.rapid.locate_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    metadata=[PromptMetadata(contexts[i])] if contexts else []
                )
            )

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    
    def create_draw_set(self,
        name: str,
        instruction: str,
        truths: list[list[Box]],
        datapoints: list[str],
        contexts: list[str] | None = None,
        print_confirmation: bool = True
    ) -> RapidataValidationSet:
        """Create a draw validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[Box]]): The truths for each datapoint. Outher list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [[Box(0, 0, 100, 100)], [Box(50, 50, 150, 150)]] -> first datapoint the object is in the top left corner, second datapoint the object is in the center
            datapoints (list[str]): The datapoints that will be used for validation.
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
        """
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
        
        rapids = []
        for i in range(len(datapoints)):
            rapids.append(
                self.rapid.draw_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    metadata=[PromptMetadata(contexts[i])] if contexts else []
                )
            )

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    

    def create_timestamp_set(self,
        name: str,
        instruction: str,
        truths: list[list[tuple[int, int]]],
        datapoints: list[str],
        contexts: list[str] | None = None,
        print_confirmation: bool = True
    ) -> RapidataValidationSet:
        """Create a timestamp validation set.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            instruction (str): The instruction to show to the labeler.
            truths (list[list[tuple[int, int]]]): The truths for each datapoint defined as start and endpoint based on miliseconds. 
            Outher list is for each datapoint, inner list is for each truth.\n
                example:
                    datapoints: ["datapoint1", "datapoint2"]
                    truths: [[(0, 10)], [(20, 30)]] -> first datapoint the correct interval is from 0 to 10, second datapoint the correct interval is from 20 to 30
            datapoints (list[str]): The datapoints that will be used for validation.
            contexts (list[str], optional): The contexts for each datapoint. Defaults to None.
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
        """
        
        if len(datapoints) != len(truths):
            raise ValueError("The number of datapoints and truths must be equal")
        
        if not all([isinstance(truth, (list, tuple)) for truth in truths]):
            raise ValueError("Truths must be a list of lists or tuples")
        
        if contexts and len(contexts) != len(datapoints):
            raise ValueError("The number of contexts and datapoints must be equal")
        
        rapids = []
        for i in range(len(datapoints)):
            rapids.append(
                self.rapid.timestamp_rapid(
                    instruction=instruction,
                    truths=truths[i],
                    datapoint=datapoints[i],
                    metadata=[PromptMetadata(contexts[i])] if contexts else []
                )
            )

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    
    def create_mixed_set(self,
        name: str,
        rapids: Sequence[Rapid],
        print_confirmation: bool = True
    ) -> RapidataValidationSet:
        """Create a validation set with a list of rapids.

        Args:
            name (str): The name of the validation set. (will not be shown to the labeler)
            rapids (Sequence[Rapid]): The list of rapids to add to the validation set.
            print_confirmation (bool, optional): Whether to print a confirmation message that validation set has been created. Defaults to True.
        """

        validation_set_builder = ValidationSetBuilder(name, self.__openapi_service)
        for rapid in rapids:
            validation_set_builder._add_rapid(rapid)

        return validation_set_builder._submit(print_confirmation)
    
    def get_validation_set_by_id(self, validation_set_id: str) -> RapidataValidationSet:
        """Get a validation set by ID.

        Args:
            validation_set_id (str): The ID of the validation set.

        Returns:
            RapidataValidationSet: The ValidationSet instance.
        """
        try:
            validation_set = self.__openapi_service.validation_api.validation_get_by_id_get(id=validation_set_id)
        except Exception:
            raise ValueError(f"ValidationSet with ID {validation_set_id} not found.")
        
        return RapidataValidationSet(validation_set_id, self.__openapi_service, validation_set.name)
    
    def find_validation_sets(self, name: str = "", amount: int = 1) -> list[RapidataValidationSet]:
        """Find validation sets by name.

        Args:
            name (str, optional): The name to search for. Defaults to "" to match with any set.
            amount (int, optional): The amount of validation sets to return. Defaults to 1.

        Returns:
            list[RapidataValidationSet]: The list of validation sets.
        """
        try:
            validation_page_result = self.__openapi_service.validation_api.validation_query_validation_sets_get(QueryValidationSetModel(
                pageInfo=PageInfo(index=1, size=amount),
                filter=RootFilter(filters=[Filter(field="Name", operator="Contains", value=name)]),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="CreatedAt")]
                ))

        except BadRequestException as e:
            raise ValueError(f"Error occured during request. \nError: {e.body} \nTraceid: {e.headers.get('X-Trace-Id') if isinstance(e.headers, HTTPHeaderDict) else 'Unknown'}")

        except Exception as e:
            raise ValueError(f"Unknown error occured: {e}")

        validation_sets = [self.get_validation_set_by_id(validation_set.id) for validation_set in validation_page_result.items]
        return validation_sets

