"""Tests for FailedUploadException message rendering.

Focused on the file-descriptor-exhaustion hint: when an upload fails because the
process ran out of file descriptors, the exception message must point the user
at the knobs (cacheShards / maxWorkers / ulimit) rather than only listing the
raw OSError.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)


def _exception(failed_uploads: list[FailedUpload]) -> FailedUploadException:
    return FailedUploadException(dataset=MagicMock(), failed_uploads=failed_uploads)


def test_hint_added_when_errno_is_emfile() -> None:
    exc = OSError(24, "Too many open files")
    failure = FailedUpload.from_exception("img.jpg", exc)

    message = str(_exception([failure]))

    assert "file-descriptor exhaustion" in message
    assert "RAPIDATA_cacheShards" in message
    assert "RAPIDATA_maxWorkers" in message
    assert "ulimit -n" in message


def test_hint_added_when_only_message_matches() -> None:
    # Some layers stringify the OSError before it reaches us, losing the errno.
    failure = FailedUpload(
        item="img.jpg",
        error_message="[Errno 24] Too many open files: 'img.jpg'",
        error_type="OSError",
    )

    assert "file-descriptor exhaustion" in str(_exception([failure]))


def test_no_hint_for_unrelated_failures() -> None:
    failure = FailedUpload(
        item="img.jpg", error_message="404 not found", error_type="RapidataError"
    )

    assert "file-descriptor exhaustion" not in str(_exception([failure]))
