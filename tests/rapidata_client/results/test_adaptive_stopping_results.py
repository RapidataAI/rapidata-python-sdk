from __future__ import annotations

import copy
import json
from unittest.mock import MagicMock

import pytest

from rapidata import RapidataJob
from rapidata.rapidata_client.results import RapidataResults


def _snapshot(verdict="Winner", ids=None, count=17, outcome_count=2):
    return {
        "modelVersion": "score-weighted-categorical-v1",
        "verdict": verdict,
        "leadingOutcomeIds": ["o0"] if ids is None else ids,
        "responseCount": count,
        "outcomes": [
            {
                "outcomeId": f"o{i}",
                "count": count if i == 0 else 0,
                "userScoreSum": 3.5 if i == 0 else 0.0,
                "share": {
                    "estimate": 1.0 if i == 0 else 0.0,
                    "lower": 0.6 if i == 0 else 0.0,
                    "upper": 1.0 if i == 0 else 0.4,
                },
            }
            for i in range(outcome_count)
        ],
        "ambiguity": {"estimate": 0.0, "lower": 0.0, "upper": 0.7},
        "parameters": {
            "maxVotes": 100,
            "minConfidence": 0.9,
            "ambiguityThreshold": 0.64,
            "unsolvableThreshold": None,
            "maxOutcomeCount": 1,
        },
    }


def _payload(task_type="Compare", **extra):
    row = {
        "identifier": "pair-1",
        "aggregatedResults": {"left.png": 12, "right.png": 5},
        "summedUserScores": {"left.png": 2.0, "right.png": 3.0},
        "detailedResults": [{"votedFor": "right.png"}],
        **extra,
    }
    if task_type == "Compare":
        row["assetUrls"] = {"left.png": "https://left", "right.png": "https://right"}
    return {"info": {"type": task_type}, "results": [row]}


@pytest.mark.parametrize("task_type", ["Compare", "Classification", "Classify"])
@pytest.mark.parametrize(
    "verdict",
    [
        "Open",
        "Winner",
        "TopSet",
        "Ambiguous",
        "Unsolvable",
        "Undecided",
        "FutureVerdict",
    ],
)
def test_canonical_verdicts_and_ids_are_not_reinterpreted(task_type, verdict):
    state = _snapshot(verdict)
    state["future"] = {"empty": {}, "items": [None, {"nested": True}]}
    result = RapidataResults(_payload(task_type, adaptiveStopping=copy.deepcopy(state)))
    row = result["results"][0]

    assert row["adaptiveStopping"] == state
    assert row["verdict"] == verdict
    assert row["responses"] == 17
    assert row["leadingOutcomeIds"] == ["o0"]
    assert "winner" not in row


@pytest.mark.parametrize(
    "task_type", ["Compare", "Classification", "Classify", "FutureTask"]
)
@pytest.mark.parametrize("split_details", [False, True])
def test_evidence_and_leading_set_survive_dataframe_and_json(
    task_type, split_details, tmp_path
):
    state = _snapshot("TopSet", ["o0", "o1", "o2"], count=30, outcome_count=6)
    state["parameters"]["maxOutcomeCount"] = 3
    for i, outcome in enumerate(state["outcomes"]):
        outcome.update(count=9 if i < 3 else 1, userScoreSum=4.5 if i < 3 else 0.5)
        outcome["share"] = {
            "estimate": 0.3 if i < 3 else 1 / 30,
            "lower": 0.2 if i < 3 else 0.0,
            "upper": 0.4 if i < 3 else 0.1,
        }
    state["future"] = {"empty": {}, "nested": [None, {"value": 2}]}
    result = RapidataResults(_payload(task_type, adaptiveStopping=copy.deepcopy(state)))

    frame = result.to_pandas(split_details=split_details)
    assert len(frame) > 0
    for _, row in frame.iterrows():
        assert row["adaptiveStopping"] == state
        assert row["leadingOutcomeIds"] == ["o0", "o1", "o2"]
        assert row["verdict"] == "TopSet"

    path = tmp_path / "results.json"
    result.to_json(str(path))
    loaded = RapidataResults(json.loads(path.read_text()))
    assert loaded == result
    assert loaded["results"][0]["adaptiveStopping"] == state


@pytest.mark.parametrize(
    "cant_solve",
    [
        "omitted",
        None,
        {
            "count": 0,
            "userScoreSum": 0.0,
            "share": {"estimate": None, "lower": 0.0, "upper": 1.0},
        },
    ],
)
def test_optional_cant_solve_and_undefined_estimates_roundtrip(cant_solve):
    state = _snapshot("Open", [], count=0)
    state["ambiguity"]["estimate"] = None
    for outcome in state["outcomes"]:
        outcome["share"]["estimate"] = None
    if cant_solve != "omitted":
        state["cantSolve"] = cant_solve
    result = RapidataResults(_payload(adaptiveStopping=copy.deepcopy(state)))

    assert json.loads(json.dumps(result))["results"][0]["adaptiveStopping"] == state
    assert result.to_pandas().iloc[0]["adaptiveStopping"] == state


@pytest.mark.parametrize("label, outcome_index", [("Both", 2), ("Neither", 3)])
def test_counts_weighted_shares_and_cant_solve_stay_separate_from_compare_options(
    label, outcome_index
):
    state = _snapshot("Unsolvable", [], count=20, outcome_count=4)
    state["parameters"]["unsolvableThreshold"] = 0.5
    state["cantSolve"] = {
        "count": 12,
        "userScoreSum": 9.0,
        "share": {"estimate": 0.75, "lower": 0.51, "upper": 0.9},
    }
    for outcome in state["outcomes"]:
        outcome.update(count=0, userScoreSum=0.0)
    state["outcomes"][outcome_index].update(count=8, userScoreSum=3.0)
    counts = {"left.png": 0, "right.png": 0, "Both": 0, "Neither": 0}
    counts[label] = 8
    scores = {"left.png": 0.0, "right.png": 0.0, "Both": 0.0, "Neither": 0.0}
    scores[label] = 3.0
    result = RapidataResults(
        _payload(
            adaptiveStopping=copy.deepcopy(state),
            aggregatedResults=counts,
            summedUserScores=scores,
        )
    )
    row = result.to_pandas().iloc[0]

    assert row["A_aggregatedResults"] == 0
    assert row["B_aggregatedResults"] == 0
    assert row[f"{label}_aggregatedResults"] == 8
    assert row["adaptiveStopping"]["cantSolve"]["count"] == 12
    assert row["adaptiveStopping"]["cantSolve"]["share"]["estimate"] == 0.75
    assert row["adaptiveStopping"]["outcomes"][outcome_index]["count"] == 8


def test_binary_weighted_evidence_does_not_replace_raw_counts():
    state = _snapshot("Winner", ["o1"])
    for outcome, count, score in zip(state["outcomes"], [12, 5], [2.0, 3.0]):
        outcome.update(count=count, userScoreSum=score)
        outcome["share"]["estimate"] = score / 5
    row = RapidataResults(_payload(adaptiveStopping=state)).to_pandas().iloc[0]

    assert row["A_aggregatedResults"] == 12
    assert row["B_aggregatedResults"] == 5
    assert row["A_summedUserScores"] == 2.0
    assert row["B_summedUserScores"] == 3.0
    assert row["adaptiveStopping"]["outcomes"][1]["share"]["estimate"] == 0.6
    assert row["leadingOutcomeIds"] == ["o1"]


@pytest.mark.parametrize("task_type", ["Compare", "Classification", "FutureTask"])
def test_non_adaptive_and_heterogeneous_rows_do_not_lose_metadata(task_type):
    payload = _payload(task_type)
    payload["results"].append({"identifier": "fixed", "adaptiveStopping": None})
    payload["results"].append(
        {"identifier": "adaptive", "adaptiveStopping": _snapshot("Open", [])}
    )
    result = RapidataResults(payload)
    rows = result["results"]

    assert "verdict" not in rows[0]
    assert "responses" not in rows[1]
    assert "leadingOutcomeIds" not in rows[1]
    frame = result.to_pandas()
    adaptive = frame[frame["identifier"] == "adaptive"].iloc[0]
    assert adaptive["verdict"] == "Open"
    assert adaptive["adaptiveStopping"] == rows[2]["adaptiveStopping"]


def test_new_snapshot_takes_precedence_over_legacy():
    result = RapidataResults(
        _payload(
            adaptiveStopping=_snapshot("TopSet", ["o1", "o2"]),
            stoppingState={"verdict": "B", "responseCount": 3},
        )
    )
    row = result["results"][0]
    assert row["verdict"] == "TopSet"
    assert row["responses"] == 17
    assert row["stoppingState"] == {"verdict": "B", "responseCount": 3}


@pytest.mark.parametrize(
    "verdict, expected",
    [
        ("A", "A"),
        ("B", "B"),
        ("Ambiguous", "ambiguous"),
        ("Undecided", "undecided"),
        ("Open", "open"),
        ("FutureVerdict", "FutureVerdict"),
        (None, "open"),
    ],
)
def test_legacy_decode_keeps_binary_behavior(verdict, expected):
    result = RapidataResults(
        _payload(stoppingState={"verdict": verdict, "responseCount": 7})
    )
    assert result["results"][0]["verdict"] == expected
    assert result["results"][0]["responses"] == 7


def test_long_counts_are_preserved():
    state = _snapshot(count=2**53 + 1)
    row = RapidataResults(_payload(adaptiveStopping=state))["results"][0]
    assert (
        json.loads(json.dumps(row))["adaptiveStopping"]["outcomes"][0]["count"]
        == 2**53 + 1
    )


@pytest.mark.parametrize("preliminary", [False, True])
def test_final_and_preliminary_job_downloads_keep_categorical_evidence(preliminary):
    service = MagicMock()
    service.environment = "rapidata.ai"
    job = RapidataJob(
        "job-1", "Job", "global", MagicMock(), "def-1", service, pipeline_id="pip-1"
    )
    job.get_status = MagicMock(return_value="Running" if preliminary else "Completed")
    job._wait_for_status = MagicMock()
    state = _snapshot("FutureVerdict", ["o0", "o2"], outcome_count=4)
    state["future"] = {"preserve": [None, {"empty": {}}]}
    payload = _payload(adaptiveStopping=state)
    service.order.job_api.job_job_id_download_results_get.return_value = json.dumps(
        payload
    )
    pipeline_api = service.pipeline.pipeline_api
    pipeline_api.pipeline_pipeline_id_preliminary_download_post.return_value.download_id = (
        "download-1"
    )
    response = (
        pipeline_api.pipeline_preliminary_download_preliminary_download_id_get_with_http_info.return_value
    )
    response.status_code = 200
    response.raw_data = json.dumps(payload).encode()

    row = job.get_results(preliminary_results=preliminary)["results"][0]

    assert row["adaptiveStopping"] == state
    assert row["verdict"] == "FutureVerdict"
    assert row["leadingOutcomeIds"] == ["o0", "o2"]
