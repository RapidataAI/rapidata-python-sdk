from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.metadata import Metadata
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.workflow.compare_workflow import CompareWorkflow
from rapidata.rapidata_client.referee import NaiveReferee, EarlyStoppingReferee
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.assets import MultiAsset, MediaAsset
from typing import Sequence

class CompareOrderBuilder:
    def __init__(self, name:str, criteria: str, media_paths: list[list[str]], openapi_service: OpenAPIService):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._name = name
        self._criteria = criteria
        self._media_paths = media_paths
        self._responses_required = 10
        self._metadata = None
        self._validation_set_id = None
        self._probability_threshold = None

    def responses(self, responses_required: int) -> 'CompareOrderBuilder':
        """Set the number of resoonses required per matchup/pairing for the comparison order."""
        self._responses_required = responses_required
        return self
    
    def metadata(self, metadata: Sequence[Metadata]) -> 'CompareOrderBuilder':
        """Set the metadata for the comparison order. Has to be the same shape as the media paths."""
        self._metadata = metadata
        return self
    
    def validation_set_id(self, validation_set_id: str) -> 'CompareOrderBuilder':
        """Set the validation set ID for the comparison order."""
        self._validation_set_id = validation_set_id
        return self
    
    def probability_threshold(self, probability_threshold: float) -> 'CompareOrderBuilder':
        """Set the probability threshold for early stopping."""
        self._probability_threshold = probability_threshold
        return self
    
    def create(self, submit: bool = True, max_upload_workers: int = 10):
        if self._probability_threshold and self._responses_required:
            referee = EarlyStoppingReferee(
                max_vote_count=self._responses_required,
                threshold=self._probability_threshold
            )

        else:
            referee = NaiveReferee(responses=self._responses_required)
        selection: list[Selection] = ([ValidationSelection(amount=1, validation_set_id=self._validation_set_id), LabelingSelection(amount=2)] 
                     if self._validation_set_id 
                     else [LabelingSelection(amount=3)])
        
        media_paths = [MultiAsset([MediaAsset(path=path) for path in paths]) for paths in self._media_paths]
        order = (self._order_builder
            .workflow(
                CompareWorkflow(
                    criteria=self._criteria
                )
            )
            .referee(referee)
            .media(media_paths, metadata=self._metadata) # type: ignore
            .selections(selection)
            .create(submit=submit, max_workers=max_upload_workers))
        
        return order

class CompareMediaBuilder:
    def __init__(self, name: str, criteria: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._criteria = criteria
        self._media_paths = None

    def media(self, media_paths: list[list[str]]) -> CompareOrderBuilder:
        """Set the media assets for the comparison order by providing the local paths to the files."""
        self._media_paths = media_paths
        return self._build()
    
    def _build(self) -> CompareOrderBuilder:
        if self._media_paths is None:
            raise ValueError("Media paths are required")
        assert all([len(path) == 2 for path in self._media_paths]), "The media paths must come in pairs for comparison tasks."
        return CompareOrderBuilder(self._name, self._criteria, self._media_paths, self._openapi_service)

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

