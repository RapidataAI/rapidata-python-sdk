from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.validation.rapids.rapids import ClassificationRapid, CompareRapid, SelectWordsRapid
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata

from typing import Sequence

class RapidsManager:
    """RapidsManager Class
    
    Can be used to build different types of rapids. That can then be added to Validation sets"""
    def __init__(self):
        pass
    
    def build_classification_rapid(self,
            question: str,
            options: list[str],
            datapoint: str,
            truths: list[str],
            data_type: str = RapidataDataTypes.MEDIA,
            metadata: Sequence[Metadata] = [],
    ) -> ClassificationRapid:
        """Build a classification rapid
        
        Args:
            question (str): The question to be asked to the labeler.
            options (list[str]): The options that the labeler can choose from.
            datapoint (str): The datapoint that the labeler will be labeling.
            truths (list[str]): The correct answers to the question.
            data_type (str, optional): The type of the datapoint. Defaults to RapidataDataTypes.MEDIA.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
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
        """Build a compare rapid

        Args:
            criteria (str): The criteria that the labeler will be comparing the assets on.
            truth (str): The correct answer to the comparison. (has to be one of the assets)
            datapoint (list[str]): The two assets that the labeler will be comparing.
            data_type (str, optional): The type of the datapoint. Defaults to RapidataDataTypes.MEDIA.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """

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
            sentence: str,
            strict_grading: bool = True,
    ) -> SelectWordsRapid:
        """Build a select words rapid

        Args:
            instruction (str): The instruction for the labeler.
            truths (list[int]): The indices of the words that are the correct answers.
            datapoint (str): The asset that the labeler will be selecting words from.
            sentence (str): The sentence that the labeler will be selecting words from. (split up by spaces)
            strict_grading (bool, optional): Whether the grading should be strict or not. 
                True means that all correct words and no wrong words have to be selected for the rapid to be marked as correct.
                False means that at least one correct word and no wrong words have to be selected for the rapid to be marked as correct. Defaults to True.
        """
        
        asset = MediaAsset(datapoint)

        return SelectWordsRapid(
                instruction=instruction,
                truths=truths,
                asset=asset,
                sentence=sentence,
                strict_grading=strict_grading,
                )
        
