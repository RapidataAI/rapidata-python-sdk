from typing import Sequence, cast
from rapidata.rapidata_client.datapoints.assets import (
    MediaAsset,
    TextAsset,
    MultiAsset,
    BaseAsset,
)
from rapidata.rapidata_client.datapoints.assets.constants import (
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_AUDIO_EXTENSIONS,
)
from rapidata.rapidata_client.datapoints.metadata import Metadata
from rapidata.api_client.models.dataset_dataset_id_datapoints_post_request_metadata_inner import (
    DatasetDatasetIdDatapointsPostRequestMetadataInner,
)
from rapidata.api_client.models.create_datapoint_from_text_sources_model import (
    CreateDatapointFromTextSourcesModel,
)
from pydantic import StrictStr, StrictBytes
from rapidata.api_client.models.asset_type import AssetType
from rapidata.api_client.models.prompt_type import PromptType
from rapidata.rapidata_client.datapoints.metadata._media_asset_metadata import (
    MediaAssetMetadata,
)
from rapidata.rapidata_client.datapoints.metadata._prompt_metadata import PromptMetadata
from rapidata.rapidata_client.config import logger


class Datapoint:
    def __init__(
        self,
        asset: MediaAsset | TextAsset | MultiAsset,
        metadata: Sequence[Metadata] | None = None,
    ):
        if not isinstance(asset, (MediaAsset, TextAsset, MultiAsset)):
            raise TypeError(
                "Asset must be of type MediaAsset, TextAsset, or MultiAsset."
            )

        if metadata and not isinstance(metadata, Sequence):
            raise TypeError("Metadata must be a list of Metadata objects.")

        if metadata and not all(isinstance(m, Metadata) for m in metadata):
            raise TypeError("All metadata objects must be of type Metadata.")

        self.asset = asset
        self.metadata = metadata

    def _get_effective_asset_type(self) -> type:
        """Get the effective asset type, handling MultiAsset by looking at its first asset."""
        if isinstance(self.asset, MultiAsset):
            return type(self.asset.assets[0])
        return type(self.asset)

    def is_media_asset(self) -> bool:
        """Check if this datapoint contains media assets."""
        effective_type = self._get_effective_asset_type()
        return issubclass(effective_type, MediaAsset)

    def is_text_asset(self) -> bool:
        """Check if this datapoint contains text assets."""
        effective_type = self._get_effective_asset_type()
        return issubclass(effective_type, TextAsset)

    def get_asset_type(self) -> AssetType:
        """Get the asset type of the datapoint."""
        if self.is_text_asset():
            return AssetType.TEXT
        elif self.is_media_asset():
            if isinstance(self.asset, MultiAsset):
                asset = self.asset.assets[0]
            else:
                asset = self.asset
            assert isinstance(asset, MediaAsset)
            if any(asset.path.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
                return AssetType.IMAGE
            elif any(asset.path.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
                return AssetType.VIDEO
            elif any(asset.path.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS):
                return AssetType.AUDIO
            else:
                logger.debug(
                    f"Cannot get asset type for asset type: {type(self.asset)}"
                )
                return AssetType.NONE
        else:
            logger.debug(f"Cannot get asset type for asset type: {type(self.asset)}")
            return AssetType.NONE

    def get_prompt_type(self) -> list[PromptType]:
        """Get the prompt type of the datapoint."""
        prompt_types = []
        for metadata in self.metadata or []:
            if isinstance(metadata, MediaAssetMetadata):
                prompt_types.append(PromptType.ASSET)
            elif isinstance(metadata, PromptMetadata):
                prompt_types.append(PromptType.TEXT)

        if len(prompt_types) == 0:
            return [PromptType.NONE]

        return prompt_types

    def get_texts(self) -> list[str]:
        """Extract text content from the asset(s)."""
        if isinstance(self.asset, TextAsset):
            return [self.asset.text]
        elif isinstance(self.asset, MultiAsset):
            texts = []
            for asset in self.asset.assets:
                if isinstance(asset, TextAsset):
                    texts.append(asset.text)
            return texts
        else:
            raise ValueError(f"Cannot extract text from asset type: {type(self.asset)}")

    def get_media_assets(self) -> list[MediaAsset]:
        """Extract media assets from the datapoint."""
        if isinstance(self.asset, MediaAsset):
            return [self.asset]
        elif isinstance(self.asset, MultiAsset):
            media_assets = []
            for asset in self.asset.assets:
                if isinstance(asset, MediaAsset):
                    media_assets.append(asset)
            return media_assets
        else:
            raise ValueError(
                f"Cannot extract media assets from asset type: {type(self.asset)}"
            )

    def get_local_file_paths(
        self,
    ) -> list[StrictStr | tuple[StrictStr, StrictBytes] | StrictBytes]:
        """Get local file paths for media assets that are stored locally."""
        if not self.is_media_asset():
            return []

        media_assets = self.get_media_assets()
        return [asset.to_file() for asset in media_assets if asset.is_local()]

    def get_urls(self) -> list[str]:
        """Get URLs for media assets that are remote."""
        if not self.is_media_asset():
            return []

        media_assets = self.get_media_assets()
        return [asset.path for asset in media_assets if not asset.is_local()]

    def get_prepared_metadata(
        self,
    ) -> list[DatasetDatasetIdDatapointsPostRequestMetadataInner]:
        """Prepare metadata for API upload."""
        metadata: list[DatasetDatasetIdDatapointsPostRequestMetadataInner] = []
        if self.metadata:
            for meta in self.metadata:
                meta_model = meta.to_model() if meta else None
                if meta_model:
                    metadata.append(
                        DatasetDatasetIdDatapointsPostRequestMetadataInner(meta_model)
                    )
        return metadata

    def create_text_upload_model(
        self, index: int
    ) -> CreateDatapointFromTextSourcesModel:
        """Create the model for uploading text datapoints."""
        if not self.is_text_asset():
            raise ValueError("Cannot create text upload model for non-text asset")

        texts = self.get_texts()
        metadata = self.get_prepared_metadata()

        return CreateDatapointFromTextSourcesModel(
            textSources=texts,
            sortIndex=index,
            metadata=metadata,
        )

    def get_datapoint_string(self) -> str:
        """Get the datapoint string for the datapoint."""
        if isinstance(self.asset, MediaAsset):
            return self.asset.path
        elif isinstance(self.asset, TextAsset):
            return self.asset.text
        else:
            raise ValueError(
                f"Cannot get datapoint string for asset type: {type(self.asset)}"
            )

    def __str__(self):
        return f"Datapoint(asset={self.asset})"

    def __repr__(self):
        return self.__str__()
