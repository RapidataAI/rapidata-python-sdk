import pytest

from rapidata.rapidata_client.datapoints._datapoint import (
    MAX_MEDIA_CONTEXT_ASSETS,
    Datapoint,
    coerce_media_context,
)


def _contexts(count: int) -> list[str]:
    return [f"https://example.com/{i}.png" for i in range(count)]


def test_media_context_at_the_limit_is_accepted() -> None:
    contexts = _contexts(MAX_MEDIA_CONTEXT_ASSETS)

    assert coerce_media_context(contexts) == contexts


def test_media_context_over_the_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="at most 10 entries, got 11"):
        coerce_media_context(_contexts(MAX_MEDIA_CONTEXT_ASSETS + 1))


def test_datapoint_rejects_media_context_over_the_limit() -> None:
    with pytest.raises(ValueError, match="at most 10 entries"):
        Datapoint(
            asset="https://example.com/a.png",
            data_type="media",
            media_context=_contexts(MAX_MEDIA_CONTEXT_ASSETS + 1),
        )
