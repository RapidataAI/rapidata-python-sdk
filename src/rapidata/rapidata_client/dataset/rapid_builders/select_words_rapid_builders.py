from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.dataset.rapid_builders.rapids import SelectWordsRapid

class SelectWordsRapidBuilder:
    """Final builder class for rapid.
    
    This class handles the final construction of a rapid with all required parameters.
    """
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, text: str):
        self._instruction = instruction
        self._truths = truths
        self._asset = asset
        self._text = text
        self._strict_grading = True

    def strict_grading(self, strict_grading: bool = True):
        """Set whether to use strict grading for the select words.
        Strict grading true: In order to be correct, you must select all of the right words
        Strict grading false: In order to be correct, you must select at least one right word
        In both cases it will be incorrect if you select any wrong words
        
        Args:
            strict_grading (bool): Whether to use strict grading. Defaults to True."""
        self._strict_grading = strict_grading
        return self

    def build(self):
        """Constructs and returns the final rapid."""
        return SelectWordsRapid(
            instruction=self._instruction,
            truths=self._truths,
            asset=self._asset,
            text=self._text,
            strict_grading=self._strict_grading
        )

class SelectWordsRapidTruthsBuilder:
    """Builder class for the truths of the rapid.

    This adds the truths to the rapid.
    """
    def __init__(self, instruction: str, media: MediaAsset, text: str):
        self._instruction = instruction
        self._media = media
        self._text = text
        self._truths = None

    def truths(self, truths: list[int]):
        """Set the truths for the rapid.

        Args:
            truths (list[int]): The correct answers for the task. \
                Each integer represents the index of the correct word in the text."""
        
        if not isinstance(truths, list) or not all(isinstance(truth, int) for truth in truths):
            raise ValueError("Truths must be a list of integers")
        
        self._truths = truths
        return self._build()
    
    def _build(self):
        if self._truths is None:
            raise ValueError("Truths are required")
        
        return SelectWordsRapidBuilder(
            instruction=self._instruction,
            truths=self._truths,
            asset=self._media,
            text=self._text
        )

class SelectWordsRapidAssetBuilder:
    """Builder class for the asset of the rapid.

    This adds the asset to the rapid.
    """
    def __init__(self, instruction: str):
        self._instruction = instruction

    def media(self, media: str, text: str):
        """Set the media asset for the rapid.

        Args:
            media (str): The local path (image, video, audio) or URL (image) of the media asset.
            text (str): The text will be split up by spaces and the labeler will be able to select the words"""
        
        self._asset = MediaAsset(media)
        self._text = text

        return self._build()

    def _build(self):
        if not self._asset:
            raise ValueError("Media is required")
        
        return SelectWordsRapidTruthsBuilder(
            instruction=self._instruction,
            media=self._asset,
            text=self._text
        )

class SelectWordsRapidInstructionBuilder:
    def __init__(self):
        self._instruction = None

    def instruction(self, instruction: str):
        """Set the instruction for the rapid.

        Args:
            instruction (str): The instruction for the task"""
        
        if not isinstance(instruction, str):
            raise ValueError("Instruction must be a string")
        
        self._instruction = instruction
        return self._build()
    
    def _build(self):
        if self._instruction is None:
            raise ValueError("Instruction is required")
        
        return SelectWordsRapidAssetBuilder(
            instruction=self._instruction,
        )
