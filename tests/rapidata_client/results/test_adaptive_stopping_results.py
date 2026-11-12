"""Compare results keep the backend's adaptiveStoppingState exactly as downloaded."""

from __future__ import annotations

import copy
import json

from rapidata.rapidata_client.results.rapidata_results import RapidataResults

DECIDED = {
    "verdict": "Decided",
    "winners": ["1"],
    "outcomes": {
        "0": {"weight": 1.485, "lower": 0.004, "upper": 0.496},
        "1": {"weight": 10.515, "lower": 0.504, "upper": 0.996},
    },
    "responseCount": 12,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
}

UNDECIDED_ALL_SKIPS = {
    "verdict": "Undecided",
    "winners": [],
    "outcomes": {},
    "responseCount": 0,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
}


def _compare_result(identifier: str, state: dict | None) -> dict:
    result = {
        "identifier": identifier,
        "assetUrls": {"a.png": "https://host/a.png", "b.png": "https://host/b.png"},
        "aggregatedResults": {"a.png": 1, "b.png": 11},
        "detailedResults": [],
    }
    if state is not None:
        result["adaptiveStoppingState"] = state
    return result


def _results(*results: dict) -> RapidataResults:
    payload = {"info": {"type": "Compare"}, "results": list(results)}
    return RapidataResults(json.loads(json.dumps(payload)))


def test_state_is_kept_verbatim_on_each_datapoint():
    results = _results(
        _compare_result("p1", DECIDED), _compare_result("p2", UNDECIDED_ALL_SKIPS)
    )

    assert results["results"][0]["adaptiveStoppingState"] == DECIDED
    assert results["results"][1]["adaptiveStoppingState"] == UNDECIDED_ALL_SKIPS


def test_state_survives_to_json(tmp_path):
    results = _results(_compare_result("p1", DECIDED))
    path = tmp_path / "results.json"

    results.to_json(str(path))

    saved = json.loads(path.read_text())
    assert saved["results"][0]["adaptiveStoppingState"] == DECIDED


def test_to_pandas_flattens_the_state_without_recomputing_it():
    results = _results(
        _compare_result("p1", DECIDED), _compare_result("p2", UNDECIDED_ALL_SKIPS)
    )
    before = copy.deepcopy(dict(results))

    df = results.to_pandas()

    decided, undecided = df.iloc[0], df.iloc[1]
    assert decided["adaptiveStoppingState_verdict"] == "Decided"
    assert decided["adaptiveStoppingState_responseCount"] == 12
    assert decided["adaptiveStoppingState_outcomes_1_weight"] == 10.515
    assert decided["adaptiveStoppingState_outcomes_0_upper"] == 0.496
    assert undecided["adaptiveStoppingState_verdict"] == "Undecided"
    assert dict(results) == before


def test_results_without_the_state_are_unchanged():
    df = _results(_compare_result("p1", None)).to_pandas()

    assert not any(c.startswith("adaptiveStoppingState") for c in df.columns)
    assert df.iloc[0]["A_aggregatedResults"] == 1
