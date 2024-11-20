from rapidata.rapidata_client.assets import MultiAsset, TextAsset, MediaAsset
from rapidata.rapidata_client.metadata import PromptMetadata
from rapidata.rapidata_client.dataset.rapid_builders.rapids import CompareRapid

class CompareRapidBuilder:
    def __init__(self, criteria: str, truth: str, asset: MultiAsset):
        self._criteria = criteria
        self._truth = truth
        self._asset = asset
        self._metadata = []

    def prompt(self, prompt: str):
        self._metadata.append(PromptMetadata(prompt))
        return self

    def build(self):
        return CompareRapid(
            criteria=self._criteria,
            asset=self._asset,
            truth=self._truth,
            metadata=self._metadata
        )

class CompareRapidTruthBuilder:
    def __init__(self, criteria: str, asset: MultiAsset):
        self._criteria = criteria
        self._asset = asset
        self._truth = None
    
    def truth(self, truth: str):
        self._truth = truth
        return self._build()
    
    def _build(self):
        if self._truth is None:
            raise ValueError("Truth is required")
        
        return CompareRapidBuilder(
            criteria=self._criteria,
            asset=self._asset,
            truth=self._truth,
        )

class CompareRapidAssetBuilder:
    def __init__(self, criteria: str):
        self._criteria = criteria
        self._asset: MultiAsset | None = None

    def media(self, medias: list[str]):
        media_assets = [MediaAsset(media) for media in medias]
        self._asset = MultiAsset(media_assets)
        return self._build()
    
    def text(self, texts: list[str]):
        text_assets = [TextAsset(text) for text in texts]
        self._asset = MultiAsset(text_assets)
        return self._build()
    
    def _build(self):
        if self._asset is None:
            raise ValueError("Asset is required")

        return CompareRapidTruthBuilder(
            criteria=self._criteria,
            asset=self._asset,
        )

class CompareRapidCriteriaBuilder:
    def __init__(self):
        self._criteria = None

    def criteria(self, criteria: str):
        self._criteria = criteria
        return self._build()

    def _build(self):
        if self._criteria is None:
            raise ValueError("Criteria is required")

        return CompareRapidAssetBuilder(
            criteria=self._criteria,
        )
