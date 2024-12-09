from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.validation.rapids.rapids import ClassificationRapid, CompareRapid, SelectWordsRapid
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata

from typing import Sequence

class RapidsManager:
    def build_classification_rapid(self,
            question: str,
            options: list[str],
            datapoint: str,
            truths: list[str],
            data_type: str = RapidataDataTypes.MEDIA,
            metadata: Sequence[Metadata] = [],
    ) -> ClassificationRapid:
        
        if data_type == RapidataDataTypes.MEDIA:
            asset = MediaAsset(datapoint)
        elif data_type == RapidataDataTypes.TEXT:
            asset = TextAsset(datapoint)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        return ClassificationRapid(
                question=question,
                options=options,
                asset=asset,
                truths=truths,
                metadata=metadata,
                )
    
    def build_compare_rapid(self,
            criteria: str,
            truth: str,
            datapoint: list[str],
            data_type: str = RapidataDataTypes.MEDIA,
            metadata: Sequence[Metadata] = [],
    ) -> CompareRapid:
        

        if data_type == RapidataDataTypes.MEDIA:
            assets = [MediaAsset(image) for image in datapoint]
        elif data_type == RapidataDataTypes.TEXT:
            assets = [TextAsset(text) for text in datapoint]
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
        asset = MultiAsset(assets)

        return CompareRapid(
                criteria=criteria,
                asset=asset,
                truth=truth,
                metadata=metadata,
                )
    
    def build_select_words_rapid(self,
            instruction: str,
            truths: list[int],
            datapoint: str,
            text: str,
            strict_grading: bool = True,
    ) -> SelectWordsRapid:
        
        asset = MediaAsset(datapoint)

        return SelectWordsRapid(
                instruction=instruction,
                truths=truths,
                asset=asset,
                text=text,
                strict_grading=strict_grading,
                )
        
