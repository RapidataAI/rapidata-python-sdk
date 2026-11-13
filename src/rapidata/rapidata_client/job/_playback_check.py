from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.datapoints._default_segments import (
    ASSET_SEGMENT_KEY,
    CONTEXT_ASSET_SEGMENT_KEY,
)

if TYPE_CHECKING:
    from rapidata.api_client.models.i_asset import IAsset
    from rapidata.service.openapi_service import OpenAPIService

MAX_PLAYBACK_SECONDS = 15.0
SAMPLE_SIZE = 100

_DURATION_RE = re.compile(r"^(?:(\d+)\.)?(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)$")


def _parse_duration(value: str) -> float | None:
    match = _DURATION_RE.match(value)
    if match is None:
        return None
    days, hours, minutes, seconds = match.groups()
    return (
        int(days or 0) * 86400 + int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    )


def _clips(asset: IAsset | None) -> Iterable[tuple[bool, float]]:
    """Yields ``(is_video, seconds)`` for every timed file in the asset."""
    from rapidata.api_client.models.i_asset_file_asset import IAssetFileAsset
    from rapidata.api_client.models.i_asset_multi_asset import IAssetMultiAsset
    from rapidata.api_client.models.i_metadata_streams_metadata import (
        IMetadataStreamsMetadata,
    )
    from rapidata.api_client.models.i_metadata_video_duration_metadata import (
        IMetadataVideoDurationMetadata,
    )

    instance = asset.actual_instance if asset is not None else None
    if isinstance(instance, IAssetMultiAsset):
        for child in instance.assets:
            yield from _clips(child)
        return
    if not isinstance(instance, IAssetFileAsset):
        return

    seconds: float | None = None
    is_video = False
    for value in instance.metadata.values():
        meta = value.actual_instance
        if isinstance(meta, IMetadataVideoDurationMetadata):
            seconds = _parse_duration(meta.duration)
        elif isinstance(meta, IMetadataStreamsMetadata):
            is_video = meta.has_video
    if seconds is not None:
        yield is_video, seconds


def playback_seconds(assets: Iterable[IAsset | None]) -> float:
    """Audio clips play one after the other and add up; videos count by the longest one."""
    audio = 0.0
    video = 0.0
    for asset in assets:
        for is_video, seconds in _clips(asset):
            if is_video:
                video = max(video, seconds)
            else:
                audio += seconds
    return audio + video


def warn_long_playback(openapi_service: OpenAPIService, dataset_id: str) -> None:
    """Warns when sampled datapoints need more playback than a task's time budget. Never raises."""
    try:
        response = (
            openapi_service.dataset.datapoints_api.dataset_dataset_id_datapoints_get(
                dataset_id=dataset_id, page=1, page_size=SAMPLE_SIZE
            )
        )
        durations = [
            playback_seconds(
                segment.asset
                for segment in datapoint.segments
                if segment.key in (ASSET_SEGMENT_KEY, CONTEXT_ASSET_SEGMENT_KEY)
            )
            for datapoint in response.items
        ]
    except Exception as e:
        logger.debug("Skipped the media playback check: %s", e)
        return

    too_long = [d for d in durations if d > MAX_PLAYBACK_SECONDS]
    if not too_long:
        return
    logger.warning(
        "%d of %d checked datapoint(s) need more than %d seconds of media playback "
        "(longest: %.1f s). Labelers should answer a task in about 10 seconds, "
        "15 at most, and audio clips play one after the other, so their lengths add up. "
        "Trim the clips to the part the question checks; see 'Task design rules' in "
        "`python -m rapidata skill`.",
        len(too_long),
        len(durations),
        int(MAX_PLAYBACK_SECONDS),
        max(too_long),
    )
