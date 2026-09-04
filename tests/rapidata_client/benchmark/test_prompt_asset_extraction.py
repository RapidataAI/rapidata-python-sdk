"""Tests for reading back the asset a benchmark prompt carries.

The prompts endpoint returns the read-side ``IAsset`` union
(``IAssetFileAsset`` / ``IAssetMultiAsset`` / ``IAssetNullAsset`` /
``IAssetTextAsset``), never the write-side ``IAssetModel*`` classes. Asserting
on the write-side class made every asset-carrying benchmark raise on
``identifiers`` — and so on ``add_model``, which validates against it — before
a single byte was uploaded. Only text-only benchmarks stayed usable.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.get_prompts_by_benchmark_endpoint_output import (
    GetPromptsByBenchmarkEndpointOutput,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark

_FILE_ASSET = {
    "_t": "FileAsset",
    "fileName": "38719dc3-31e1-491b-b5ec-f72e4260562e.jpg",
    "metadata": {
        "fileType": {"_t": "FileTypeMetadata", "fileType": "Image"},
        "originalFilename": {
            "_t": "OriginalFilenameMetadata",
            "originalFilename": "8.jpg",
        },
    },
    "identifier": "38719dc3-31e1-491b-b5ec-f72e4260562e.jpg",
}

_REMOTE_FILE_ASSET = {
    "_t": "FileAsset",
    "fileName": "9c0b5f21-1f4f-4a2b-9f3e-1d0c2b3a4e5f.jpg",
    "metadata": {
        "sourceUrl": {
            "_t": "SourceUrlMetadataModel",
            "url": "https://assets.rapidata.ai/prompt_1.jpg",
        },
        "originalFilename": {
            "_t": "OriginalFilenameMetadata",
            "originalFilename": "prompt_1.jpg",
        },
    },
    "identifier": "9c0b5f21-1f4f-4a2b-9f3e-1d0c2b3a4e5f.jpg",
}

_MULTI_ASSET = {
    "_t": "MultiAsset",
    "assets": [
        {
            "_t": "FileAsset",
            "fileName": "3b9b0cca-e70b-45e6-908a-fbc318b218fe.gif",
            "metadata": {
                "originalFilename": {
                    "_t": "OriginalFilenameMetadata",
                    "originalFilename": "camera-moves-forward.gif",
                }
            },
            "identifier": "3b9b0cca-e70b-45e6-908a-fbc318b218fe.gif",
        },
        {
            "_t": "FileAsset",
            "fileName": "d87f1813-d2fe-4d79-8a08-2680f4d3f2bc.jpg",
            "metadata": {
                "originalFilename": {
                    "_t": "OriginalFilenameMetadata",
                    "originalFilename": "interior-2685521.jpg",
                }
            },
            "identifier": "d87f1813-d2fe-4d79-8a08-2680f4d3f2bc.jpg",
        },
    ],
    "metadata": {},
    "identifier": "3b9b0cca-e70b-45e6-908a-fbc318b218fe.gif,d87f1813-d2fe-4d79-8a08-2680f4d3f2bc.jpg",
}

_NULL_ASSET = {"_t": "NullAsset", "metadata": {}, "identifier": "null"}

_TEXT_ASSET = {
    "_t": "TextAsset",
    "text": "a cat on a bicycle",
    "metadata": {},
    "identifier": "a cat on a bicycle",
}


def _prompt(identifier: str, prompt_asset: dict | None) -> dict:
    return {
        "id": f"prm_{identifier}",
        "identifier": identifier,
        "originalPrompt": f"prompt for {identifier}",
        "englishPrompt": f"prompt for {identifier}",
        "promptAsset": prompt_asset,
        "createdAt": "2026-09-04T12:00:00Z",
        "tags": [{"value": "scene", "category": "kind"}],
        "origin": {"source": "coco"},
    }


def _make_benchmark(prompts: list[dict]) -> RapidataBenchmark:
    svc = MagicMock()
    svc.environment = "rapidata.ai"

    items = [GetPromptsByBenchmarkEndpointOutput.from_dict(p) for p in prompts]
    page = MagicMock(items=items, total_pages=1)
    svc.leaderboard.benchmark_api.benchmark_benchmark_id_prompts_get.return_value = page

    return RapidataBenchmark("bm", "bm-1", svc)


@pytest.mark.parametrize(
    "asset,expected",
    [
        # A single asset is a one-element list: the same shape `add_prompts` takes.
        (_FILE_ASSET, ["8.jpg"]),
        # A remote asset keeps its URL; the filename is only the fallback.
        (_REMOTE_FILE_ASSET, ["https://assets.rapidata.ai/prompt_1.jpg"]),
        (_MULTI_ASSET, ["camera-moves-forward.gif", "interior-2685521.jpg"]),
        (_NULL_ASSET, None),
        (_TEXT_ASSET, None),
        (None, None),
    ],
)
def test_prompt_assets_read_back(asset, expected) -> None:
    benchmark = _make_benchmark([_prompt("id0", asset)])

    assert benchmark.identifiers == ["id0"]
    assert benchmark.prompt_assets == [expected]


def test_identifiers_across_mixed_asset_kinds() -> None:
    benchmark = _make_benchmark(
        [
            _prompt("realism", _FILE_ASSET),
            _prompt("camera", _MULTI_ASSET),
            _prompt("text-only", None),
        ]
    )

    assert benchmark.identifiers == ["realism", "camera", "text-only"]
    assert benchmark.prompts == [
        "prompt for realism",
        "prompt for camera",
        "prompt for text-only",
    ]
