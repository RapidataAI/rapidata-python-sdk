"""Shaping of order results for return over MCP.

Raw results carry one ``detailedResults`` entry per individual response — each
with the annotator's country, language, demographics and reliability score.
For an order with thousands of responses that payload is far too large to hand
back to an agent verbatim, so detail is dropped unless explicitly requested and
the datapoint list is capped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rapidata.rapidata_client.results.rapidata_results import RapidataResults

_DETAIL_KEY = "detailedResults"


def summarize_results(
    results: RapidataResults,
    include_details: bool = False,
    max_datapoints: int = 50,
) -> dict[str, Any]:
    """Return a JSON-serialisable summary of an order's results.

    Args:
        results: The raw results from the SDK.
        include_details: Keep per-annotator ``detailedResults``. Off by default.
        max_datapoints: Cap on how many per-datapoint entries are returned.
    """
    items = results.get("results", []) or []
    total = len(items)
    shown = items[:max_datapoints]

    out_items: list[dict[str, Any]] = []
    for item in shown:
        if include_details:
            out_items.append(item)
        else:
            out_items.append({k: v for k, v in item.items() if k != _DETAIL_KEY})

    return {
        "info": results.get("info", {}),
        "summary": results.get("summary", {}),
        "datapoint_count": total,
        "returned_datapoints": len(out_items),
        "truncated": total > len(out_items),
        "results": out_items,
    }
