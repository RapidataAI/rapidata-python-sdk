from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.dataset.rapid_builders.rapids import TranscriptionRapid

class TranscriptionRapidBuilder:
    """Final builder class for transcription rapid.
    
    This class handles the final construction of a transcription rapid with all required parameters.
    """
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, transcription_text: str):
        self._instruction = instruction
        self._truths = truths
        self._asset = asset
        self._transcription_text = transcription_text
        self._strict_grading = True

    def strict_grading(self, strict_grading: bool = True):
        """Set whether to use strict grading for the transcription.
        Strict grading true: In order to be correct, you must select all of the right words
        Strict grading false: In order to be correct, you must select at least one right word
        In both cases it will be incorrect if you select any wrong words
        
        Args:
            strict_grading (bool): Whether to use strict grading. Defaults to True.
            
        Returns:
            TranscriptionRapidBuilder: The builder instance for method chaining
        """
        self._strict_grading = strict_grading
        return self

    def build(self):
        """Constructs and returns the final transcription rapid.
        
        Returns:
            TranscriptionRapid: The constructed transcription rapid
        """
        return TranscriptionRapid(
            instruction=self._instruction,
            truths=self._truths,
            asset=self._asset,
            transcription=self._transcription_text,
            strict_grading=self._strict_grading
        )

class TranscriptionRapidTruthsBuilder:
    """Builder class for the truths of the transcription rapid.

    This adds the truths to the transcription rapid.
    """
    def __init__(self, instruction: str, media: MediaAsset, transcription_text: str):
        self._instruction = instruction
        self._media = media
        self._transcription_text = transcription_text
        self._truths = None

    def truths(self, truths: list[int]):
        """Set the truths for the transcription rapid.

        Args:
            truths (list[int]): The correct answers for the transcription task. \
                Each integer represents the index of the correct word in the transcription text."""
        
        if not isinstance(truths, list) or not all(isinstance(truth, int) for truth in truths):
            raise ValueError("Truths must be a list of integers")
        
        self._truths = truths
        return self._build()
    
    def _build(self):
        if self._truths is None:
            raise ValueError("Truths are required")
        
        return TranscriptionRapidBuilder(
            instruction=self._instruction,
            truths=self._truths,
            asset=self._media,
            transcription_text=self._transcription_text
        )

class TranscriptionRapidAssetBuilder:
    """Builder class for the asset of the transcription rapid.

    This adds the asset to the transcription rapid.
    """
    def __init__(self, instruction: str):
        self._instruction = instruction

    def media(self, media: str, transcription_text: str):
        """Set the media asset for the transcription rapid.

        Args:
            media (str): The local file path of the audio or video file to be transcribed 
            transcription_text (str): The text to be transcribed from the media asset""" # is video file okay?
        
        self._asset = MediaAsset(media)
        self._transcription_text = transcription_text

        return self._build()

    def _build(self):
        if not self._asset:
            raise ValueError("Media is required")
        
        return TranscriptionRapidTruthsBuilder(
            instruction=self._instruction,
            media=self._asset,
            transcription_text=self._transcription_text
        )

class TranscriptionRapidInstructionBuilder:
    def __init__(self):
        self._instruction = None

    def instruction(self, instruction: str):
        """Set the instruction for the transcription rapid.

        Args:
            instruction (str): The instruction for the transcription task"""
        
        if not isinstance(instruction, str):
            raise ValueError("Instruction must be a string")
        
        self._instruction = instruction
        return self._build()
    
    def _build(self):
        if self._instruction is None:
            raise ValueError("Instruction is required")
        
        return TranscriptionRapidAssetBuilder(
            instruction=self._instruction,
        )
