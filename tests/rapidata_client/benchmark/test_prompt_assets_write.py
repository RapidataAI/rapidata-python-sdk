"""Tests for the assets a benchmark prompt is registered with.

A prompt's assets are a ``list[str]`` per prompt, the same shape the job
definitions take for ``media_contexts`` and the same shape ``prompt_assets``
reads back, so a value read from one benchmark can be fed straight into
``add_prompts`` on another. Scripts written when a prompt could only carry a
single asset pass a bare ``str`` per prompt; those keep working.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from rapidata.api_client.models.i_asset_input_existing_asset_input import (
    IAssetInputExistingAssetInput,
)
from rapidata.api_client.models.i_asset_input_multi_asset_input import (
    IAssetInputMultiAssetInput,
)
from rapidata.rapidata_client.benchmark._prompt_uploader import (
    BenchmarkPrompt,
    BenchmarkPromptUploader,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


def _make_benchmark() -> tuple[RapidataBenchmark, list[list[BenchmarkPrompt]]]:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    benchmark = RapidataBenchmark("bm", "bm-1", svc)

    uploaded: list[list[BenchmarkPrompt]] = []

    def upload_many(prompts: list[BenchmarkPrompt]) -> list[BenchmarkPrompt]:
        uploaded.append(prompts)
        return prompts

    benchmark._prompt_uploader.upload_many = upload_many  # type: ignore[method-assign]
    return benchmark, uploaded


def _add_prompts(benchmark: RapidataBenchmark, prompt_assets) -> None:
    # `identifiers` re-fetches over HTTP while the cache is empty; an empty
    # benchmark is all these cases need.
    with patch.object(RapidataBenchmark, "identifiers", property(lambda self: [])):
        benchmark.add_prompts(
            identifiers=[f"id{i}" for i in range(len(prompt_assets))],
            prompt_assets=prompt_assets,
        )


def test_add_prompts_takes_a_list_of_assets_per_prompt() -> None:
    benchmark, uploaded = _make_benchmark()

    _add_prompts(
        benchmark,
        [
            ["https://assets.rapidata.ai/a.jpg"],
            ["https://assets.rapidata.ai/ref.gif", "https://assets.rapidata.ai/b.jpg"],
            None,
        ],
    )

    assert [p.prompt_asset for p in uploaded[0]] == [
        ["https://assets.rapidata.ai/a.jpg"],
        ["https://assets.rapidata.ai/ref.gif", "https://assets.rapidata.ai/b.jpg"],
        None,
    ]
    assert benchmark.prompt_assets == [
        ["https://assets.rapidata.ai/a.jpg"],
        ["https://assets.rapidata.ai/ref.gif", "https://assets.rapidata.ai/b.jpg"],
        None,
    ]


def test_add_prompts_still_accepts_one_string_per_prompt(caplog) -> None:
    benchmark, uploaded = _make_benchmark()

    with caplog.at_level(logging.WARNING, logger="rapidata"):
        _add_prompts(benchmark, ["https://assets.rapidata.ai/a.jpg", None])

    assert [p.prompt_asset for p in uploaded[0]] == [
        ["https://assets.rapidata.ai/a.jpg"],
        None,
    ]
    # One notice per call, not one per prompt.
    deprecations = [r for r in caplog.records if "deprecated" in r.getMessage()]
    assert len(deprecations) == 1


def test_cached_assets_match_what_a_refetch_reads_back() -> None:
    # Locally uploaded files come back from the server as their bare filename,
    # so the cache holds the same value the read side would reconstruct.
    benchmark, _ = _make_benchmark()

    _add_prompts(
        benchmark,
        [["/data/frames/ref.gif", "https://assets.rapidata.ai/still.jpg"]],
    )

    assert benchmark.prompt_assets == [
        ["ref.gif", "https://assets.rapidata.ai/still.jpg"]
    ]


@pytest.mark.parametrize(
    "prompt_assets",
    [
        [[]],
        [[""]],
        [""],
        [["a.jpg", 3]],
        [42],
        "a.jpg",
    ],
)
def test_add_prompts_rejects_malformed_assets(prompt_assets) -> None:
    benchmark, _ = _make_benchmark()

    with pytest.raises(ValueError):
        _add_prompts(benchmark, prompt_assets)


def _make_uploader() -> tuple[BenchmarkPromptUploader, MagicMock]:
    svc = MagicMock()
    uploader = BenchmarkPromptUploader("bm-1", svc)
    uploader._asset_uploader.upload_asset = MagicMock(side_effect=lambda a: f"up:{a}")  # type: ignore[method-assign]
    return uploader, svc.leaderboard.benchmark_api.benchmark_benchmark_id_prompt_post


def _sent_asset(post: MagicMock):
    return post.call_args.kwargs[
        "create_prompt_for_benchmark_endpoint_input"
    ].prompt_asset


def test_single_asset_is_sent_as_an_existing_asset() -> None:
    uploader, post = _make_uploader()

    uploader.upload(BenchmarkPrompt("id0", "p0", ["a.jpg"]))

    sent = _sent_asset(post).actual_instance
    assert isinstance(sent, IAssetInputExistingAssetInput)
    assert sent.name == "up:a.jpg"


def test_several_assets_are_sent_as_one_multi_asset() -> None:
    uploader, post = _make_uploader()

    uploader.upload(BenchmarkPrompt("id0", "p0", ["ref.gif", "still.jpg"]))

    sent = _sent_asset(post).actual_instance
    assert isinstance(sent, IAssetInputMultiAssetInput)
    assert [part.actual_instance.name for part in sent.assets] == [
        "up:ref.gif",
        "up:still.jpg",
    ]


def test_no_asset_sends_none() -> None:
    uploader, post = _make_uploader()

    uploader.upload(BenchmarkPrompt("id0", "p0", None))

    assert _sent_asset(post) is None
