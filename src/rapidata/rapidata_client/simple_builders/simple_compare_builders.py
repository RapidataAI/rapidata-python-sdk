from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.metadata import Metadata
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.workflow.compare_workflow import CompareWorkflow
from rapidata.rapidata_client.referee import NaiveReferee, EarlyStoppingReferee
from rapidata.rapidata_client.selection.validation_selection import ValidationSelection
from rapidata.rapidata_client.selection.labeling_selection import LabelingSelection
from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.rapidata_client.assets import MultiAsset, MediaAsset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from typing import Sequence

class CompareOrderBuilder:
    def __init__(self, name:str, criteria: str, media_assets: list[MultiAsset], openapi_service: OpenAPIService):
        self._order_builder = RapidataOrderBuilder(name=name, openapi_service=openapi_service)
        self._name = name
        self._criteria = criteria
        self._media_assets = media_assets
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
    
    def create(self, submit: bool = True, max_upload_workers: int = 10) -> RapidataOrder:
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
        
        order = (self._order_builder
            .workflow(
                CompareWorkflow(
                    criteria=self._criteria
                )
            )
            .referee(referee)
            .media(self._media_assets, metadata=self._metadata)
            .selections(selection)
            .create(submit=submit, max_workers=max_upload_workers))
        
        return order

class CompareMediaBuilder:
    def __init__(self, name: str, criteria: str, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._criteria = criteria
        self._media_assets = []

    def media(self, media_paths: list[list[str]]) -> CompareOrderBuilder:
        """Set the media assets for the comparison order by providing the local paths to the files."""
        if not isinstance(media_paths, list) \
                or not all([isinstance(matchup_paths, list) for matchup_paths in media_paths]) \
                or not all([isinstance(path, str) for matchup_paths in media_paths for path in matchup_paths]):
            raise ValueError("Media paths must be a list of lists. The inner list is a pair of file paths that will be shown together in a matchup.")
        
        invalid_paths = []
        for matchup_idx, matchup_paths in enumerate(media_paths):
            matchup_assets = []
            for path in matchup_paths:
                try:
                    matchup_assets.append(MediaAsset(path=path))
                except FileNotFoundError:
                    invalid_paths.append((matchup_idx, path))
            
            if not invalid_paths:
                self._media_assets.append(MultiAsset(matchup_assets))
                
        if invalid_paths:
            error_msg = "Could not find the following files:\n"
            for matchup_idx, path in invalid_paths:
                error_msg += f"  Matchup {matchup_idx + 1}: {path}\n"
            raise FileNotFoundError(error_msg.rstrip())
        return self._build()
    
    def _build(self) -> CompareOrderBuilder:
        if not self._media_assets:
            raise ValueError("Media paths are required")
        assert all([len(path) == 2 for path in self._media_assets]), "The media paths must come in pairs for comparison tasks."
        return CompareOrderBuilder(self._name, self._criteria, self._media_assets, self._openapi_service)

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

