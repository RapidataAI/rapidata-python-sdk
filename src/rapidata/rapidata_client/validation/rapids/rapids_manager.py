from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.validation.rapids.rapids import (
    ClassificationRapid, 
    CompareRapid, 
    SelectWordsRapid, 
    LocateRapid, 
    DrawRapid,
    TimestampRapid)
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata
from rapidata.rapidata_client.validation.rapids.box import Box

from typing import Sequence

class RapidsManager:
    """
    Can be used to build different types of rapids. That can then be added to Validation sets
    """
    def __init__(self):
        pass
    
    def classification_rapid(self,
            instruction: str,
            answer_options: list[str],
            datapoint: str,
            truths: list[str],
            data_type: str = RapidataDataTypes.MEDIA,
            metadata: Sequence[Metadata] = [],
    ) -> ClassificationRapid:
        """Build a classification rapid
        
        Args:
            instruction (str): The instruction/question to be shown to the labeler.
            answer_options (list[str]): The options that the labeler can choose from to answer the question.
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
                instruction=instruction,
                answer_options=answer_options,
                asset=asset,
                truths=truths,
                metadata=metadata,
                )
    
    def compare_rapid(self,
            instruction: str,
            truth: str,
            datapoint: list[str],
            data_type: str = RapidataDataTypes.MEDIA,
            metadata: Sequence[Metadata] = [],
    ) -> CompareRapid:
        """Build a compare rapid

        Args:
            instruction (str): The instruction that the labeler will be comparing the assets on.
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
                instruction=instruction,
                asset=asset,
                truth=truth,
                metadata=metadata,
                )
    
    def select_words_rapid(self,
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
    
    def locate_rapid(self,
            instruction: str,
            truths: list[Box],
            datapoint: str,
            metadata: Sequence[Metadata] = [],
    ) -> LocateRapid:
        """Build a locate rapid

        Args:
            instruction (str): The instruction on what the labeler should do.
            truths (list[Box]): The bounding boxes of the object that the labeler ought to be locating.
            datapoint (str): The asset that the labeler will be locating the object in.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)

        return LocateRapid(
                instruction=instruction,
                truths=truths,
                asset=asset,
                metadata=metadata,
                )
    
    def draw_rapid(self,
            instruction: str,
            truths: list[Box],
            datapoint: str,
            metadata: Sequence[Metadata] = [],
    ) -> DrawRapid:
        """Build a draw rapid

        Args:
            instruction (str): The instructions on what the labeler
            truths (list[Box]): The bounding boxes of the object that the labeler ought to be drawing.
            datapoint (str): The asset that the labeler will be drawing the object in.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)

        return DrawRapid(
                instruction=instruction,
                truths=truths,
                asset=asset,
                metadata=metadata,
                )
    
    def timestamp_rapid(self,
            instruction: str,
            truths: list[tuple[int, int]],
            datapoint: str,
            metadata: Sequence[Metadata] = []
    ) -> TimestampRapid:
        """Build a timestamp rapid

        Args:
            instruction (str): The instruction for the labeler.
            truths (list[tuple[int, int]]): The possible accepted timestamps intervals for the labeler (in miliseconds).
                The first element of the tuple is the start of the interval and the second element is the end of the interval.
            datapoint (str): The asset that the labeler will be timestamping.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)

        return TimestampRapid(
                instruction=instruction,
                truths=truths,
                asset=asset,
                metadata=metadata,
                )

        
