"""Tests for the body the prompt-upload endpoint actually receives.

The upload path had no coverage over the wire body, so when the backend
replaced the flat ``prompt`` / ``promptAsset`` fields with keyed ``segments``
the generated model silently dropped both kwargs — pydantic ignores unknown
fields — and every prompt uploaded with no text and no asset while the asset
itself was still uploaded and billed. Asserting on the serialized body is the
only assertion that would have caught it.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.rapidata_client.benchmark._prompt_uploader import (
    BenchmarkPrompt,
    BenchmarkPromptUploader,
)
from rapidata.rapidata_client.benchmark.prompt_metadata import Origin, Tag


def _upload(prompt: BenchmarkPrompt) -> dict:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    uploader = BenchmarkPromptUploader("bm-1", svc)
    uploader._asset_uploader.upload_asset = MagicMock(return_value="uploaded.jpg")  # type: ignore[method-assign]

    uploader.upload(prompt)

    post = svc.leaderboard.benchmark_api.benchmark_benchmark_id_prompt_post
    post.assert_called_once()
    return post.call_args.kwargs["create_prompt_for_benchmark_endpoint_input"].to_dict()


def test_text_prompt_is_sent_as_a_text_segment() -> None:
    body = _upload(BenchmarkPrompt(identifier="id0", prompt="a cat"))

    assert body["identifier"] == "id0"
    assert body["segments"] == [{"key": "prompt", "kind": "Text", "text": "a cat"}]


def test_prompt_asset_is_sent_as_an_asset_segment() -> None:
    body = _upload(
        BenchmarkPrompt(identifier="id0", prompt_asset="https://x.test/cat.jpg")
    )

    assert body["segments"] == [
        {
            "key": "prompt_asset",
            "kind": "Asset",
            "asset": {"_t": "ExistingAssetInput", "name": "uploaded.jpg"},
        }
    ]


def test_text_and_asset_are_sent_as_two_segments() -> None:
    body = _upload(
        BenchmarkPrompt(
            identifier="id0",
            prompt="a cat",
            prompt_asset="https://x.test/cat.jpg",
            tags=[Tag("scene", category="kind")],
            origin=Origin("coco"),
        )
    )

    assert [segment["key"] for segment in body["segments"]] == [
        "prompt",
        "prompt_asset",
    ]
    assert body["tags"] == [{"value": "scene", "category": "kind"}]
    assert body["origin"] == {"source": "coco"}


def test_legacy_fields_are_never_sent() -> None:
    """Sending both representations is a 400, so the flat fields must stay off."""
    body = _upload(
        BenchmarkPrompt(
            identifier="id0", prompt="a cat", prompt_asset="https://x.test/cat.jpg"
        )
    )

    assert "prompt" not in body
    assert "promptAsset" not in body
