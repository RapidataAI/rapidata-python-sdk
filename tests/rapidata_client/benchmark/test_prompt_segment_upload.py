"""Tests for the segment payload a benchmark prompt is registered with.

The create-prompt endpoint no longer takes a flat ``prompt`` / ``promptAsset``
pair — those are deprecated on the wire and stripped from the generated client
entirely. The SDK's flat surface now maps onto the two segment keys of the
default prompt structure, and an absent value must send no segment at all
rather than an empty one.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_asset_input_existing_asset_input import (
    IAssetInputExistingAssetInput,
)
from rapidata.api_client.models.prompt_segment_kind import PromptSegmentKind
from rapidata.rapidata_client.benchmark._prompt_uploader import (
    BenchmarkPrompt,
    BenchmarkPromptUploader,
)
from rapidata.rapidata_client.benchmark.prompt_metadata import Origin, Tag


def _upload(prompt: BenchmarkPrompt):
    uploader = BenchmarkPromptUploader("bm-1", MagicMock())
    uploader._asset_uploader = MagicMock()  # type: ignore[method-assign]
    uploader._asset_uploader.upload_and_map_asset.side_effect = (
        lambda asset: IAssetInput(
            actual_instance=IAssetInputExistingAssetInput(
                _t="ExistingAssetInput", name=f"mapped:{asset}"
            )
        )
    )

    uploader.upload(prompt)

    post = (
        uploader._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_prompt_post
    )
    post.assert_called_once()
    return post.call_args.kwargs["create_prompt_for_benchmark_endpoint_input"]


def test_text_and_asset_map_to_the_default_segment_keys() -> None:
    payload = _upload(
        BenchmarkPrompt(
            identifier="id0",
            prompt="a red car",
            prompt_asset="https://assets.rapidata.ai/ref.jpg",
            tags=[Tag("scene", "kind")],
            origin=Origin("coco"),
        )
    )

    assert payload.identifier == "id0"
    assert [(s.key, s.kind) for s in payload.segments] == [
        ("prompt", PromptSegmentKind.TEXT),
        ("prompt_asset", PromptSegmentKind.ASSET),
    ]
    assert payload.segments[0].text == "a red car"
    asset = payload.segments[1].asset
    assert asset is not None
    assert asset.actual_instance.name == "mapped:https://assets.rapidata.ai/ref.jpg"


def test_missing_values_send_no_segment() -> None:
    payload = _upload(BenchmarkPrompt(identifier="id0", prompt="text only"))

    assert [s.key for s in payload.segments] == ["prompt"]


def test_asset_only_prompt_sends_only_the_asset_segment() -> None:
    payload = _upload(
        BenchmarkPrompt(
            identifier="id0", prompt_asset="https://assets.rapidata.ai/a.jpg"
        )
    )

    assert [s.key for s in payload.segments] == ["prompt_asset"]
