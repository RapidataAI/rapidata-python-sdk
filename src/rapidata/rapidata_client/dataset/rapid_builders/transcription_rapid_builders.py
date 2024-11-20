from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.dataset.rapid_builders.rapids import TranscriptionRapid

class TranscriptionRapidBuilder:
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, transcription_text: str):
        self._instruction = instruction
        self._truths = truths
        self._asset = asset
        self._transcription_text = transcription_text
        self._strict_grading = True

    def strict_grading(self, strict_grading: bool):
        self._strict_grading = strict_grading
        return self

    def build(self):
        return TranscriptionRapid(
            instruction=self._instruction,
            truths=self._truths,
            asset=self._asset,
            transcription=self._transcription_text,
            strict_grading=self._strict_grading
        )

class TranscriptionRapidTruthsBuilder:
    def __init__(self, instruction: str, media: MediaAsset, transcription_text: str):
        self._instruction = instruction
        self._media = media
        self._transcription_text = transcription_text
        self._truths = None

    def truths(self, truths: list[int]):
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
    def __init__(self, instruction: str):
        self._instruction = instruction

    def media(self, media: str, transcription_text: str):
        if not isinstance(media, str):
            raise ValueError("Media must be a local file path as a string")
        
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
        self._instruction = instruction
        return self._build()
    
    def _build(self):
        if self._instruction is None:
            raise ValueError("Instruction is required")
        
        return TranscriptionRapidAssetBuilder(
            instruction=self._instruction,
        )
