import os
from rapidata.api_client import AttachCategoryTruth, BoundingBoxTruth, BoxShape, ClassifyPayload, ComparePayload, CompareTruth, LinePayload, LocateBoxTruth, LocatePayload, ScrubPayload, ScrubRange, ScrubTruth, TranscriptionPayload, TranscriptionTruth, TranscriptionWord
from rapidata.rapidata_client.datapoints.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.datapoints.metadata import Metadata
from rapidata.rapidata_client.validation.rapids.box import Box

from typing import Sequence, Literal

from rapidata.rapidata_client.validation.rapids.rapids import Rapid

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
            data_type: Literal["media", "text"] = "media",
            metadata: Sequence[Metadata] = [],
            explanation: str | None = None,
    ) -> Rapid:
        """Build a classification rapid
        
        Args:
            instruction (str): The instruction/question to be shown to the labeler.
            answer_options (list[str]): The options that the labeler can choose from to answer the question.
            datapoint (str): The datapoint that the labeler will be labeling.
            truths (list[str]): The correct answers to the question.
            data_type (str, optional): The type of the datapoint. Defaults to "media" (any form of image, video or audio).
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        if data_type == "media":
            asset = MediaAsset(datapoint)
        elif data_type == "text":
            asset = TextAsset(datapoint)
        else:
            raise ValueError(f"Unsupported data type: {data_type}, must be one of 'media' or 'text'")

        if not isinstance(truths, list):
            raise ValueError("Truths must be a list of strings")
        
        if not all(truth in answer_options for truth in truths):
            raise ValueError("Truths must be part of the answer options")

        payload = ClassifyPayload(
            _t="ClassifyPayload", possibleCategories=answer_options, title=instruction
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        return Rapid(
                asset=asset,
                metadata=metadata,
                explanation=explanation,
                payload=payload,
                truth=model_truth,
                randomCorrectProbability=len(truths) / len(answer_options)
             )
    
    def compare_rapid(self,
            instruction: str,
            truth: str,
            datapoint: list[str],
            data_type: Literal["media", "text"] = "media",
            metadata: Sequence[Metadata] = [],
            explanation: str | None = None,
    ) -> Rapid:
        """Build a compare rapid

        Args:
            instruction (str): The instruction that the labeler will be comparing the assets on.
            truth (str): The correct answer to the comparison. (has to be one of the assets)
            datapoint (list[str]): The two assets that the labeler will be comparing.
            data_type (str, optional): The type of the datapoint. Defaults to "media" (any form of image, video or audio).
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """

        if data_type == "media":
            assets = [MediaAsset(image) for image in datapoint]
        elif data_type == "text":
            assets = [TextAsset(text) for text in datapoint]
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
        asset = MultiAsset(assets)
        
        payload = ComparePayload(_t="ComparePayload", criteria=instruction)
        # take only last part of truth path
        truth = os.path.basename(truth)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(asset) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")


        return Rapid(
                asset=asset,
                truth=model_truth,
                metadata=metadata,
                payload=payload,
                explanation=explanation,
                randomCorrectProbability= 1 / len(asset.assets)
                )
    
    def select_words_rapid(self,
            instruction: str,
            truths: list[int],
            datapoint: str,
            sentence: str,
            required_precision: float = 1,
            required_completeness: float = 1,
            metadata: Sequence[Metadata] = [],
            explanation: str | None = None,
    ) -> Rapid:
        """Build a select words rapid

        Args:
            instruction (str): The instruction for the labeler.
            truths (list[int]): The indices of the words that are the correct answers.
            datapoint (str): The asset that the labeler will be selecting words from.
            sentence (str): The sentence that the labeler will be selecting words from. (split up by spaces)
            required_precision (float): The required precision for the labeler to get the rapid correct (minimum ratio of the words selected that need to be correct). defaults to 1. (no wrong words can be selected)
            required_completeness (float): The required completeness for the labeler to get the rapid correct (miminum ratio of total correct words selected). defaults to 1. (all correct words need to be selected)
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)
        transcription_words = [
            TranscriptionWord(word=word, wordIndex=i)
            for i, word in enumerate(sentence.split(" "))
        ]

        correct_transcription_words: list[TranscriptionWord] = []
        for index in truths:
            correct_transcription_words.append(
                TranscriptionWord(word=transcription_words[index].word, wordIndex=index)
            )

        payload = TranscriptionPayload(
            _t="TranscriptionPayload", title=instruction, transcription=transcription_words
        )

        model_truth = TranscriptionTruth(
            _t="TranscriptionTruth",
            correctWords=correct_transcription_words,
            requiredPrecision=required_precision,
            requiredCompleteness=required_completeness,
        )

        return Rapid(
                payload=payload,
                truth=model_truth,
                asset=asset,
                metadata=metadata,
                explanation=explanation,
                randomCorrectProbability= len(correct_transcription_words) / len(transcription_words)
            )
    
    def locate_rapid(self,
            instruction: str,
            truths: list[Box],
            datapoint: str,
            metadata: Sequence[Metadata] = [],
            explanation: str | None = None,
    ) -> Rapid:
        """Build a locate rapid

        Args:
            instruction (str): The instruction on what the labeler should do.
            truths (list[Box]): The bounding boxes of the object that the labeler ought to be locating.
            datapoint (str): The asset that the labeler will be locating the object in.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)
        payload = LocatePayload(
            _t="LocatePayload", target=instruction
        )

        img_dimensions = asset.get_image_dimension()

        if not img_dimensions:
            raise ValueError("Failed to get image dimensions")

        model_truth = LocateBoxTruth(
            _t="LocateBoxTruth", 
            boundingBoxes=[BoxShape(
                _t="BoxShape",
                xMin=truth.x_min / img_dimensions[0] * 100,
                xMax=truth.x_max / img_dimensions[0] * 100,
                yMax=truth.y_max / img_dimensions[1] * 100,
                yMin=truth.y_min / img_dimensions[1] * 100,
            ) for truth in truths]
        )

        coverage = self._calculate_boxes_coverage(truths, img_dimensions[0], img_dimensions[1])

        return Rapid(
                payload=payload,
                truth=model_truth,
                asset=asset,
                metadata=metadata,
                explanation=explanation,
                randomCorrectProbability=coverage                
                )
    
    def draw_rapid(self,
            instruction: str,
            truths: list[Box],
            datapoint: str,
            metadata: Sequence[Metadata] = [],
            explanation: str | None = None
    ) -> Rapid:
        """Build a draw rapid

        Args:
            instruction (str): The instructions on what the labeler
            truths (list[Box]): The bounding boxes of the object that the labeler ought to be drawing.
            datapoint (str): The asset that the labeler will be drawing the object in.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)

        payload = LinePayload(
            _t="LinePayload", target=instruction
        )

        img_dimensions = asset.get_image_dimension()

        if not img_dimensions:
            raise ValueError("Failed to get image dimensions")

        model_truth = BoundingBoxTruth(
            _t="BoundingBoxTruth", 
            xMax=truths[0].x_max / img_dimensions[0] * 100,
            xMin=truths[0].x_min / img_dimensions[0] * 100,
            yMax=truths[0].y_max / img_dimensions[1] * 100,
            yMin=truths[0].y_min / img_dimensions[1] * 100,
        )

        coverage = self._calculate_boxes_coverage(truths, img_dimensions[0], img_dimensions[1])

        return Rapid(
            payload=payload,
            truth=model_truth,
            asset=asset,
            metadata=metadata,
            explanation=explanation,
            randomCorrectProbability=coverage
        )


    def timestamp_rapid(self,
            instruction: str,
            truths: list[tuple[int, int]],
            datapoint: str,
            metadata: Sequence[Metadata] = [],
            explanation: str | None = None
    ) -> Rapid:
        """Build a timestamp rapid

        Args:
            instruction (str): The instruction for the labeler.
            truths (list[tuple[int, int]]): The possible accepted timestamps intervals for the labeler (in miliseconds).
                The first element of the tuple is the start of the interval and the second element is the end of the interval.
            datapoint (str): The asset that the labeler will be timestamping.
            metadata (Sequence[Metadata], optional): The metadata that is attached to the rapid. Defaults to [].
        """
        
        asset = MediaAsset(datapoint)
        
        for truth in truths:
            if len(truth) != 2:
                raise ValueError("The truths per datapoint must be a tuple of exactly two integers.")
            if truth[0] > truth[1]:
                raise ValueError("The start of the interval must be smaller than the end of the interval.")
        
        payload = ScrubPayload(
            _t="ScrubPayload", 
            target=instruction
        )

        model_truth = ScrubTruth(
            _t="ScrubTruth",
            validRanges=[ScrubRange(
                start=truth[0],
                end=truth[1]
            ) for truth in truths]
        )

        return Rapid(
                payload=payload,
                truth=model_truth,
                asset=asset,
                metadata=metadata,
                explanation=explanation,
                randomCorrectProbability=self._calculate_coverage_ratio(asset.get_duration(), truths),
                )

    def _calculate_boxes_coverage(self, boxes: list[Box], image_width: int, image_height: int) -> float:
        if not boxes:
            return 0.0
        # Convert all coordinates to integers for pixel-wise coverage
        pixels = set()
        for box in boxes:
            for x in range(int(box.x_min), int(box.x_max + 1)):
                for y in range(int(box.y_min), int(box.y_max + 1)):
                    if 0 <= x < image_width and 0 <= y < image_height:
                        pixels.add((x,y))
                        
        total_covered = len(pixels)
        return total_covered / (image_width * image_height)

    def _calculate_coverage_ratio(self, total_duration: int, subsections: list[tuple[int, int]]) -> float:
        """
        Calculate the ratio of total_duration that is covered by subsections, handling overlaps.
        
        Args:
            total_duration: The total duration to consider
            subsections: List of tuples containing (start, end) times
            
        Returns:
            float: Ratio of coverage (0 to 1)
        """
        if not subsections:
            return 0.0
        
        # Sort subsections by start time and clamp to valid range
        sorted_ranges = sorted(
            (max(0, start), min(end, total_duration)) 
            for start, end in subsections
        )
        
        # Merge overlapping ranges
        merged_ranges = []
        current_range = list(sorted_ranges[0])
        
        for next_start, next_end in sorted_ranges[1:]:
            current_start, current_end = current_range
            
            # If ranges overlap or are adjacent
            if next_start <= current_end:
                current_range[1] = max(current_end, next_end)
            else:
                merged_ranges.append(current_range)
                current_range = [next_start, next_end]
        
        merged_ranges.append(current_range)
        
        # Calculate total coverage
        total_coverage = sum(end - start for start, end in merged_ranges)
        
        return total_coverage / total_duration
