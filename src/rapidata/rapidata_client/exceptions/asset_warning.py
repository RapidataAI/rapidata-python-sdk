from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class AssetWarning(Generic[T]):
    """A non-fatal advisory the backend attached to an otherwise-successful upload.

    Mirrors :class:`FailedUpload` for the success path: the upload went
    through, but the backend flagged something the caller should know about
    (e.g. a video longer than the annotator-solvable limit). Frozen so it can
    be de-duplicated in a set before reporting.

    Attributes:
        item: The asset (file path or URL) the warning is about.
        message: The backend-provided advisory text, surfaced verbatim.
    """

    item: T
    message: str

    def __str__(self) -> str:
        return f"{self.item}: {self.message}"
