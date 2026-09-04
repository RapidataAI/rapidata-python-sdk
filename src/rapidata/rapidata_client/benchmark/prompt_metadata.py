from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass
class Tag:
    """A structured tag attached to a benchmark prompt.

    Tags are metadata used to filter and organize benchmark results; they are
    never shown to the annotators. ``category`` optionally groups related tags
    (e.g. ``Tag("landscape", category="scene")``); leave it ``None`` for a bare
    tag.
    """

    value: str
    category: str | None = None


@dataclass
class Origin:
    """Where a benchmark prompt originated from (e.g. a source dataset)."""

    source: str


@dataclass
class BenchmarkPromptInfo:
    """A single prompt returned by a filtered/sorted benchmark prompt query."""

    identifier: str
    prompt: str | None
    english_prompt: str | None
    prompt_asset: list[str] | None
    tags: list[Tag]
    origin: Origin | None


def is_tag_list(value: Any) -> bool:
    """Whether ``value`` is usable as one prompt's tag list.

    A bare ``str`` is itself a ``Sequence`` of characters, so it has to be
    rejected explicitly or ``tags=["a", "b"]`` would silently be read as two
    prompts' worth of tags instead of one.
    """
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def coerce_tags(tags: Sequence[str | Tag] | None) -> list[Tag]:
    """Normalize user-supplied tags into ``Tag`` objects.

    Bare strings become uncategorized tags, so callers can keep passing the
    plain ``list[str]`` they used before categories existed.
    """
    return [Tag(value=item) if isinstance(item, str) else item for item in (tags or [])]


def coerce_origin(origin: Origin | str | None) -> Origin | None:
    """Normalize a user-supplied origin into an ``Origin``."""
    return Origin(source=origin) if isinstance(origin, str) else origin


def coerce_prompt_asset(asset: object) -> list[str] | None:
    """Normalize one prompt's asset(s) to ``list[str] | None``.

    A prompt's assets are a list of URLs / file paths, the same shape the job
    definitions use for ``media_contexts``; several entries are registered as
    one multi-asset. A bare ``str`` is still accepted for scripts written when
    a prompt could only carry one asset and is wrapped in a single-element list.
    """
    if asset is None:
        return None
    if isinstance(asset, str):
        if asset == "":
            raise ValueError(
                "A prompt asset cannot be an empty string. If not needed, set to None."
            )
        return [asset]
    if isinstance(asset, list):
        if len(asset) == 0:
            raise ValueError(
                "A prompt asset list cannot be empty. If not needed, set to None."
            )
        if any(not isinstance(item, str) or item == "" for item in asset):
            raise ValueError(
                "Every entry in a prompt asset list must be a non-empty string."
            )
        return asset
    raise ValueError(
        f"A prompt asset must be a list of strings or None, got {type(asset).__name__}."
    )
