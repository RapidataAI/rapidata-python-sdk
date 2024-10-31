from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.referee.early_stopping_referee import EarlyStoppingReferee
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.workflow.classify_workflow import ClassifyWorkflow
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset
from typing import Sequence

class ClassificationOrderBuilder:
    def __init__(self, name: str, question: str, options: list[str], media_paths: list[str], openapi_service: OpenAPIService):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._question = question
        self._options = options
        self._media_paths = media_paths
        self._responses_required = 10
        self._probability_threshold = None
        self._metadata = None
        self._validation_set_id = None

    def metadata(self, metadata: Sequence[Metadata]):
        """Set the metadata for the classification order. Has to be the same lenght as the media paths."""
        self._metadata = metadata
        return self

    def responses(self, responses_required: int):
        """Set the number of responses required for the classification order."""
        self._responses_required = responses_required
        return self

    def probability_threshold(self, probability_threshold: float):
        """Set the probability threshold for early stopping."""
        self._probability_threshold = probability_threshold
        return self

    def validation_set_id(self, validation_set_id: str):
        """Set the validation set ID for the classification order."""
        self._validation_set_id = validation_set_id
        return self

    def create(self, submit: bool = True, max_upload_workers: int = 10):
        if self._probability_threshold and self._responses_required:
            referee = EarlyStoppingReferee(
                max_vote_count=self._responses_required,
                threshold=self._probability_threshold
            )

        else:
            referee = NaiveReferee(responses=self._responses_required)

        assets = [MediaAsset(path=media_path) for media_path in self._media_paths]

        selection: list[Selection] = ([ValidationSelection(amount=1, validation_set_id=self._validation_set_id), LabelingSelection(amount=2)] 
                     if self._validation_set_id 
                     else [LabelingSelection(amount=3)])

        order = (self._order_builder
            .workflow(
                ClassifyWorkflow(
                    question=self._question,
                    options=self._options
                )
            )
            .referee(referee)
            .media(assets, metadata=self._metadata) # type: ignore
            .selections(selection)
            .create(submit=submit, max_workers=max_upload_workers))

        return order 


class ClassificationMediaBuilder:
    "test"
    def __init__(self, name: str, question: str, options: list[str], openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._question = question
        self._options = options
        self._media_paths = None

    def media(self, media_paths: list[str]) -> ClassificationOrderBuilder:
        """Set the media assets for the classification order by providing the local paths to the files."""
        self._media_paths = media_paths
        return self._build()

    def _build(self) -> ClassificationOrderBuilder:
        if self._media_paths is None:
            raise ValueError("Media paths are required")
        return ClassificationOrderBuilder(self._name, self._question, self._options, self._media_paths, openapi_service=self._openapi_service)


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
