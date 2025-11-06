import os
from rapidata.api_client import (
    AttachCategoryTruth,
    BoundingBoxTruth,
    ClassifyPayload,
    ComparePayload,
    CompareTruth,
    LinePayload,
    LocateBoxTruth,
    LocatePayload,
    ScrubPayload,
    ScrubRange,
    ScrubTruth,
    TranscriptionPayload,
    TranscriptionTruth,
    TranscriptionWord,
)
from rapidata.rapidata_client.validation.rapids.box import Box
from rapidata.api_client.models.classify_payload_category import ClassifyPayloadCategory
from typing import Literal

from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.service.openapi_service import OpenAPIService


class RapidsManager:
    """
    Can be used to build different types of rapids. That can then be added to Validation sets
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def classification_rapid(
        self,
        instruction: str,
        answer_options: list[str],
        datapoint: str,
        truths: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> Rapid:
        """Build a classification rapid

        Args:
            instruction (str): The instruction/question to be shown to the labeler.
            answer_options (list[str]): The options that the labeler can choose from to answer the question.
            datapoint (str): The datapoint that the labeler will be labeling.
            truths (list[str]): The correct answers to the question.
            data_type (str, optional): The type of the datapoint. Defaults to "media" (any form of image, video or audio).
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """
        if not isinstance(truths, list):
            raise ValueError("Truths must be a list of strings")

        if not all(truth in answer_options for truth in truths):
            raise ValueError("Truths must be part of the answer options")

        payload = ClassifyPayload(
            _t="ClassifyPayload",
            categories=[
                ClassifyPayloadCategory(label=option, value=option)
                for option in answer_options
            ],
            title=instruction,
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        return Rapid(
            asset=datapoint,
            data_type=data_type,
            context=context,
            media_context=media_context,
            explanation=explanation,
            payload=payload,
            truth=model_truth,
            random_correct_probability=len(truths) / len(answer_options),
        )

    def compare_rapid(
        self,
        instruction: str,
        truth: str,
        datapoint: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> Rapid:
        """Build a compare rapid

        Args:
            instruction (str): The instruction that the labeler will be comparing the assets on.
            truth (str): The correct answer to the comparison. (has to be one of the assets)
            datapoint (list[str]): The two assets that the labeler will be comparing.
            data_type (str, optional): The type of the datapoint. Defaults to "media" (any form of image, video or audio).
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """

        payload = ComparePayload(_t="ComparePayload", criteria=instruction)
        truth = os.path.basename(truth)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(datapoint) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        return Rapid(
            asset=datapoint,
            data_type=data_type,
            truth=model_truth,
            context=context,
            media_context=media_context,
            payload=payload,
            explanation=explanation,
            random_correct_probability=0.5,
        )

    def select_words_rapid(
        self,
        instruction: str,
        truths: list[int],
        datapoint: str,
        sentence: str,
        required_precision: float = 1,
        required_completeness: float = 1,
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
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """

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
            _t="TranscriptionPayload",
            title=instruction,
            transcription=transcription_words,
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
            asset=datapoint,
            sentence=sentence,
            explanation=explanation,
            random_correct_probability=len(correct_transcription_words)
            / len(transcription_words),
        )

    def locate_rapid(
        self,
        instruction: str,
        truths: list[Box],
        datapoint: str,
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> Rapid:
        """Build a locate rapid

        Args:
            instruction (str): The instruction on what the labeler should do.
            truths (list[Box]): The bounding boxes of the object that the labeler ought to be locating.
            datapoint (str): The asset that the labeler will be locating the object in.
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """

        payload = LocatePayload(_t="LocatePayload", target=instruction)

        model_truth = LocateBoxTruth(
            _t="LocateBoxTruth",
            boundingBoxes=[truth.to_model() for truth in truths],
        )

        coverage = self._calculate_boxes_coverage(
            truths,
        )

        return Rapid(
            payload=payload,
            truth=model_truth,
            asset=datapoint,
            context=context,
            media_context=media_context,
            explanation=explanation,
            random_correct_probability=coverage,
        )

    def draw_rapid(
        self,
        instruction: str,
        truths: list[Box],
        datapoint: str,
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> Rapid:
        """Build a draw rapid

        Args:
            instruction (str): The instructions on what the labeler
            truths (list[Box]): The bounding boxes of the object that the labeler ought to be drawing.
            datapoint (str): The asset that the labeler will be drawing the object in.
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """

        payload = LinePayload(_t="LinePayload", target=instruction)

        model_truth = BoundingBoxTruth(
            _t="BoundingBoxTruth",
            xMax=truths[0].x_max * 100,
            xMin=truths[0].x_min * 100,
            yMax=truths[0].y_max * 100,
            yMin=truths[0].y_min * 100,
        )

        coverage = self._calculate_boxes_coverage(
            truths,
        )

        return Rapid(
            payload=payload,
            truth=model_truth,
            asset=datapoint,
            context=context,
            media_context=media_context,
            explanation=explanation,
            random_correct_probability=coverage,
        )

    def timestamp_rapid(
        self,
        instruction: str,
        truths: list[tuple[int, int]],
        datapoint: str,
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> Rapid:
        """Build a timestamp rapid

        Args:
            instruction (str): The instruction for the labeler.
            truths (list[tuple[int, int]]): The possible accepted timestamps intervals for the labeler (in miliseconds).
                The first element of the tuple is the start of the interval and the second element is the end of the interval.
            datapoint (str): The asset that the labeler will be timestamping.
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """

        for truth in truths:
            if len(truth) != 2:
                raise ValueError(
                    "The truths per datapoint must be a tuple of exactly two integers."
                )
            if truth[0] > truth[1]:
                raise ValueError(
                    "The start of the interval must be smaller than the end of the interval."
                )

        payload = ScrubPayload(_t="ScrubPayload", target=instruction)

        model_truth = ScrubTruth(
            _t="ScrubTruth",
            validRanges=[ScrubRange(start=truth[0], end=truth[1]) for truth in truths],
        )

        return Rapid(
            payload=payload,
            truth=model_truth,
            asset=datapoint,
            context=context,
            media_context=media_context,
            explanation=explanation,
            random_correct_probability=0.5,  # TODO: implement coverage ratio
        )

    def _calculate_boxes_coverage(self, boxes: list[Box]) -> float:
        """
        Calculate the ratio of area covered by a list of boxes.

        Args:
            boxes: List of Box objects with coordinates in range [0, 1]

        Returns:
            float: Coverage ratio between 0.0 and 1.0
        """
        if not boxes:
            return 0.0

        # Convert boxes to intervals for sweep line algorithm
        events = []

        # Create events for x-coordinates
        for i, box in enumerate(boxes):
            events.append((box.x_min, "start", i, box))
            events.append((box.x_max, "end", i, box))

        # Sort events by x-coordinate
        events.sort(key=lambda x: (x[0], x[1] == "end"))

        total_area = 0.0
        active_boxes = set()
        prev_x = 0.0

        for x, event_type, box_id, box in events:
            # Calculate area for the previous x-interval
            if active_boxes and x > prev_x:
                # Merge y-intervals for active boxes
                y_intervals = [(boxes[i].y_min, boxes[i].y_max) for i in active_boxes]
                y_intervals.sort()

                # Merge overlapping y-intervals
                merged_intervals = []
                for start, end in y_intervals:
                    if merged_intervals and start <= merged_intervals[-1][1]:
                        # Overlapping intervals - merge them
                        merged_intervals[-1] = (
                            merged_intervals[-1][0],
                            max(merged_intervals[-1][1], end),
                        )
                    else:
                        # Non-overlapping interval
                        merged_intervals.append((start, end))

                # Calculate total y-coverage for this x-interval
                y_coverage = sum(end - start for start, end in merged_intervals)
                total_area += (x - prev_x) * y_coverage

            # Update active boxes
            if event_type == "start":
                active_boxes.add(box_id)
            else:
                active_boxes.discard(box_id)

            prev_x = x

        return total_area

    @staticmethod
    def _calculate_coverage_ratio(
        total_duration: int, subsections: list[tuple[int, int]]
    ) -> float:
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
            (max(0, start), min(end, total_duration)) for start, end in subsections
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

    def __str__(self) -> str:
        return "RapidsManager"

    def __repr__(self) -> str:
        return self.__str__()
