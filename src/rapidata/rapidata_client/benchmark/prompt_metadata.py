from __future__ import annotations

from dataclasses import dataclass


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

    value: str
