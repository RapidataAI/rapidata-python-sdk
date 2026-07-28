"""Tests for prompt tag/origin input coercion on benchmarks.

Tags gained an optional ``category`` (``Tag``) and prompts gained an ``Origin``,
but scripts written before that pass plain ``list[list[str]]`` / ``list[str]``.
Those have to keep working — both at runtime and, because the annotations are
covariant ``Sequence``s rather than invariant ``list``s, under a type checker.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rapidata.rapidata_client.benchmark._prompt_uploader import BenchmarkPrompt
from rapidata.rapidata_client.benchmark.prompt_metadata import Origin, Tag
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


def _add_prompts(benchmark: RapidataBenchmark, count: int, **kwargs) -> None:
    # `identifiers` re-fetches over HTTP while the cache is empty; an empty
    # benchmark is all these cases need.
    with patch.object(RapidataBenchmark, "identifiers", property(lambda self: [])):
        benchmark.add_prompts(
            identifiers=[f"id{i}" for i in range(count)],
            prompts=[f"p{i}" for i in range(count)],
            **kwargs,
        )


@pytest.mark.parametrize(
    "tags,expected",
    [
        # The pre-category shape: plain strings become uncategorized tags.
        ([["a", "b"], ["c"]], [[Tag("a"), Tag("b")], [Tag("c")]]),
        ([[Tag("a", "cat")], [Tag("b")]], [[Tag("a", "cat")], [Tag("b")]]),
        ([["a", Tag("b", "cat")], []], [[Tag("a"), Tag("b", "cat")], []]),
        ([["a"], None], [[Tag("a")], []]),
        # Any sequence, not just list — the annotation is a Sequence.
        ((("a", "b"), ("c",)), [[Tag("a"), Tag("b")], [Tag("c")]]),
    ],
)
def test_add_prompts_coerces_tags(tags, expected) -> None:
    benchmark, uploaded = _make_benchmark()
    _add_prompts(benchmark, len(tags), tags=tags)
    assert [prompt.tags for prompt in uploaded[0]] == expected


@pytest.mark.parametrize(
    "origins,expected",
    [
        (["coco", "laion"], [Origin("coco"), Origin("laion")]),
        ([Origin("coco"), None], [Origin("coco"), None]),
        (["coco", Origin("laion")], [Origin("coco"), Origin("laion")]),
    ],
)
def test_add_prompts_coerces_origins(origins, expected) -> None:
    benchmark, uploaded = _make_benchmark()
    _add_prompts(benchmark, len(origins), origins=origins)
    assert [prompt.origin for prompt in uploaded[0]] == expected


def test_tags_property_stays_values_only() -> None:
    """`.tags` predates categories and must keep its `list[list[str]]` shape."""
    benchmark, _ = _make_benchmark()
    _add_prompts(benchmark, 2, tags=[["a", Tag("b", "cat")], ["c"]])

    assert benchmark.tags == [["a", "b"], ["c"]]
    assert benchmark.structured_tags == [[Tag("a"), Tag("b", "cat")], [Tag("c")]]


@pytest.mark.parametrize("tags", ["abc", ["a", "b"], [1], [["a"], "b"]])
def test_add_prompts_rejects_malformed_tags(tags) -> None:
    """A flat string list is a plausible mistake and must not be accepted.

    A `str` is itself a `Sequence`, so without an explicit guard `tags=["a", "b"]`
    would be read as two prompts' worth of tags rather than one prompt's.
    """
    benchmark, _ = _make_benchmark()
    with pytest.raises(ValueError, match="Tags must be"):
        _add_prompts(benchmark, 2, tags=tags)


def test_add_prompts_rejects_malformed_origins() -> None:
    benchmark, _ = _make_benchmark()
    with pytest.raises(ValueError, match="Origins must be"):
        _add_prompts(benchmark, 1, origins=[1])


def test_update_prompt_coerces_and_replaces_tags() -> None:
    benchmark, _ = _make_benchmark()
    _add_prompts(benchmark, 1, tags=[["old"]])

    with patch.object(
        RapidataBenchmark,
        "_RapidataBenchmark__instantiate_prompts",
        lambda self: None,
    ):
        benchmark._RapidataBenchmark__prompt_ids["id0"] = "prompt-0"  # type: ignore[attr-defined]
        benchmark.update_prompt("id0", tags=["new", Tag("extra", "cat")])

    sent = (
        benchmark._openapi_service.leaderboard.prompt_api.benchmark_prompt_prompt_id_tags_put
    )
    payload = sent.call_args.kwargs["update_prompt_tags_endpoint_input"]
    assert [(tag.value, tag.category) for tag in payload.tags or []] == [
        ("new", None),
        ("extra", "cat"),
    ]
    # The cache reflects the replacement without a re-fetch.
    assert benchmark.tags == [["new", "extra"]]


def test_update_prompt_requires_a_field() -> None:
    benchmark, _ = _make_benchmark()
    with pytest.raises(ValueError, match="Provide tags and/or origin"):
        benchmark.update_prompt("id0")
