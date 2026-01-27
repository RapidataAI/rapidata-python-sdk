from __future__ import annotations

from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload


class AssetUploadException(Exception):
    """
    Exception raised when asset uploads fail in Step 1/2 of the two-step upload process.

    This exception contains details about which assets failed to upload,
    allowing users to decide how to proceed (retry, skip, or abort).

    Attributes:
        failed_uploads: List of FailedUpload instances containing the failed assets and error details.
    """

    def __init__(self, failed_uploads: list[FailedUpload[str]]):
        self.failed_uploads = failed_uploads
        message = (
            f"Failed to upload {len(failed_uploads)} asset(s) in Step 1/2. "
            f"See failed_uploads attribute for details."
        )
        super().__init__(message)

    def __str__(self) -> str:
        error_summary = "\n".join(
            f"  - {fu.item}: {fu.error_message}" for fu in self.failed_uploads[:5]
        )
        if len(self.failed_uploads) > 5:
            error_summary += f"\n  ... and {len(self.failed_uploads) - 5} more"
        return f"{super().__str__()}\n{error_summary}"
