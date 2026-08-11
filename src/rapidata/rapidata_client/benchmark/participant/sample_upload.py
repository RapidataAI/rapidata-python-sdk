from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SampleUpload:
    """A media/identifier pair as submitted to a benchmark participant.

    Used as the `item` of a `FailedUpload`, so a caller recovering from a
    partial upload has both halves of the pair and can re-submit it directly
    instead of reconstructing it from the logs.

    Attributes:
        media: The media asset (local path or URL) or text content.
        identifier: The benchmark identifier/prompt the media was paired with.
    """

    media: str
    identifier: str

    def __str__(self) -> str:
        return f"{self.identifier} ({self.media})"
