from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UploadedAsset:
    """A reference to media that is already uploaded to Rapidata.

    Job definitions accept it wherever they take a media datapoint or media
    context, on its own or mixed with paths and URLs, and use it as-is instead
    of uploading again. Get one from ``client.asset.upload(...)``, or wrap the
    ``fileName`` the asset API returned for an upload.

    Attributes:
        name: The uploaded asset's file name on Rapidata.
    """

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("UploadedAsset.name must be a non-empty string.")
        if "://" in self.name:
            raise ValueError(
                f"UploadedAsset.name must be an uploaded asset's file name, not a URL: "
                f"{self.name!r}. Upload the URL with client.asset.upload() first."
            )
